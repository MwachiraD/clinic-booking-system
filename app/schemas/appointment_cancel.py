from pydantic import BaseModel


class AppointmentCancel(BaseModel):
    cancellation_reason: str