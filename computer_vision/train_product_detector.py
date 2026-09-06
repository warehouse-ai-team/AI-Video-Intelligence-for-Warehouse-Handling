"""
Fine-tune a small YOLO model on your own annotated carton/mattress/pallet
data (exported from Roboflow or CVAT in YOLO format).
"""

import argparse
from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="path to data.yaml from your exported dataset")
    ap.add_argument("--base_model", default="yolo11n.pt", help="pretrained weights to fine-tune from")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cpu", help="'cpu', or '0' for first GPU if you have one")
    args = ap.parse_args()

    model = YOLO(args.base_model)
    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=args.device,
        patience=20,
        batch=8,
        project="runs/detect",
        name="product_detector",
    )
    print("\nDone. Best weights saved to runs/detect/product_detector/weights/best.pt")


if __name__ == "__main__":
    main()
