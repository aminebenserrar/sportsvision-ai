"""Inspect the original Kaggle Sports Classification train/valid/test split.

The dataset downloaded by the Colab notebook already contains train/, valid/ and
test/; this script checks the split instead of creating an artificial random split.
Run: python scripts/check_dataset.py /path/to/sports-dataset
"""
from pathlib import Path
import argparse
from PIL import Image

SPORTS = ("basketball", "football", "tennis")
SPLITS = ("train", "valid", "test")
EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def main():
    parser = argparse.ArgumentParser(description="Audit the original sports dataset")
    parser.add_argument("dataset_root", type=Path)
    args = parser.parse_args()
    root = args.dataset_root
    if not all((root / name).is_dir() for name in SPLITS):
        raise SystemExit("Expected train/, valid/ and test/ subdirectories.")
    print("Split       Basketball   Football   Tennis   Total")
    for split in SPLITS:
        values = []
        for sport in SPORTS:
            folder = root / split / sport
            if not folder.is_dir():
                raise SystemExit(f"Missing class folder: {folder}")
            images = [p for p in folder.iterdir()
                      if p.is_file() and p.suffix.lower() in EXTENSIONS]
            values.append(len(images))
        print(f"{split:<11} {values[0]:<12} {values[1]:<10} "
              f"{values[2]:<8} {sum(values)}")
    print("Model preprocessing: RGB, 224x224; built-in Rescaling layer.")


if __name__ == "__main__":
    main()
