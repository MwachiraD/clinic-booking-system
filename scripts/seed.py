from datetime import time

from sqlalchemy import select

from app.database import SessionLocal

from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.working_hours import WorkingHours


DOCTORS = [
    "Dr. Jane Doe",
    "Dr. John Smith",
    "Dr. Alice Mwangi",
    "Dr. David Kamau",
    "Dr. Sarah Wanjiku",
]

PATIENTS = [
    {
        "name": "John Doe",
        "email": "john.doe@example.com",
        "phone_number": "0712345678",
    },
    {
        "name": "Mary Wanjiku",
        "email": "mary.wanjiku@example.com",
        "phone_number": "0723456789",
    },
]

DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
]


def seed():
    db = SessionLocal()

    try:
        doctors = []

        for doctor_name in DOCTORS:
            doctor = db.scalar(
                select(Doctor).where(Doctor.name == doctor_name)
            )

            if doctor is None:
                doctor = Doctor(name=doctor_name)
                db.add(doctor)
                db.flush()

            doctors.append(doctor)

            for day in DAYS:
                working_hour = db.scalar(
                    select(WorkingHours).where(
                        WorkingHours.doctor_id == doctor.id,
                        WorkingHours.day_of_week == day,
                    )
                )

                if working_hour is None:
                    db.add(
                        WorkingHours(
                            doctor_id=doctor.id,
                            day_of_week=day,
                            start_time=time(9, 0),
                            end_time=time(17, 0),
                        )
                    )

        patients = []

        for patient_data in PATIENTS:
            patient = db.scalar(
                select(Patient).where(
                    Patient.email == patient_data["email"]
                )
            )

            if patient is None:
                patient = Patient(**patient_data)
                db.add(patient)
                db.flush()

            patients.append(patient)

        db.commit()

        print("Seed data created successfully.")
        print(f"Doctors: {len(doctors)}")
        print(f"Patients: {len(patients)}")
        print("Working hours: Monday-Friday, 09:00-17:00")

        for doctor in doctors:
            print(f"Doctor ID {doctor.id}: {doctor.name}")

        for patient in patients:
            print(f"Patient ID {patient.id}: {patient.name}")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()