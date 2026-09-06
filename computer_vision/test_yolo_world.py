"""
Diagnostic v3: is "mattress" the wrong WORD for what's actually in the
frame (a mattress wrapped in plain plastic), or does YOLO-World just not
see the object at all regardless of phrasing?

Tests several alternate phrasings, one at a time, against the same frame.
"""

import cv2
from ultralytics import YOLO

VIDEO_PATH = "data/raw_videos/Throwing_Mattresses.mp4"
TIMESTAMP = 8.9
CONF_THRESHOLD = 0.03

# Each of these is tried as a SEPARATE single-class vocabulary, one at a
# time - so we can see which specific wording (if any) catches the object,
# without other class names "stealing" the match.
PHRASES_TO_TRY = [
    "mattress",
    "bed mattress",
    "rolled mattress",
    "foam mattress",
    "bedding",
    "wrapped package",
    "large white bundle",
    "plastic wrapped object",
    "furniture wrapped in plastic",
    "large box",
    "cardboard box",
    "cupboard",
    "wardrobe",
    "goods",
    "warehouse goods",
    "packaged goods",
    "freight",
    "cargo",
    "shipment",
]

cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS) or 30
frame_number = int(TIMESTAMP * fps)
cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
ok, frame = cap.read()
cap.release()
if not ok:
    print(f"Could not read frame from {VIDEO_PATH}")
    raise SystemExit(1)

print("Loading YOLO-World once...")
model = YOLO("yolov8s-world.pt")
print("Loaded. Testing each phrase separately...\n")

best_conf = 0.0
best_phrase = None

for phrase in PHRASES_TO_TRY:
    model.set_classes([phrase])
    results = model.predict(frame, conf=CONF_THRESHOLD, verbose=False)
    r = results[0]
    if len(r.boxes) == 0:
        print(f"  '{phrase}': nothing")
    else:
        confs = [float(b.conf[0]) for b in r.boxes]
        top = max(confs)
        print(f"  '{phrase}': {len(confs)} box(es), top conf={top:.3f}")
        if top > best_conf:
            best_conf = top
            best_phrase = phrase
            cv2.imwrite("yolo_world_best_phrase.jpg", r.plot())

print(f"\nBest result: '{best_phrase}' at conf={best_conf:.3f}")
if best_conf < 0.15:
    print("Even the best phrasing is weak (<0.15) - this looks like a real "
          "model limitation on this footage, not a wording problem. "
          "Custom training is the right call.")
else:
    print(f"'{best_phrase}' got a usable confidence - check yolo_world_best_phrase.jpg. "
          "This phrasing might be worth using in the real pipeline instead of 'mattress'.")