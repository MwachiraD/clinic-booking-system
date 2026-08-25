from datetime import date, datetime, time, timedelta, timezone

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.working_hours import WorkingHours


def future_date():
    return date.today() + timedelta(days=2)


def create_doctor_and_patient(db_session, appointment_date):
    doctor = Doctor(
        name="Test Doctor"
    )

    patient = Patient(
        name="Test Patient",
        email="availability@example.com",
        phone_number="0711111111"
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


def test_booked_slot_not_available(client, db_session):

    appointment_date = future_date()

    doctor, patient = create_doctor_and_patient(
        db_session,
        appointment_date
    )

    slot = datetime.combine(
        appointment_date,
        time(11, 0),
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

    assert booking_response.status_code == 200

    response = client.get(
        f"/doctors/{doctor.id}/availability",
        params={"day": appointment_date.isoformat()}
    )

    assert response.status_code == 200

    data = response.json()

    assert "11:00:00" not in data["available_slots"]