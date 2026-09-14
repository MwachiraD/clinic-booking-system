from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Appointment , Patient, Doctor

from app.services.availability import (
    get_working_hours,
    generate_daily_slots,
)


def book_appointment(
    db: Session,
    doctor_id: int,
    patient_id: int,
    slot_start_time: datetime,
):
    # Store and compare appointment instants consistently, regardless of the
    # timezone offset supplied by the API client.
    if slot_start_time.tzinfo is None:
        slot_start_time = slot_start_time.replace(tzinfo=timezone.utc)  
    else:
        slot_start_time = slot_start_time.astimezone(timezone.utc)

    slot_start_time = slot_start_time.replace(microsecond=0)

    query = select(Doctor).where(
        Doctor.id == doctor_id
    )

    result = db.execute(query)
    doctor = result.scalar_one_or_none()

    if doctor is None:
        raise HTTPException(
            status_code=404,
            detail="Doctor not found"
        )

    # 2. Check that the patient exists
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

    min_booking_time = datetime.now(timezone.utc) + timedelta(hours=1)

    if slot_start_time < min_booking_time:
        raise HTTPException(
            status_code=400,
            detail="Appointments must be booked at least 1 hour in advance"
        )

    # Valid slots are derived from the doctor's recurring working hours rather
    # than stored independently, so schedule changes cannot leave stale slots.
    working_hours = get_working_hours(
        db,
        doctor_id,
        slot_start_time.date()
    )

    valid_slots = generate_daily_slots(
        slot_start_time.date(),
        working_hours
    )

    if slot_start_time not in valid_slots:
        raise HTTPException(
            status_code=400,
            detail="Slot is not within the doctor's working hours"
        )

    # This pre-check returns a clear error in the common case. The partial
    # unique index remains the authoritative protection if requests race.
    query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.slot_start_time == slot_start_time,
        Appointment.status == "confirmed"
    )

    result = db.execute(query)
    existing_appointment = result.scalar_one_or_none()

    if existing_appointment is not None:
        raise HTTPException(
            status_code=409,
            detail="Requested slot is already booked"
        )

    appointment = Appointment(
        doctor_id=doctor_id,
        patient_id=patient_id,
        slot_start_time=slot_start_time,
        status="confirmed"
    )

    db.add(appointment)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="This slot is no longer available"
        )

    db.refresh(appointment)

    return appointment



def cancel_appointment(
    db: Session,
    appointment_id: int,
    cancellation_reason: str
):
    query = select(Appointment).where(
        Appointment.id == appointment_id
    )
    
    result = db.execute(query)
    
    appointment = result.scalar_one_or_none()
    
    if appointment is None:
        raise HTTPException(
            status_code = 404,
            detail = "Appointment not found"
        )
    if appointment.status == "cancelled":
        raise HTTPException(
            status_code = 400,
            detail = "Appointment already cancelled"
        )
        
    appointment.status = "cancelled"
    appointment.cancellation_reason = cancellation_reason
    
    db.commit()
    
    db.refresh(appointment)
    return appointment
    
    
def reschedule_appointment(
    db: Session,
    appointment_id: int,
    new_slot_start_time: datetime
):
    if new_slot_start_time.tzinfo is None:
        new_slot_start_time = new_slot_start_time.replace(tzinfo=timezone.utc)
    else:
        new_slot_start_time = new_slot_start_time.astimezone(timezone.utc)

    new_slot_start_time = new_slot_start_time.replace(microsecond=0)
    
    query = select(Appointment).where(
        Appointment.id == appointment_id
    )
    
    result = db.execute(query)
    appointment = result.scalar_one_or_none()
    
    if appointment is None:
        raise HTTPException(
            status_code = 404,
            detail = "Appointment not found"
        )
        
    if appointment.status != "confirmed":
        raise HTTPException(
            status_code = 400, 
            detail = "only confirmed appointments can be rescheduled"
        )
        
    min_booking_time = datetime.now(timezone.utc) + timedelta(hours=1)

    if new_slot_start_time < min_booking_time:
        raise HTTPException(
            status_code = 400,
            detail="Rescheduled appointments must be at least 1 hour in advance"
        )
        
    working_hours = get_working_hours(
        db, 
        appointment.doctor_id,
        new_slot_start_time.date()
    )
    
    valid_slots = generate_daily_slots(
        new_slot_start_time.date(),
        working_hours
    )
    
    if new_slot_start_time not in valid_slots:
        raise HTTPException(
            status_code = 400,
            detail="Slot is not within the doctor's working hours"
        )
        
    query = select(Appointment).where(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.slot_start_time == new_slot_start_time,
        Appointment.status == "confirmed",
        Appointment.id != appointment_id
    )
    
    result = db.execute(query)
    existing_appointment = result.scalar_one_or_none()
    
    if existing_appointment is not None:
        raise HTTPException(
            status_code = 409, 
            detail = "The slot is already booked. Please choose another time"
        )

    # The appointment is updated only after the new slot has passed every
    # validation check, so a failed reschedule leaves the original slot intact.
    appointment.slot_start_time = new_slot_start_time
    
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code = 409, 
            detail = "This slot is already booked"
        )
    db.refresh(appointment)
    
    return appointment
