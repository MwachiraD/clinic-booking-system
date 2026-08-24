from datetime import datetime

from pydantic import BaseModel, ConfigDict



class AppointmentResponse(BaseModel):
    id: int
    doctor_id: int
    patient_id: int
    slot_start_time: datetime
    status: str
    cancellation_reason: str | None
    
    model_config = ConfigDict(from_attributes=True)