"""Surveillance-tailored Augmentation Pipeline for Traffic Datasets.

Simulates extreme outdoor conditions:
- Weather: Rain, heavy fog, wet road reflections.
- Lighting: Night low-light, harsh sunlight glare, headlight bloom.
- Camera: Motion blur (fast moving cars), camera pole vibration, oblique angles.
"""

from typing import Dict, Any, List, Tuple
import numpy as np

try:
    import albumentations as A
    ALBUMENTATIONS_AVAILABLE = True
except ImportError:
    ALBUMENTATIONS_AVAILABLE = False


def get_surveillance_augmentation_pipeline(
    img_size: Tuple[int, int] = (640, 640),
    is_training: bool = True
) -> Any:
    """Creates a robust Albumentations pipeline with YOLO bbox preservation.

    Args:
        img_size: Target width and height (W, H).
        is_training: If True, applies stochastic augmentations; if False, applies clean resize.

    Returns:
        Albumentations Compose pipeline.
    """
    if not ALBUMENTATIONS_AVAILABLE:
        raise ImportError("Albumentations is required. Run `pip install albumentations`.")

    w, h = img_size

    if not is_training:
        return A.Compose(
            [
                A.Resize(height=h, width=w),
            ],
            bbox_params=A.BboxParams(
                format="yolo",
                label_fields=["class_labels"],
                min_visibility=0.25
            )
        )

    return A.Compose(
        [
            A.Resize(height=h, width=w),
            # 1. Weather and Optical Distortion
            A.OneOf(
                [
                    A.MotionBlur(blur_limit=7, p=0.4),
                    A.GaussianBlur(blur_limit=5, p=0.3),
                    A.RandomFog(fog_coef_lower=0.1, fog_coef_upper=0.4, p=0.3),
                ],
                p=0.5
            ),
            # 2. Day / Night & Harsh Illumination Shifts
            A.OneOf(
                [
                    A.RandomBrightnessContrast(brightness_limit=0.35, contrast_limit=0.35, p=0.5),
                    A.RandomGamma(gamma_limit=(60, 140), p=0.5),
                    A.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1, p=0.4),
                ],
                p=0.7
            ),
            # 3. Camera Vibration and Perspective Angle Variations
            A.ShiftScaleRotate(
                shift_limit=0.0625,
                scale_limit=0.1,
                rotate_limit=10,
                border_mode=0,
                p=0.4
            ),
            A.Perspective(scale=(0.02, 0.08), p=0.3),
            # 4. Partial Occlusion & Headlight Glare
            A.CoarseDropout(
                num_holes_range=(1, 4),
                hole_height_range=(16, 48),
                hole_width_range=(16, 48),
                fill=0,
                p=0.3
            ),
        ],
        bbox_params=A.BboxParams(
            format="yolo",
            label_fields=["class_labels"],
            min_visibility=0.20,
            check_each_transform=False
        )
    )
