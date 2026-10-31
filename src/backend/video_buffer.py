"""Thread-safe Circular Frame Ring Buffer for Video Snippet Extraction."""

from collections import deque
from typing import List, Tuple, Optional
import threading
import numpy as np
import cv2
from pathlib import Path


class FrameRingBuffer:
    """Maintains a rolling window of recent video frames to generate pre/post event clips."""

    def __init__(self, capacity: int = 150):
        self.capacity = capacity
        self._buffer: deque = deque(maxlen=capacity)
        self._lock = threading.Lock()

    def push(self, frame: np.ndarray, frame_idx: int, timestamp: float):
        """Pushes a copy of a frame into the ring buffer."""
        with self._lock:
            self._buffer.append({
                "frame": frame.copy(),
                "frame_idx": frame_idx,
                "timestamp": timestamp
            })

    def export_video_clip(
        self,
        output_path: str,
        fps: int = 30,
        num_frames: Optional[int] = None
    ) -> bool:
        """Encodes frames in the buffer into an MP4 video file.

        Args:
            output_path: Destination .mp4 file path.
            fps: Frame rate for encoding.
            num_frames: Number of most recent frames to export. None exports all.
        """
        with self._lock:
            if not self._buffer:
                return False
            frames_to_write = list(self._buffer)

        if num_frames is not None and num_frames < len(frames_to_write):
            frames_to_write = frames_to_write[-num_frames:]

        if not frames_to_write:
            return False

        h, w = frames_to_write[0]["frame"].shape[:2]
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(dest), fourcc, fps, (w, h))

        try:
            for item in frames_to_write:
                writer.write(item["frame"])
            return True
        finally:
            writer.release()
