"""
Direct test: does our newly fine-tuned model (best.pt) actually detect
mattress, now that we know 11 real mattress instances were in training data?
"""

import argparse
import cv2
from ultralytics import YOLO

ap = argparse.ArgumentParser()
ap.add_argument("--weights", default="runs/detect/product_detector/weights/best.pt")
args = ap.parse_args()

WEIGHTS = args.weights
VIDEO_PATH = "data/raw_videos/Throwing_Mattresses.mp4"
TIMESTAMPS = [5.0, 8.9, 15.0, 20.0]
CONF_THRESHOLD = 0.15

model = YOLO(WEIGHTS)
print(f"Loaded {WEIGHTS}")
print(f"Classes: {model.names}\n")

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30

for t in TIMESTAMPS:
    frame_number = int(t * fps)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
    ok, frame = cap.read()
    if not ok:
        continue

    results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False)
    r = results[0]
    print(f"--- t={t}s ---")
    if len(r.boxes) == 0:
        print("  nothing detected")
    else:
        for box in r.boxes:
            cls_id = int(box.cls[0])
            cls_name = model.names[cls_id]
            conf = float(box.conf[0])
            print(f"  {cls_name:12s} conf={conf:.3f}")

    out_path = f"custom_model_test_t{t}.jpg"
    cv2.imwrite(out_path, r.plot())
    print(f"  saved -> {out_path}")

cap.release()
print("\nCheck the saved images - is there a box around the mattress in any of them?")