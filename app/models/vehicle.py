from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
import datetime

from app.models.base import Base

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    license_plate = Column(String(50), nullable=False, index=True)
    vehicle_type = Column(String(50), nullable=True) # e.g., car, motorcycle, truck
    owner_name = Column(String(100), nullable=True)
    phone_number = Column(String(20), nullable=True) # For WhatsApp notifications
    color = Column(String(50), nullable=True)
    speed = Column(Float, nullable=True) # speed in km/h or m/s
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Optional foreign key to persons table
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=True)
    
    # Relationship back to Person
    person = relationship("Person", back_populates="vehicles")
