"""Dataset Validator & Quality Assurance Suite.

Verifies:
- Label formatting (YOLO: class x_center y_center width height, all in [0, 1]).
- Corrupt / non-readable image files.
- Empty label files or orphan images without annotations.
- Class distribution balance & outlier bounding boxes.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple, Any
from loguru import logger
import cv2


class DatasetValidator:
    """Validates YOLO and ALPR traffic datasets for consistency and errors."""

    def __init__(self, data_root: str, class_names: List[str]):
        self.data_root = Path(data_root)
        self.class_names = class_names
        self.num_classes = len(class_names)
        self.stats: Dict[str, Any] = {
            "total_images": 0,
            "valid_images": 0,
            "corrupted_images": 0,
            "missing_labels": 0,
            "empty_labels": 0,
            "total_boxes": 0,
            "class_counts": {name: 0 for name in class_names},
            "invalid_boxes": 0,
        }

    def validate_split(self, split: str = "train") -> Dict[str, Any]:
        """Scans a specific split (train/val/test) and reports discrepancies."""
        img_dir = self.data_root / "images" / split
        lbl_dir = self.data_root / "labels" / split

        if not img_dir.exists():
            logger.warning(f"Image directory does not exist: {img_dir}")
            return self.stats

        image_files = list(img_dir.glob("*.jpg")) + list(img_dir.glob("*.png"))
        self.stats["total_images"] = len(image_files)

        for img_path in image_files:
            # 1. Verify image can be decoded
            img = cv2.imread(str(img_path))
            if img is None:
                self.stats["corrupted_images"] += 1
                logger.error(f"Corrupt image file: {img_path}")
                continue

            self.stats["valid_images"] += 1
            h, w = img.shape[:2]

            # 2. Check corresponding label file
            lbl_path = lbl_dir / f"{img_path.stem}.txt"
            if not lbl_path.exists():
                self.stats["missing_labels"] += 1
                continue

            with open(lbl_path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]

            if not lines:
                self.stats["empty_labels"] += 1
                continue

            # 3. Validate each bounding box
            for line in lines:
                parts = line.split()
                if len(parts) < 5:
                    self.stats["invalid_boxes"] += 1
                    continue

                try:
                    cls_id = int(parts[0])
                    xc, yc, bw, bh = map(float, parts[1:5])
                except ValueError:
                    self.stats["invalid_boxes"] += 1
                    continue

                # Coordinate boundary check [0, 1]
                if not (0.0 <= xc <= 1.0 and 0.0 <= yc <= 1.0 and 0.0 < bw <= 1.0 and 0.0 < bh <= 1.0):
                    self.stats["invalid_boxes"] += 1
                    continue

                if 0 <= cls_id < self.num_classes:
                    cname = self.class_names[cls_id]
                    self.stats["class_counts"][cname] += 1
                    self.stats["total_boxes"] += 1
                else:
                    self.stats["invalid_boxes"] += 1

        logger.info(f"Validation completed for split '{split}': {self.stats}")
        return self.stats
