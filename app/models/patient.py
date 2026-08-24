from sqlalchemy import Column, Integer, String


from sqlalchemy.orm import relationship
from app.database import Base

class Patient(Base):
    __tablename__ = "patients"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable = False)
    email = Column(String, nullable = False, unique = True) 
    phone_number = Column(String, nullable = False)
    appointments = relationship("Appointment" , back_populates = "patient")