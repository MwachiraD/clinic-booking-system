from pydantic import BaseModel
from datetime import  datetime


class AppointmentReschedule(BaseModel):
    slot_start_time: datetime