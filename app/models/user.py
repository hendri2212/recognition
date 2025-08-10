from sqlalchemy import Column, Integer, String, LargeBinary, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    embedding = Column(LargeBinary, nullable=False)

    # Foreign key to persons table
    person_id = Column(Integer, ForeignKey("persons.id"), nullable=False)
    # Relationship back to Person
    person = relationship("Person", back_populates="users")