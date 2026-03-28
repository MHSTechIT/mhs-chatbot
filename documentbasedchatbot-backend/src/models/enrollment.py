from sqlalchemy import Column, Integer, String, DateTime, func
from src.database import Base
from datetime import datetime

class Enrollment(Base):
    """Model for storing program enrollment submissions."""
    __tablename__ = "enrollments"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(20), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    location = Column(String(255), nullable=False)
    sugar_level = Column(String(50), nullable=True)  # Optional
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    def __repr__(self):
        return f"<Enrollment(id={self.id}, name={self.name}, phone={self.phone}, age={self.age}, location={self.location}, sugar_level={self.sugar_level})>"
