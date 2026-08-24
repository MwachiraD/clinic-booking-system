from datetime import datetime

from pydantic import BaseModel



class AppointmentCreate(BaseModel):
    doctor_id: int
    patient_id: int
    slot_start_time: datetime