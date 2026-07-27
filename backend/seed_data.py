"""
Seed the database with sample complaint data for demo and testing.
Run: python seed_data.py
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Ensure the app module is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal, engine, Base
from app.models import Complaint, ComplaintStatus, RiskAssessment
from app.services.complaint_service import ComplaintService


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    svc = ComplaintService(db)

    # Check if data already exists
    existing = db.query(Complaint).count()
    if existing > 0:
        print(f"Database already has {existing} complaint(s). Skipping seed.")
        db.close()
        return

    # Sample complaint 1: Discolored capsules
    c1 = Complaint(
        display_id=svc.generate_display_id(),
        date_received=datetime(2026, 7, 20),
        complainant="Apollo Pharmacy",
        product_name="Amoxicillin Capsules",
        product_strength="500mg",
        batch_number="BMX240601",
        manufacturing_date=datetime(2026, 1, 15),
        expiry_date=datetime(2028, 1, 14),
        affected_quantity_value=48.0,
        affected_quantity_unit="capsules",
        complaint_category="Discoloration",
        complaint_description="Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500mg. Batch BMX240601. The capsules showed abnormal yellow-brown discoloration instead of standard white.",
        market_region="India",
        status=ComplaintStatus.UNDER_INVESTIGATION.value,
    )
    db.add(c1)
    db.commit()
    db.refresh(c1)

    # Risk assessment for c1
    ra1 = RiskAssessment(
        complaint_fk=c1.complaint_id,
        severity="Major",
        next_action="Route to QA investigation and initiate batch retention sampling.",
        rationale="Product quality deviation (discoloration) in a batch of oral solid dosage form. Discoloration may indicate degradation or contamination, requiring full QA investigation.",
        confidence=0.85,
    )
    db.add(ra1)

    # Sample complaint 2: Packaging defect
    c2 = Complaint(
        display_id=svc.generate_display_id(),
        date_received=datetime(2026, 7, 22),
        complainant="City Med Distributors",
        product_name="Paracetamol Tablets",
        product_strength="650mg",
        batch_number="PCM260703B",
        manufacturing_date=datetime(2026, 3, 10),
        expiry_date=datetime(2028, 3, 9),
        affected_quantity_value=200.0,
        affected_quantity_unit="tablets",
        complaint_category="Packaging Defect",
        complaint_description="Blister pack seals were found compromised in 3 out of 50 strips. Tablets exposed to air, possible contamination risk.",
        market_region="India",
        status=ComplaintStatus.NEW.value,
    )
    db.add(c2)
    db.commit()
    db.refresh(c2)

    ra2 = RiskAssessment(
        complaint_fk=c2.complaint_id,
        severity="Major",
        next_action="Initiate batch recall review and replace affected strips.",
        rationale="Compromised packaging integrity in a tablet product. Although limited to 3 strips, the integrity breach could affect product sterility and efficacy.",
        confidence=0.75,
    )
    db.add(ra2)

    db.commit()
    db.close()
    print(f"Seeded database with 2 sample complaints and risk assessments.")


if __name__ == "__main__":
    seed()
