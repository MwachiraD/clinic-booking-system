from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.doctor import Doctor
from app.schemas.availability_response import AvailabilityResponse
from app.services.availability import get_available_slots

NAIROBI = ZoneInfo("Africa/Nairobi")

router = APIRouter()

@router.get(
    "/doctors/{doctor_id}/availability",
    response_model=AvailabilityResponse
)
def get_doctor_availability(
    doctor_id: int,
    day: date,
    db: Session = Depends(get_db)
):
    doctor = db.scalar(select(Doctor).where(Doctor.id == doctor_id))

    if doctor is None:
        raise HTTPException(status_code=404, detail="Doctor not found")
    available_slots = get_available_slots(db=db, doctor_id=doctor_id, day=day)
    available_times = [slot.astimezone(NAIROBI).time() for slot in available_slots]

    return AvailabilityResponse(
        doctor_id=doctor_id,
        date=day,
        available_slots=available_times
    )
