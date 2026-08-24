from sqlalchemy import Column, Integer, String, DateTime, Index
from sqlalchemy import ForeignKey

from sqlalchemy.orm import relationship
from app.database import Base

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable= False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable= False)
    slot_start_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)
    cancellation_reason = Column(String, nullable=True)
    doctor = relationship("Doctor" , back_populates = "appointments")
    patient = relationship( "Patient" , back_populates = "appointments")
    
    __table_args__ = (
        Index(
            "uq_active_doctor_slot",
            "doctor_id",
            "slot_start_time",
            unique=True,
            postgresql_where=(status == "confirmed"),
        ),
    )