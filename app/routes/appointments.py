from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.appointment_cancel import AppointmentCancel
from app.schemas.appointment_create import AppointmentCreate
from app.schemas.appointment_reschedule import AppointmentReschedule
from app.schemas.appointment_response import AppointmentResponse
from app.services.booking import book_appointment, cancel_appointment, reschedule_appointment



router = APIRouter()

@router.post("/appointments", response_model = AppointmentResponse)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db)
):
    booked_appointment = book_appointment(
        db=db,
        doctor_id=appointment.doctor_id,
        patient_id=appointment.patient_id,
        slot_start_time=appointment.slot_start_time
    )

    return booked_appointment

@router.patch(
    "/appointments/{appointment_id}/cancel",
    response_model=AppointmentResponse
)
def cancel_appointment_route(
    appointment_id: int,
    cancellation: AppointmentCancel,
    db: Session = Depends(get_db)
):

    canceled_appointment = cancel_appointment(
        db=db,
        appointment_id=appointment_id,
        cancellation_reason=cancellation.cancellation_reason
        
    )

    return canceled_appointment

@router.patch(
    "/appointments/{appointment_id}/reschedule",
    response_model=AppointmentResponse
)   
def reschedule_appointment_route(
    appointment_id: int,
    reschedule: AppointmentReschedule,
    db: Session = Depends(get_db)
):
    rescheduled_appointment = reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        new_slot_start_time=reschedule.slot_start_time
    )

    return rescheduled_appointment  