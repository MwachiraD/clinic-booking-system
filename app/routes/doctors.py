from datetime import date , datetime, time, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.availability_response import AvailabilityResponse
from app.services.availability import (
    get_working_hours,
    generate_daily_slots,
    get_active_appointments,
)

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
    working_hours = get_working_hours(db=db, doctor_id=doctor_id, day=day)
    daily_slots = generate_daily_slots(day, working_hours)
    active_appointments = get_active_appointments(db=db, doctor_id=doctor_id, day=day)

    booked_slots = {appointment.slot_start_time for appointment in active_appointments}
    min_booking_time = datetime.now() + timedelta(hours=1)
    available_slots = [
        slot for slot in daily_slots if slot not in booked_slots and slot >= min_booking_time]
    available_times= [slot.time() for slot in available_slots]

    return AvailabilityResponse(
        doctor_id=doctor_id,
        date=day,
        available_slots=available_times
    )
