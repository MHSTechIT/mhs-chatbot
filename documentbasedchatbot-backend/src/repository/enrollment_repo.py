import logging
from sqlalchemy.orm import Session
from src.models.enrollment import Enrollment

logger = logging.getLogger(__name__)

class EnrollmentRepository:
    """Repository for managing enrollment submissions."""

    @staticmethod
    def create_enrollment(db: Session, name: str, phone: str, age: int, location: str, sugar_level: str = None) -> Enrollment:
        """Save enrollment submission to database."""
        try:
            enrollment = Enrollment(
                name=name.strip(),
                phone=phone.strip(),
                age=age,
                location=location.strip(),
                sugar_level=sugar_level.strip() if sugar_level else None
            )
            db.add(enrollment)
            db.commit()
            db.refresh(enrollment)
            logger.info(f"✅ Enrollment saved: {enrollment.id} - {enrollment.name} ({enrollment.phone}) from {location}")
            return enrollment
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error saving enrollment: {str(e)}")
            raise

    @staticmethod
    def get_enrollment(db: Session, enrollment_id: int) -> Enrollment:
        """Retrieve enrollment by ID."""
        return db.query(Enrollment).filter(Enrollment.id == enrollment_id).first()

    @staticmethod
    def get_all_enrollments(db: Session, limit: int = 100) -> list:
        """Retrieve all enrollments."""
        return db.query(Enrollment).order_by(Enrollment.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_enrollments_paginated(db: Session, limit: int = 20, offset: int = 0):
        """Retrieve enrollments with pagination. Returns (rows, total_count)."""
        query = db.query(Enrollment).order_by(Enrollment.created_at.desc())
        total = query.count()
        rows = query.offset(offset).limit(limit).all()
        return rows, total

    @staticmethod
    def get_enrollments_by_phone(db: Session, phone: str) -> list:
        """Retrieve enrollments by phone number."""
        return db.query(Enrollment).filter(Enrollment.phone == phone.strip()).all()
