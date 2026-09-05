"""
Phase 3/5 - Detection module.

Two complementary detectors, because COCO-pretrained YOLO has NO class for
carton / box / mattress / pallet (verified empirically on real footage -
see data/annotations/detection_findings.md). We do NOT train a custom model
in the 2-day window; instead:

1. PersonDetector - pretrained YOLO, class 0 (person). Reliable, verified.
2. ProductBlobDetector - background-subtraction based motion blob detector.
   Class-agnostic proxy for "product" (carton/mattress/pallet/whatever moves).
   Works on any static CCTV camera without training or internet access.

If you test YOLO-World locally (see README) and it reliably detects
'cardboard box' / 'mattress' / 'pallet' on your machine, swap
ProductBlobDetector for YoloWorldProductDetector - the interface
(list of Detection namedtuples per frame) is identical either way.
"""

from collections import namedtuple
import cv2
import numpy as np
from ultralytics import YOLO

Detection = namedtuple("Detection", ["cls", "conf", "x1", "y1", "x2", "y2", "keypoints"])


class PersonDetector:
    """Pretrained YOLO person detection (+ pose keypoints for stepping_on_carton)."""

    def __init__(self, model_path="yolo11n-pose.pt", conf_threshold=0.35, device="auto"):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = None if device == "auto" else device

    def detect(self, frame):
        results = self.model.predict(
            frame, classes=[0], conf=self.conf_threshold,
            device=self.device, verbose=False
        )
        r = results[0]
        detections = []
        kpts_all = r.keypoints.xy.cpu().numpy() if r.keypoints is not None else None
        for i, box in enumerate(r.boxes):
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            conf = float(box.conf[0])
            kpts = kpts_all[i].tolist() if kpts_all is not None and i < len(kpts_all) else None
            detections.append(Detection("person", conf, x1, y1, x2, y2, kpts))
        return detections


class ProductBlobDetector:
    """
    Class-agnostic moving-object detector for products (carton/mattress/pallet).
    Background subtraction (MOG2) + contour filtering.

    Caveats (report these, do not hide them):
    - Only detects objects that MOVE relative to the static background.
      A product sitting still on the floor before/after an event will NOT
      be detected by this method alone - it is a motion proxy, not a
      general object detector.
    - Cannot distinguish carton vs. mattress vs. pallet vs. a person's
      shadow - class label is always the generic 'product'.
    - Tuned for static, fixed-mount CCTV cameras (all 6 audited videos
      qualify - camera does not pan/zoom).
    """

    def __init__(self, min_area=1500, history=30, var_threshold=40):
        self.bg_sub = cv2.createBackgroundSubtractorMOG2(
            history=history, varThreshold=var_threshold, detectShadows=False
        )
        self.min_area = min_area
        self._warmup_frames = 15  # let the background model stabilize
        self._frame_count = 0

    def detect(self, frame, exclude_boxes=None):
        """
        exclude_boxes: list of (x1,y1,x2,y2) person boxes to suppress from
        product blobs, so we don't double-detect a walking person as a
        'product'. Cheap IoU-based suppression, not perfect.
        """
        fgmask = self.bg_sub.apply(frame)
        self._frame_count += 1

        detections = []
        if self._frame_count <= self._warmup_frames:
            return detections  # background model still learning

        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))
        fgmask = cv2.dilate(fgmask, np.ones((9, 9), np.uint8), iterations=2)
        contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        exclude_boxes = exclude_boxes or []
        for c in contours:
            area = cv2.contourArea(c)
            if area < self.min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            x1, y1, x2, y2 = x, y, x + w, y + h

            if self._overlaps_person(x1, y1, x2, y2, exclude_boxes):
                continue

            detections.append(Detection("product", 0.5, float(x1), float(y1), float(x2), float(y2), None))
        return detections

    @staticmethod
    def _overlaps_person(x1, y1, x2, y2, person_boxes, iou_thresh=0.5):
        for (px1, py1, px2, py2) in person_boxes:
            ix1, iy1 = max(x1, px1), max(y1, py1)
            ix2, iy2 = min(x2, px2), min(y2, py2)
            if ix2 <= ix1 or iy2 <= iy1:
                continue
            inter = (ix2 - ix1) * (iy2 - iy1)
            area_a = (x2 - x1) * (y2 - y1)
            if area_a > 0 and inter / area_a > iou_thresh:
                return True
        return False
