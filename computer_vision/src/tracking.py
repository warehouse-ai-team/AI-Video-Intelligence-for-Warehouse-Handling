"""
Phase 4 - Tracking module.

- Persons: ultralytics' built-in ByteTrack (model.track(...)), verified
  working on real footage. Real limitation observed: ID churn on crowded
  frames in low-quality re-recorded footage (IDs can switch within ~1s
  when people cross paths or the codec introduces compression artifacts).
  This is reported, not hidden - see data/annotations/detection_findings.md.

- Products (from ProductBlobDetector): simple greedy IoU tracker. Good
  enough for single-product-per-event clips like ours; would need a real
  tracker (SORT/ByteTrack-style Kalman prediction) if multiple products
  move simultaneously and cross paths.
"""

from ultralytics import YOLO


class PersonByteTracker:
    def __init__(self, model_path="yolo11n-pose.pt", conf_threshold=0.35, device="auto"):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = None if device == "auto" else device

    def track_video(self, video_path, tracker_cfg="bytetrack.yaml", content_roi=None, frame_skip=1):
        """
        Yields (frame_idx, frame, list of dict) where each dict is:
        {track_id, cls, conf, x1, y1, x2, y2, cx, cy, keypoints}

        If content_roi=(x1,y1,x2,y2) is given, each frame is cropped to that
        region BEFORE being handed to the tracker (persist=True keeps ID
        state across calls). This matters a lot for split-screen recordings
        where two independent camera feeds are stacked in one video frame -
        tracking across both as if they were one continuous scene causes ID
        churn. Detected boxes are shifted back to full-frame coordinates
        before being returned, so downstream code doesn't need to know
        cropping happened.
        """
        import cv2
        cap = cv2.VideoCapture(video_path)
        frame_idx = 0
        rx1, ry1 = (content_roi[0], content_roi[1]) if content_roi else (0, 0)

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_idx % frame_skip != 0:
                frame_idx += 1
                continue

            proc_frame = frame
            if content_roi:
                x1, y1, x2, y2 = content_roi
                proc_frame = frame[y1:y2, x1:x2]

            r = self.model.track(
                proc_frame, tracker=tracker_cfg, classes=[0],
                conf=self.conf_threshold, device=self.device,
                verbose=False, persist=True,
            )[0]

            out = []
            ids = r.boxes.id
            kpts_all = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else None
            if ids is not None:
                for i, box in enumerate(r.boxes):
                    bx1, by1, bx2, by2 = [float(v) for v in box.xyxy[0]]
                    # shift back to full-frame coords
                    x1f, y1f, x2f, y2f = bx1 + rx1, by1 + ry1, bx2 + rx1, by2 + ry1
                    conf = float(box.conf[0])
                    track_id = int(ids[i])
                    cx, cy = (x1f + x2f) / 2, (y1f + y2f) / 2
                    kpts = None
                    if kpts_all is not None and i < len(kpts_all):
                        kpts = [[kx + rx1, ky + ry1] for kx, ky in kpts_all[i].tolist()]
                    out.append({
                        "track_id": track_id, "cls": "person", "conf": conf,
                        "x1": x1f, "y1": y1f, "x2": x2f, "y2": y2f,
                        "cx": cx, "cy": cy, "keypoints": kpts,
                    })
            yield frame_idx, frame, out
            frame_idx += 1

        cap.release()


class SimpleIOUTracker:
    """
    Greedy IoU + centroid-distance tracker for class-agnostic product blobs.

    NOTE (honest limitation, verified empirically): pure IoU matching failed
    badly on real footage - MOG2 blob edges are too jittery frame-to-frame
    (100+ spurious IDs in an 81-frame window). Adding a centroid-distance
    fallback (a blob is "the same object" if its center moved less than
    max_centroid_dist px, even if the box shape changed) is a partial fix.
    If ID stability is still not good enough for a specific behaviour rule,
    prefer deriving that rule from a fixed ROI around the tracked PERSON
    (which IS reliably tracked) rather than depending on independent
    product track IDs across the whole clip.
    """

    def __init__(self, iou_threshold=0.15, max_missed=10, max_centroid_dist=80):
        self.iou_threshold = iou_threshold
        self.max_missed = max_missed
        self.max_centroid_dist = max_centroid_dist
        self.tracks = {}  # id -> {"box": (x1,y1,x2,y2), "missed": int}
        self.next_id = 1

    @staticmethod
    def _iou(box_a, box_b):
        ax1, ay1, ax2, ay2 = box_a
        bx1, by1, bx2, by2 = box_b
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        if ix2 <= ix1 or iy2 <= iy1:
            return 0.0
        inter = (ix2 - ix1) * (iy2 - iy1)
        area_a = (ax2 - ax1) * (ay2 - ay1)
        area_b = (bx2 - bx1) * (by2 - by1)
        union = area_a + area_b - inter
        return inter / union if union > 0 else 0.0

    def update(self, detections):
        """detections: list of Detection namedtuples (cls='product'). Returns list of dicts with track_id."""
        det_boxes = [(d.x1, d.y1, d.x2, d.y2) for d in detections]
        matched_track_ids = set()
        matched_det_idxs = set()

        def centroid(b):
            return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

        # Greedy match: score = IoU if above threshold OR centroid closeness, highest score first
        pairs = []
        for tid, t in self.tracks.items():
            tc = centroid(t["box"])
            for di, db in enumerate(det_boxes):
                iou = self._iou(t["box"], db)
                dc = centroid(db)
                dist = ((tc[0] - dc[0]) ** 2 + (tc[1] - dc[1]) ** 2) ** 0.5
                score = None
                if iou >= self.iou_threshold:
                    score = 1.0 + iou  # prefer IoU matches
                elif dist <= self.max_centroid_dist:
                    score = 1.0 - (dist / self.max_centroid_dist)  # closer = higher
                if score is not None:
                    pairs.append((score, tid, di))
        pairs.sort(reverse=True, key=lambda p: p[0])

        for score, tid, di in pairs:
            if tid in matched_track_ids or di in matched_det_idxs:
                continue
            self.tracks[tid]["box"] = det_boxes[di]
            self.tracks[tid]["missed"] = 0
            matched_track_ids.add(tid)
            matched_det_idxs.add(di)

        # New tracks for unmatched detections
        for di, db in enumerate(det_boxes):
            if di not in matched_det_idxs:
                self.tracks[self.next_id] = {"box": db, "missed": 0}
                matched_track_ids.add(self.next_id)
                matched_det_idxs.add(di)
                self.next_id += 1

        # Age out unmatched tracks
        for tid in list(self.tracks.keys()):
            if tid not in matched_track_ids:
                self.tracks[tid]["missed"] += 1
                if self.tracks[tid]["missed"] > self.max_missed:
                    del self.tracks[tid]

        # Build output (only for tracks matched this frame)
        out = []
        det_by_box = {db: d for db, d in zip(det_boxes, detections)}
        for tid, t in self.tracks.items():
            if t["missed"] == 0 and t["box"] in det_by_box:
                d = det_by_box[t["box"]]
                x1, y1, x2, y2 = t["box"]
                out.append({
                    "track_id": tid, "cls": "product", "conf": d.conf,
                    "x1": x1, "y1": y1, "x2": x2, "y2": y2,
                    "cx": (x1 + x2) / 2, "cy": (y1 + y2) / 2, "keypoints": None,
                })
        return out
