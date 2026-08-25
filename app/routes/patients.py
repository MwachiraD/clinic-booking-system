from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.appointment_response import AppointmentResponse
from app.services.patient_appointments import (
    get_upcoming_patient_appointments,
)


router = APIRouter()


@router.get(
    "/patients/{patient_id}/appointments",
    response_model=list[AppointmentResponse]
)
def get_patient_appointments(
    patient_id: int,
    db: Session = Depends(get_db)
):
    return get_upcoming_patient_appointments(
        db=db,
        patient_id=patient_id
    )