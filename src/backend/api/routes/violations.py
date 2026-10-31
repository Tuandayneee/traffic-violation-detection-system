"""REST API Endpoints for Violation Tickets & Review Management."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ...db.session import get_db
from ...db.models import ViolationRecord

router = APIRouter(prefix="/api/violations", tags=["Violations"])


class ReviewRequest(BaseModel):
    status: str # "APPROVED" or "REJECTED"
    notes: Optional[str] = None


@router.get("")
def list_violations(
    status: Optional[str] = Query(None, description="Filter by status: PENDING, APPROVED, REJECTED"),
    violation_type: Optional[str] = Query(None, description="Filter by violation type"),
    license_plate: Optional[str] = Query(None, description="Search by plate number"),
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Retrieves paginated violation records with optional filters."""
    query = db.query(ViolationRecord)

    if status:
        query = query.filter(ViolationRecord.status == status.upper())
    if violation_type:
        query = query.filter(ViolationRecord.violation_type == violation_type)
    if license_plate:
        query = query.filter(ViolationRecord.license_plate.ilike(f"%{license_plate}%"))

    total = query.count()
    items = query.order_by(ViolationRecord.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": v.id,
                "event_id": v.event_id,
                "camera_id": v.camera_id,
                "violation_type": v.violation_type,
                "vehicle_type": v.vehicle_type,
                "license_plate": v.license_plate,
                "confidence": v.confidence,
                "plate_confidence": v.plate_confidence,
                "status": v.status,
                "reviewer_notes": v.reviewer_notes,
                "snapshot_path": v.snapshot_path,
                "plate_crop_path": v.plate_crop_path,
                "video_clip_path": v.video_clip_path,
                "timestamp": v.timestamp,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in items
        ]
    }


@router.get("/stats/summary")
def get_violation_stats(db: Session = Depends(get_db)):
    """Computes high-level violation metrics and breakdown."""
    total = db.query(ViolationRecord).count()
    pending = db.query(ViolationRecord).filter(ViolationRecord.status == "PENDING").count()
    approved = db.query(ViolationRecord).filter(ViolationRecord.status == "APPROVED").count()
    rejected = db.query(ViolationRecord).filter(ViolationRecord.status == "REJECTED").count()

    # Breakdown by type
    from sqlalchemy import func
    breakdown = db.query(
        ViolationRecord.violation_type,
        func.count(ViolationRecord.id)
    ).group_by(ViolationRecord.violation_type).all()

    return {
        "total_violations": total,
        "pending_review": pending,
        "approved": approved,
        "rejected": rejected,
        "breakdown": {b[0]: b[1] for b in breakdown}
    }


@router.get("/{violation_id}")
def get_violation(violation_id: int, db: Session = Depends(get_db)):
    """Returns detailed information of a single violation."""
    v = db.query(ViolationRecord).filter(ViolationRecord.id == violation_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Violation record not found")
    return v


@router.post("/{violation_id}/review")
def review_violation(
    violation_id: int,
    req: ReviewRequest,
    db: Session = Depends(get_db)
):
    """Approves or rejects a violation ticket by reviewing officer."""
    v = db.query(ViolationRecord).filter(ViolationRecord.id == violation_id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Violation record not found")

    status_upper = req.status.upper()
    if status_upper not in ["APPROVED", "REJECTED"]:
        raise HTTPException(status_code=400, detail="Status must be APPROVED or REJECTED")

    v.status = status_upper
    v.reviewer_notes = req.notes
    db.commit()
    db.refresh(v)

    return {"message": "Violation reviewed successfully", "id": v.id, "status": v.status}
