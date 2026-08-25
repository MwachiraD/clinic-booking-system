from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.patient import Patient


def get_upcoming_patient_appointments(
    db: Session,
    patient_id: int
):
    # Check that the patient exists
    query = select(Patient).where(
        Patient.id == patient_id
    )

    result = db.execute(query)
    patient = result.scalar_one_or_none()

    if patient is None:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )

    # Get upcoming appointments
    now = datetime.now(timezone.utc)

    query = (
        select(Appointment)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.slot_start_time > now,
            Appointment.status == "confirmed"
        )
        .order_by(Appointment.slot_start_time)
    )

    result = db.execute(query)

    return result.scalars().all()