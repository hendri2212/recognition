from sqlalchemy import Column, Integer, String, LargeBinary
from sqlalchemy.orm import relationship
from app.models.base import Base

class Person(Base):
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    mean_embedding = Column(LargeBinary, nullable=True)

    # Relationship to User samples
    users = relationship('User', back_populates='person')
    
    # Relationship to Vehicle
    vehicles = relationship('Vehicle', back_populates='person')