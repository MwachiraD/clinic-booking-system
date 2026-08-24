from sqlalchemy import Column, Integer, String
    
from sqlalchemy.orm import relationship
from app.database import Base

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    working_hours = relationship("WorkingHours", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")