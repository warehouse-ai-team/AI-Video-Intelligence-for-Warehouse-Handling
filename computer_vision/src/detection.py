"""
Phase 3/5 - Detection module.

Two complementary detectors, because COCO-pretrained YOLO has NO class for
carton / box / mattress / pallet (verified empirically on real footage -
see data/annotations/detection_findings.md).

STATUS (updated after running across all 6 real videos, not just one):
- PersonDetector: reliable, verified.
- YoloWorldProductDetector: PREFERRED for products. Not yet verified inside
  this build sandbox (network-restricted, see class docstring) but should
  work on a normal machine. Test it first.
- ProductBlobDetector: the original class-agnostic motion-blob fallback.
  VERIFIED BROKEN for busy scenes: on all 6 real clips it just as often
  tracks ambient foot traffic as the actual flagged product, because it has
  no way to distinguish "a carton" from "a person walking through the
  background" - both are just moving blobs. Kept in the codebase as a
  last-resort fallback (e.g. if YOLO-World isn't usable) and because the
  background-subtraction code is still useful for other things (e.g. a
  coarse "is anything moving in this ROI at all" signal), but it should NOT
  be trusted as the primary product tracker without further constraints
  (e.g. restricting it to a tight ROI immediately at the truck opening).
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


class YoloWorldProductDetector:
    """
    Open-vocabulary product detector using YOLO-World. PREFERRED over
    ProductBlobDetector - test this first on your machine.

    Why: empirically (see data/annotations/detection_findings.md), background
    subtraction fails on busy dock scenes because ambient foot traffic and
    other continuous motion gets picked up as "the product" just as often as
    the actual carton/mattress/pallet involved in the flagged event. YOLO-World
    detects by semantic class instead of by motion, so it doesn't have this
    failure mode.

    This class could NOT be tested inside the build sandbox - CLIP's weight
    host (openaipublic.azureedge.net) isn't on the sandbox's restricted
    network allowlist (only pypi/npm/github are permitted there). It WILL
    work on a normal internet connection. Test with:

        python -c "
        from ultralytics import YOLO
        m = YOLO('yolov8s-world.pt')
        m.set_classes(['cardboard box','mattress','pallet','pallet jack'])
        r = m.predict('data/frames/Throwing_Mattresses/Throwing_Mattresses_f000267_t8.90s.jpg')
        r[0].show()
        "

    If that runs and draws boxes around the mattress, swap this class in for
    ProductBlobDetector in run_tracking_demo.py - the Detection interface is
    identical, no other code changes needed.
    """

    def __init__(self, classes=None, conf_threshold=0.15, device="auto"):
        self.model = YOLO("yolov8s-world.pt")
        self.classes = classes or ["cardboard box", "carton", "mattress", "pallet", "pallet jack"]
        self.model.set_classes(self.classes)
        self.conf_threshold = conf_threshold
        self.device = None if device == "auto" else device

    def detect(self, frame, exclude_boxes=None):
        results = self.model.predict(
            frame, conf=self.conf_threshold, device=self.device, verbose=False
        )
        r = results[0]
        detections = []
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = self.classes[cls_id] if cls_id < len(self.classes) else "product"
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            detections.append(Detection(cls_name, conf, x1, y1, x2, y2, None))
        return detections


class CustomYoloProductDetector:
    """
    Fine-tuned YOLO for carton/mattress/pallet, trained specifically on
    this footage (see computer_vision/README.md "Custom training plan").

    Used once you have a trained weights file (e.g.
    runs/detect/train/weights/best.pt) - see train_product_detector.py.
    Same Detection interface as the other detectors, so it's a drop-in
    swap in run_tracking_demo.py.
    """

    def __init__(self, model_path="runs/detect/train/weights/best.pt", conf_threshold=0.25, device="auto"):
        self.model = YOLO(model_path)
        self.conf_threshold = conf_threshold
        self.device = None if device == "auto" else device
        self.class_names = self.model.names  # dict {id: name}, comes from the trained model itself

    def detect(self, frame, exclude_boxes=None):
        results = self.model.predict(
            frame, conf=self.conf_threshold, device=self.device, verbose=False
        )
        r = results[0]
        detections = []
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = self.class_names.get(cls_id, "product")
            conf = float(box.conf[0])
            x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
            detections.append(Detection(cls_name, conf, x1, y1, x2, y2, None))
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
