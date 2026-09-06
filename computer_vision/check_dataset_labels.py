"""
Corrected version: a label file is only a REAL problem if it mixes plain
bbox rows (exactly 5 values: class x y w h) WITH polygon rows (class +
variable-length point list) in the SAME file. A file that is consistently
ALL polygon rows (from SAM3 auto-label) or ALL bbox rows (from manual
boxes) is fine - Ultralytics trains from either.

Usage (from computer_vision folder):
    python check_dataset_labels_v2.py --dataset data/dataset
"""

import argparse
import os
import glob
import yaml


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="data/dataset")
    args = ap.parse_args()

    yaml_path = os.path.join(args.dataset, "data.yaml")
    with open(yaml_path) as f:
        data_cfg = yaml.safe_load(f)
    names = data_cfg.get("names", [])
    print(f"Classes defined in data.yaml: {names}\n")

    class_counts = {i: 0 for i in range(len(names))}
    truly_mixed_files = []
    total_label_files = 0
    empty_label_files = 0
    polygon_format_files = 0
    bbox_format_files = 0

    for split in ["train", "valid", "test"]:
        label_dir = os.path.join(args.dataset, split, "labels")
        if not os.path.isdir(label_dir):
            continue
        label_files = glob.glob(os.path.join(label_dir, "*.txt"))
        for lf in label_files:
            total_label_files += 1
            with open(lf) as f:
                lines = [l.strip() for l in f if l.strip()]
            if not lines:
                empty_label_files += 1
                continue

            has_bbox_row = any(len(l.split()) == 5 for l in lines)
            has_polygon_row = any(len(l.split()) != 5 for l in lines)

            if has_bbox_row and has_polygon_row:
                truly_mixed_files.append(lf)
                continue  # this one genuinely gets dropped by Ultralytics

            if has_polygon_row:
                polygon_format_files += 1
            else:
                bbox_format_files += 1

            # count instances regardless of format - class id is always the first token
            for l in lines:
                cls_id = int(l.split()[0])
                if cls_id in class_counts:
                    class_counts[cls_id] += 1

    print(f"Total label files: {total_label_files}")
    print(f"Empty (no objects): {empty_label_files}")
    print(f"Consistent polygon-format files (fine): {polygon_format_files}")
    print(f"Consistent bbox-format files (fine): {bbox_format_files}")
    print(f"TRULY mixed/corrupt files (genuinely dropped by training): {len(truly_mixed_files)}\n")

    print("Instance counts per class (across all valid files):")
    for i, name in enumerate(names):
        print(f"  {name:12s}: {class_counts.get(i, 0)}")

    if truly_mixed_files:
        print(f"\nGenuinely problematic files:")
        for lf in truly_mixed_files:
            print(f"  {lf}")


if __name__ == "__main__":
    main()