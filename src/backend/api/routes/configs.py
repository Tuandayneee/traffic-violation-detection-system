"""Camera Calibration & ROI Configuration Endpoints."""

import json
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

router = APIRouter(prefix="/api/config", tags=["Configuration"])

DEFAULT_CONFIG_PATH = Path("configs/camera_intersection_01.json")


class RoiUpdateRequest(BaseModel):
    config: Dict[str, Any]


@router.get("/camera")
def get_camera_roi_config():
    """Returns the current intersection geometry and ROI settings."""
    if not DEFAULT_CONFIG_PATH.exists():
        raise HTTPException(status_code=404, detail="Configuration file not found")

    with open(DEFAULT_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


@router.put("/camera")
def update_camera_roi_config(req: RoiUpdateRequest):
    """Updates the stop line, lanes, and traffic light coordinates."""
    try:
        with open(DEFAULT_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(req.config, f, indent=2, ensure_ascii=False)
        return {"message": "Camera ROI configuration updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
