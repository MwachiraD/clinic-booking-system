from datetime import date, datetime, time, timedelta, timezone

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.working_hours import WorkingHours
from app.models.appointment import Appointment


def create_doctor_and_patient(db_session, appointment_date):
    doctor = Doctor(
        name="Test Doctor"
    )

    patient = Patient(
        name="Test Patient",
        email="test@example.com",
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

    return doctor, patient


def future_date():
    return date.today() + timedelta(days=2)


def test_successful_booking(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["doctor_id"] == doctor.id
    assert data["patient_id"] == patient.id
    assert data["status"] == "confirmed"


def test_doctor_not_found(client):

    appointment_date = future_date()

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    response = client.post(
        "/appointments",
        json={
            "doctor_id": 9999,
            "patient_id": 1,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 404


def test_patient_not_found(client, db_session):

    appointment_date = future_date()

    doctor, _ = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": 9999,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 404


def test_booking_outside_working_hours(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(18, 0),
        tzinfo=timezone.utc
    )

    response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 400


def test_booking_less_than_one_hour_ahead(client, db_session):

    appointment_date = date.today()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.now(timezone.utc) + timedelta(minutes=30)

    response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 400


def test_double_booking(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    patient2 = Patient(
        name="Second Patient",
        email="second@example.com",
        phone_number="0798765432"
    )

    db_session.add(patient2)
    db_session.commit()
    db_session.refresh(patient2)

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    first_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert first_response.status_code == 200

    second_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient2.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert second_response.status_code == 409


def test_cancel_appointment(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    booking_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    appointment_id = booking_response.json()["id"]

    response = client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={
            "cancellation_reason": "Patient requested cancellation"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "cancelled"
    assert data["cancellation_reason"] == "Patient requested cancellation"


def test_cancel_already_cancelled_appointment(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    booking_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": slot.isoformat().replace("+00:00", "Z")
        }
    )

    appointment_id = booking_response.json()["id"]

    client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={
            "cancellation_reason": "Patient requested cancellation"
        }
    )

    response = client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={
            "cancellation_reason": "Trying again"
        }
    )

    assert response.status_code == 400


def test_reschedule_appointment(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    original_slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    new_slot = datetime.combine(
        appointment_date,
        time(15, 0),
        tzinfo=timezone.utc
    )

    booking_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": original_slot.isoformat().replace("+00:00", "Z")
        }
    )

    appointment_id = booking_response.json()["id"]

    response = client.patch(
        f"/appointments/{appointment_id}/reschedule",
        json={
            "slot_start_time": new_slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "confirmed"


def test_reschedule_cancelled_appointment(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    original_slot = datetime.combine(
        appointment_date,
        time(14, 0),
        tzinfo=timezone.utc
    )

    new_slot = datetime.combine(
        appointment_date,
        time(15, 0),
        tzinfo=timezone.utc
    )

    booking_response = client.post(
        "/appointments",
        json={
            "doctor_id": doctor.id,
            "patient_id": patient.id,
            "slot_start_time": original_slot.isoformat().replace("+00:00", "Z")
        }
    )

    appointment_id = booking_response.json()["id"]

    client.patch(
        f"/appointments/{appointment_id}/cancel",
        json={
            "cancellation_reason": "Patient requested cancellation"
        }
    )

    response = client.patch(
        f"/appointments/{appointment_id}/reschedule",
        json={
            "slot_start_time": new_slot.isoformat().replace("+00:00", "Z")
        }
    )

    assert response.status_code == 400