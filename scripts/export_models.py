"""Model Export & Optimization Utility.

Converts PyTorch YOLO models (.pt) to high-speed Edge formats:
- ONNX Runtime (FP32 / FP16, dynamic batch)
- NVIDIA TensorRT (.engine) for ultra-low latency inference (30-60 FPS)
- OpenVINO for Intel CPU/iGPU/VPU edge deployment
"""

import argparse
from pathlib import Path
from loguru import logger

try:
    from ultralytics import YOLO
    ULTRALYTICS_AVAILABLE = True
except ImportError:
    ULTRALYTICS_AVAILABLE = False


def export_model(
    weights_path: str,
    format_type: str = "onnx",
    img_size: int = 640,
    half: bool = True,
    device: str = "cpu"
) -> Path:
    """Exports a YOLO model to the specified format.

    Args:
        weights_path: Path to .pt checkpoint.
        format_type: 'onnx', 'engine' (TensorRT), or 'openvino'.
        img_size: Inference image size (square).
        half: Enable FP16 half precision.
        device: 'cpu' or '0' (CUDA).

    Returns:
        Path to exported artifact.
    """
    if not ULTRALYTICS_AVAILABLE:
        raise RuntimeError("Ultralytics library required for export. Run `pip install ultralytics`.")

    weights_file = Path(weights_path)
    if not weights_file.exists():
        logger.warning(f"Weights file not found at {weights_path}. Generating dummy/default yolov8n export.")
        model = YOLO("yolov8n.pt")
    else:
        logger.info(f"Loading checkpoint: {weights_path}")
        model = YOLO(str(weights_file))

    logger.info(f"Exporting model to format='{format_type}' (imgsz={img_size}, half={half}, device={device})...")
    
    export_args = {
        "format": format_type,
        "imgsz": img_size,
        "half": half,
        "device": device,
        "dynamic": True if format_type == "onnx" else False,
        "simplify": True if format_type == "onnx" else False,
    }

    try:
        exported_path = model.export(**export_args)
        logger.success(f"Export completed successfully: {exported_path}")
        return Path(exported_path)
    except Exception as e:
        logger.error(f"Export failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLO model to ONNX / TensorRT")
    parser.add_argument("--weights", type=str, default="yolov8n.pt", help="Path to .pt weights file")
    parser.add_argument("--format", type=str, default="onnx", choices=["onnx", "engine", "openvino"], help="Target format")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image dimension")
    parser.add_argument("--half", action="store_true", help="Enable FP16 half-precision")
    parser.add_argument("--device", type=str, default="cpu", help="Target device (cpu or 0)")

    args = parser.parse_args()
    export_model(
        weights_path=args.weights,
        format_type=args.format,
        img_size=args.imgsz,
        half=args.half,
        device=args.device
    )
