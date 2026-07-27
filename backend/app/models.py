import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Enum,
    Float, ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship
from app.database import Base


class ComplaintStatus(str, enum.Enum):
    NEW = "New"
    UNDER_INVESTIGATION = "Under Investigation"
    CLOSED = "Closed"


class ComplaintSeverity(str, enum.Enum):
    MINOR = "Minor"
    MAJOR = "Major"
    CRITICAL = "Critical"


class ComplaintCategory(str, enum.Enum):
    DISCOLORATION = "Discoloration"
    CONTAMINATION = "Contamination"
    PACKAGING_DEFECT = "Packaging Defect"
    SHORT_FILL = "Short-fill"
    LABELING_ERROR = "Labeling Error"
    DEGRADATION = "Degradation"
    OTHER = "Other"


class Complaint(Base):
    __tablename__ = "complaints"

    complaint_id = Column(Integer, primary_key=True, autoincrement=True)
    display_id = Column(String(20), unique=True, nullable=False, index=True)

    date_received = Column(DateTime, default=datetime.utcnow, nullable=False)
    complainant = Column(String(255), nullable=True)
    product_name = Column(String(255), nullable=True)
    product_strength = Column(String(100), nullable=True)
    batch_number = Column(String(100), nullable=True)
    manufacturing_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True)
    affected_quantity_value = Column(Float, nullable=True)
    affected_quantity_unit = Column(String(50), nullable=True)
    complaint_category = Column(String(100), nullable=True)
    complaint_description = Column(Text, nullable=True)
    market_region = Column(String(100), nullable=True)
    status = Column(String(50), default=ComplaintStatus.NEW.value, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    risk_assessments = relationship("RiskAssessment", back_populates="complaint", cascade="all, delete-orphan")
    changes = relationship("ComplaintChange", back_populates="complaint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_complaint_product_batch", "product_name", "batch_number"),
    )

    def to_dict(self):
        return {
            "complaint_id": self.complaint_id,
            "display_id": self.display_id,
            "date_received": self.date_received.isoformat() if self.date_received else None,
            "complainant": self.complainant,
            "product_name": self.product_name,
            "product_strength": self.product_strength,
            "batch_number": self.batch_number,
            "manufacturing_date": self.manufacturing_date.isoformat() if self.manufacturing_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "affected_quantity_value": self.affected_quantity_value,
            "affected_quantity_unit": self.affected_quantity_unit,
            "complaint_category": self.complaint_category,
            "complaint_description": self.complaint_description,
            "market_region": self.market_region,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class RiskAssessment(Base):
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_fk = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False)
    severity = Column(String(50), nullable=False)
    next_action = Column(Text, nullable=False)
    rationale = Column(Text, nullable=False)
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    complaint = relationship("Complaint", back_populates="risk_assessments")

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_fk,
            "severity": self.severity,
            "next_action": self.next_action,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ComplaintChange(Base):
    """Append-only audit/change log for QMS traceability."""
    __tablename__ = "complaint_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    complaint_fk = Column(Integer, ForeignKey("complaints.complaint_id"), nullable=False)
    field_name = Column(String(100), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String(100), default="AI_Copilot", nullable=False)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    complaint = relationship("Complaint", back_populates="changes")

    def to_dict(self):
        return {
            "id": self.id,
            "complaint_id": self.complaint_fk,
            "field_name": self.field_name,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }
