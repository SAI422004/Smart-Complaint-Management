import logging
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import Complaint

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Detect duplicate complaints by exact product_name + batch_number match,
    or by fuzzy text similarity on the complaint description."""

    def __init__(self, db: Session):
        self.db = db

    def find_duplicate(
        self,
        product_name: Optional[str] = None,
        batch_number: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[Complaint]:
        """
        Find a duplicate complaint. Priority:
        1. Exact match on (product_name, batch_number)
        2. Text similarity on description (simple word overlap)
        """
        # Priority 1: Exact product + batch match
        if product_name and batch_number:
            exact = (
                self.db.query(Complaint)
                .filter(
                    Complaint.product_name == product_name,
                    Complaint.batch_number == batch_number,
                )
                .first()
            )
            if exact:
                logger.info(f"Duplicate found: exact match on product+ batch -> {exact.display_id}")
                return exact

        # Priority 2: Text similarity on description (simple word overlap)
        if description:
            all_complaints = (
                self.db.query(Complaint)
                .filter(Complaint.complaint_description.isnot(None))
                .all()
            )
            words_new = set(description.lower().split())
            if len(words_new) < 5:
                return None

            best_match = None
            best_score = 0.0

            for c in all_complaints:
                if not c.complaint_description:
                    continue
                words_existing = set(c.complaint_description.lower().split())
                if len(words_existing) < 3:
                    continue
                intersection = words_new & words_existing
                union = words_new | words_existing
                jaccard = len(intersection) / len(union) if union else 0.0
                if jaccard > best_score:
                    best_score = jaccard
                    best_match = c

            # Threshold: Jaccard similarity > 0.5 indicates likely duplicate
            if best_score > 0.5 and best_match:
                logger.info(f"Duplicate found: text similarity {best_score:.2f} -> {best_match.display_id}")
                return best_match

        return None
