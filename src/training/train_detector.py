"""Vehicle Detection Model Training Script using YOLOv8 / YOLOv11.

Trains custom detector for:
- Car, Motorcycle, Bus, Truck.
Integrates surveillance-specific hyperparameters (mosaic, mixup, perspective).
"""

import argparse
from pathlib import Path
from loguru import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def train_vehicle_detector(
    data_yaml: str = "configs/traffic_data.yaml",
    model_name: str = "yolov8s.pt",
    epochs: int = 100,
    batch_size: int = 16,
    img_size: int = 640,
    device: str = "0",
    project: str = "runs/train",
    name: str = "traffic_vehicle_yolo",
    resume: bool = False
):
    """Executes vehicle detector training with high-vantage traffic camera augmentations."""
    if not ULTRALYTICS_AVAILABLE:
        raise RuntimeError("Ultralytics required. Install via `pip install ultralytics`.")

    data_path = Path(data_yaml)
    if not data_path.exists():
        logger.warning(
            f"Dataset configuration '{data_yaml}' not found. "
            f"Please create it or point to your dataset YAML."
        )

    logger.info(f"Loading base model: {model_name}...")
    model = YOLO(model_name)

    logger.info("Starting training with surveillance-tailored hyperparameters...")
    results = model.train(
        data=str(data_yaml),
        epochs=epochs,
        batch=batch_size,
        imgsz=img_size,
        device=device,
        project=project,
        name=name,
        resume=resume,
        patience=20,             # Early stopping if no mAP improvement in 20 epochs
        save=True,
        save_period=10,
        # Augmentation tailored for elevated intersection CCTV:
        mosaic=1.0,              # Multi-scale object context
        mixup=0.15,              # Occlusion resilience (vehicles overlapping)
        degrees=10.0,            # Camera angle skew tolerance
        translate=0.1,           # Frame jitter tolerance
        scale=0.2,               # Object distance scale changes
        shear=2.0,               # Oblique perspective tolerance
        perspective=0.0005,      # 3D depth distortion
        flipud=0.0,              # No vertical flipping for upright vehicles
        fliplr=0.5,              # Horizontal flip
        hsv_h=0.015,             # Hue shift
        hsv_s=0.7,               # Saturation (rainy/cloudy vs sunny)
        hsv_v=0.4,               # Brightness (day vs night shift)
        plots=True,
        verbose=True
    )

    logger.success(f"Training completed! Best weights saved at: {project}/{name}/weights/best.pt")
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train Traffic Vehicle Detector (YOLO)")
    parser.add_argument("--data", type=str, default="configs/traffic_data.yaml", help="Path to data.yaml")
    parser.add_argument("--model", type=str, default="yolov8s.pt", help="Base model weights (yolov8n.pt, yolov8s.pt, yolov11s.pt)")
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (decrease to 8 or 4 if CUDA OOM)")
    parser.add_argument("--imgsz", type=int, default=640, help="Image resolution")
    parser.add_argument("--device", type=str, default="0", help="GPU device ID or 'cpu'")
    parser.add_argument("--name", type=str, default="traffic_vehicle_yolo", help="Run name")
    parser.add_argument("--resume", action="store_true", help="Resume training from last checkpoint")

    args = parser.parse_args()
    train_vehicle_detector(
        data_yaml=args.data,
        model_name=args.model,
        epochs=args.epochs,
        batch_size=args.batch,
        img_size=args.imgsz,
        device=args.device,
        name=args.name,
        resume=args.resume
    )
