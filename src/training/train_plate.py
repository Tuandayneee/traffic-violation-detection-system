"""License Plate Detector Training Script using YOLOv8-nano.

Specialized for detecting rectangular vehicle license plates in Vietnam:
- 1-row rectangular car plates
- 2-row square motorcycle plates
"""

import argparse
from pathlib import Path
from loguru import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def train_plate_detector(
    data_yaml: str = "configs/plate_data.yaml",
    model_name: str = "yolov8n.pt",
    epochs: int = 80,
    batch_size: int = 32,
    img_size: int = 640,
    device: str = "0",
    project: str = "runs/train",
    name: str = "plate_detector_yolo"
):
    """Fine-tunes lightweight YOLOv8n specifically for license plate bounding boxes."""
    if not ULTRALYTICS_AVAILABLE:
        raise RuntimeError("Ultralytics required. Install via `pip install ultralytics`.")

    logger.info(f"Initializing License Plate model from {model_name}...")
    model = YOLO(model_name)

    results = model.train(
        data=data_yaml,
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=device,
        project=project,
        name=name,
        patience=15,
        save=True,
        # Plate-specific augmentations (high detail preservation):
        mosaic=0.5,
        scale=0.1,
        degrees=5.0,
        flipud=0.0,
        fliplr=0.5,
        plots=True
    )

    logger.success(f"Plate detector training done! Checkpoint: {project}/{name}/weights/best.pt")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train License Plate Detector")
    parser.add_argument("--data", type=str, default="configs/plate_data.yaml", help="Path to plate dataset yaml")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Base model")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch", type=int, default=32)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", type=str, default="0")
    parser.add_argument("--name", type=str, default="plate_detector_yolo")

    args = parser.parse_args()
    train_plate_detector(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        device=args.device,
        name=args.name
    )
