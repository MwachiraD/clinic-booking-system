from datetime import date, time, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.working_hours import WorkingHours
from app.models.appointment import Appointment


def generate_slots(day: date, start_time: time, end_time: time):
    slots = []

    current = datetime.combine(day, start_time)
    end_datetime = datetime.combine(day, end_time)

    while current + timedelta(minutes=30) <= end_datetime:
        slots.append(current)
        current += timedelta(minutes=30)

    return slots


def generate_daily_slots(day: date, working_hours):
    all_slots = []

    for working_hour in working_hours:
        slots = generate_slots(
            day,
            working_hour.start_time,
            working_hour.end_time
        )

        all_slots.extend(slots)

    return all_slots


def get_working_hours(
    db: Session,
    doctor_id: int,
    day: date
):
    day_name = day.strftime("%A")

    query = select(WorkingHours).where(
        WorkingHours.doctor_id == doctor_id,
        WorkingHours.day_of_week == day_name
    )

    result = db.execute(query)

    return result.scalars().all()


def get_active_appointments(
    db: Session,
    doctor_id: int,
    day: date
):
    start_of_day = datetime.combine(day, time.min)

    next_day = day + timedelta(days=1)

    start_of_next_day = datetime.combine(next_day, time.min)

    query = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status == "confirmed",
        Appointment.slot_start_time >= start_of_day,
        Appointment.slot_start_time < start_of_next_day
    )

    result = db.execute(query)

    appointments = result.scalars().all()

    return appointments


def get_available_slots(
    db: Session,
    doctor_id: int,
    day: date
):
    working_hours = get_working_hours(
        db,
        doctor_id,
        day
    )

    all_slots = generate_daily_slots(
        day,
        working_hours
    )

    appointments = get_active_appointments(
        db,
        doctor_id,
        day
    )

    booked_slots = {
        appointment.slot_start_time
        for appointment in appointments
    }

    min_booking_time = datetime.now() + timedelta(hours = 1)

    available_slots = [
        slot
        for slot in all_slots
        if slot not in booked_slots
        and slot >= min_booking_time
    ]

    return available_slots