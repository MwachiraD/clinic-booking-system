from sqlalchemy import Column, Integer, String, Time 
from sqlalchemy import ForeignKey

from sqlalchemy.orm import relationship
from app.database import Base


class WorkingHours(Base):
    __tablename__ = "working_hours"
    id = Column(Integer, primary_key = True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable= False)
    day_of_week = Column(String, nullable = False) 
    start_time = Column( Time , nullable = False)
    end_time = Column (Time, nullable = False)
    doctor = relationship("Doctor" , back_populates = "working_hours")