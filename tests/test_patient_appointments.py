from datetime import date, datetime, time, timedelta, timezone

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.working_hours import WorkingHours
from app.models.appointment import Appointment


def create_patient_with_doctor(db_session):
    appointment_date = date.today() + timedelta(days=2)

    doctor = Doctor(
        name="Test Doctor"
    )

    patient = Patient(
        name="Test Patient",
        email="patient@example.com",
        phone_number="0712345678"
    )

    working_hours = WorkingHours(
        doctor=doctor,
        day_of_week=appointment_date.strftime("%A"),
        start_time=time(9, 0),
        end_time=time(17, 0)
    )

    db_session.add_all([
        doctor,
        patient,
        working_hours
    ])

    db_session.commit()

    db_session.refresh(doctor)
    db_session.refresh(patient)

    return doctor, patient, appointment_date


def test_get_patient_upcoming_appointments_sorted(
    client,
    db_session
):
    doctor, patient, appointment_date = create_patient_with_doctor(
        db_session
    )

    later_appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        slot_start_time=datetime.combine(
            appointment_date,
            time(15, 0),
            tzinfo=timezone.utc
        ),
        status="confirmed"
    )

    earlier_appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        slot_start_time=datetime.combine(
            appointment_date,
            time(10, 0),
            tzinfo=timezone.utc
        ),
        status="confirmed"
    )

    db_session.add_all([
        later_appointment,
        earlier_appointment
    ])

    db_session.commit()

    response = client.get(
        f"/patients/{patient.id}/appointments"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["slot_start_time"] < data[1]["slot_start_time"]


def test_patient_appointments_exclude_cancelled(
    client,
    db_session
):
    doctor, patient, appointment_date = create_patient_with_doctor(
        db_session
    )

    confirmed_appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        slot_start_time=datetime.combine(
            appointment_date,
            time(10, 0),
            tzinfo=timezone.utc
        ),
        status="confirmed"
    )

    cancelled_appointment = Appointment(
        doctor_id=doctor.id,
        patient_id=patient.id,
        slot_start_time=datetime.combine(
            appointment_date,
            time(11, 0),
            tzinfo=timezone.utc
        ),
        status="cancelled",
        cancellation_reason="Patient cancelled"
    )

    db_session.add_all([
        confirmed_appointment,
        cancelled_appointment
    ])

    db_session.commit()

    response = client.get(
        f"/patients/{patient.id}/appointments"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["status"] == "confirmed"


def test_patient_not_found_for_appointments(client):

    response = client.get(
        "/patients/9999/appointments"
    )

    assert response.status_code == 404