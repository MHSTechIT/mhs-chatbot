from sqlalchemy import Column, String, DateTime, func, Text
from src.database import Base
from datetime import datetime

class Document(Base):
    """Model for storing uploaded documents from admin dashboard."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    type = Column(String(50), nullable=False)  # 'document' or 'link'
    file_name = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    storage_path = Column(String(500), nullable=True)  # Alternative column name used in database
    url = Column(String(500), nullable=True)
    content = Column(Text, nullable=True)  # Document content for searching
    created_at = Column(DateTime, server_default=func.now(), nullable=False)  # Matches database schema

    def __repr__(self):
        return f"<Document(id={self.id}, title={self.title}, type={self.type})>"
