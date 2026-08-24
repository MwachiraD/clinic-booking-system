
from pydantic import BaseModel
from datetime import date, time

class AvailabilityResponse(BaseModel):
    doctor_id: int
    date: date
    available_slots: list[time]