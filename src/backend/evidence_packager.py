"""Evidence Packaging Service for Traffic Violations."""

from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import json
import time
import cv2
import numpy as np

from ..rules.base_rule import ViolationEvent
from .video_buffer import FrameRingBuffer


class EvidencePackager:
    """Packages images, cropped plates, video clips, and metadata for legal proof."""

    def __init__(self, output_root: str = "./data/evidence"):
        self.output_root = Path(output_root)
        self.output_root.mkdir(parents=True, exist_ok=True)

    def package_violation(
        self,
        event: ViolationEvent,
        current_frame: np.ndarray,
        ring_buffer: Optional[FrameRingBuffer] = None,
        plate_crop: Optional[np.ndarray] = None,
        stop_line: Optional[List[List[int]]] = None
    ) -> Dict[str, str]:
        """Generates all evidence artifacts on disk and returns relative file paths."""
        event_dir = self.output_root / event.event_id
        event_dir.mkdir(parents=True, exist_ok=True)

        # 1. Annotated Snapshot (Full Scene with BBox & Evidence Text)
        annotated = current_frame.copy()
        x1, y1, x2, y2 = event.bbox

        # Draw vehicle bounding box in bright red/orange
        cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 3)

        # Draw stop line if provided
        if stop_line and len(stop_line) >= 2:
            pt1 = tuple(stop_line[0])
            pt2 = tuple(stop_line[1])
            cv2.line(annotated, pt1, pt2, (0, 255, 255), 3)

        # Draw header banner
        header_text = f"VIOLATION: {event.violation_type.value} | Plate: {event.license_plate or 'UNRESOLVED'}"
        cv2.putText(annotated, header_text, (40, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
        cv2.putText(annotated, f"Track ID: {event.track_id} | Time: {time.ctime(event.timestamp)}", (40, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        snapshot_path = event_dir / "snapshot_full.jpg"
        cv2.imwrite(str(snapshot_path), annotated)

        # 2. License Plate Crop
        plate_path_str = ""
        if plate_crop is not None and plate_crop.size > 0:
            plate_file = event_dir / "plate_crop.jpg"
            cv2.imwrite(str(plate_file), plate_crop)
            plate_path_str = str(plate_file)

        # 3. Video Clip (5 seconds snippet)
        video_path_str = ""
        if ring_buffer is not None:
            video_file = event_dir / "evidence_clip.mp4"
            success = ring_buffer.export_video_clip(str(video_file), fps=30, num_frames=120)
            if success:
                video_path_str = str(video_file)

        # 4. Metadata JSON
        meta = {
            "event_id": event.event_id,
            "violation_type": event.violation_type.value,
            "track_id": event.track_id,
            "vehicle_type": event.vehicle_type,
            "license_plate": event.license_plate,
            "plate_confidence": event.plate_confidence,
            "confidence": event.confidence,
            "timestamp": event.timestamp,
            "frame_idx": event.frame_idx,
            "bbox": event.bbox,
            "details": event.details,
            "snapshot_file": str(snapshot_path),
            "plate_file": plate_path_str,
            "video_file": video_path_str,
        }

        meta_file = event_dir / "metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        return {
            "snapshot_path": str(snapshot_path),
            "plate_crop_path": plate_path_str,
            "video_clip_path": video_path_str,
            "metadata_path": str(meta_file),
        }
