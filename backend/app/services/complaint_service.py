from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy.orm import Session

from app.models import Complaint, ComplaintStatus, RiskAssessment, ComplaintChange
from app.schemas import sanitize_text


class ComplaintService:
    """Service layer for complaint CRUD operations with audit trail."""

    def __init__(self, db: Session):
        self.db = db

    def generate_display_id(self) -> str:
        """Generate a complaint display ID like CMP-2026-0001."""
        year = datetime.utcnow().year
        count = self.db.query(Complaint).filter(
            Complaint.display_id.like(f"CMP-{year}-%")
        ).count()
        return f"CMP-{year}-{count + 1:04d}"

    def create_complaint(self, data: Dict[str, Any]) -> Complaint:
        """Create a new complaint record from extracted data."""
        complaint = Complaint(
            display_id=self.generate_display_id(),
            date_received=datetime.utcnow(),
            complainant=sanitize_text(data.get("complainant")),
            product_name=sanitize_text(data.get("product_name")),
            product_strength=sanitize_text(data.get("product_strength")),
            batch_number=sanitize_text(data.get("batch_number")),
            manufacturing_date=data.get("manufacturing_date"),
            expiry_date=data.get("expiry_date"),
            affected_quantity_value=data.get("affected_quantity", {}).get("value") if isinstance(data.get("affected_quantity"), dict) else data.get("affected_quantity_value"),
            affected_quantity_unit=data.get("affected_quantity", {}).get("unit") if isinstance(data.get("affected_quantity"), dict) else data.get("affected_quantity_unit"),
            complaint_category=data.get("complaint_category"),
            complaint_description=sanitize_text(data.get("complaint_description")),
            market_region=sanitize_text(data.get("market_region")),
            status=ComplaintStatus.NEW.value,
        )
        self.db.add(complaint)
        self.db.commit()
        self.db.refresh(complaint)

        # Log the creation in audit trail
        self._log_change(complaint.complaint_id, "complaint_created", None, complaint.display_id)
        for field in ["complainant", "product_name", "batch_number", "complaint_description"]:
            val = getattr(complaint, field)
            if val:
                self._log_change(complaint.complaint_id, field, None, val)

        return complaint

    def update_complaint(
        self, complaint_id: int, data: Dict[str, Any], updated_fields: List[str]
    ) -> Optional[Complaint]:
        """Patch an existing complaint, logging each changed field."""
        complaint = self.db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()
        if not complaint:
            return None

        field_map = {
            "complainant": "complainant",
            "product_name": "product_name",
            "product_strength": "product_strength",
            "batch_number": "batch_number",
            "manufacturing_date": "manufacturing_date",
            "expiry_date": "expiry_date",
            "affected_quantity_value": "affected_quantity_value",
            "affected_quantity_unit": "affected_quantity_unit",
            "complaint_category": "complaint_category",
            "complaint_description": "complaint_description",
            "market_region": "market_region",
        }

        for field in updated_fields:
            db_field = field_map.get(field)
            if db_field is None:
                continue

            # Determine the new value from data
            if field == "affected_quantity_value" and isinstance(data.get("affected_quantity"), dict):
                new_val = data.get("affected_quantity", {}).get("value")
            elif field == "affected_quantity_unit" and isinstance(data.get("affected_quantity"), dict):
                new_val = data.get("affected_quantity", {}).get("unit")
            else:
                new_val = data.get(field)

            if new_val is not None:
                old_val = getattr(complaint, db_field)
                setattr(complaint, db_field, sanitize_text(str(new_val)) if isinstance(new_val, str) else new_val)
                self._log_change(complaint_id, field, old_val, new_val)

        complaint.updated_at = datetime.utcnow()
        complaint.status = ComplaintStatus.UNDER_INVESTIGATION.value
        self.db.commit()
        self.db.refresh(complaint)
        return complaint

    def get_complaint(self, complaint_id: int) -> Optional[Complaint]:
        return self.db.query(Complaint).filter(Complaint.complaint_id == complaint_id).first()

    def get_all_complaints(self, limit: int = 50, offset: int = 0):
        return (
            self.db.query(Complaint)
            .order_by(Complaint.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def save_risk_assessment(
        self, complaint_id: int, severity: str, next_action: str, rationale: str, confidence: Optional[float] = None
    ) -> RiskAssessment:
        ra = RiskAssessment(
            complaint_fk=complaint_id,
            severity=severity,
            next_action=sanitize_text(next_action),
            rationale=sanitize_text(rationale),
            confidence=confidence,
        )
        self.db.add(ra)
        self.db.commit()
        self.db.refresh(ra)
        return ra

    def get_latest_risk_assessment(self, complaint_id: int) -> Optional[RiskAssessment]:
        return (
            self.db.query(RiskAssessment)
            .filter(RiskAssessment.complaint_fk == complaint_id)
            .order_by(RiskAssessment.created_at.desc())
            .first()
        )

    def _log_change(self, complaint_id: int, field_name: str, old_value: Any, new_value: Any):
        change = ComplaintChange(
            complaint_fk=complaint_id,
            field_name=field_name,
            old_value=str(old_value) if old_value is not None else None,
            new_value=str(new_value) if new_value is not None else None,
            changed_by="AI_Copilot",
        )
        self.db.add(change)
        self.db.commit()
