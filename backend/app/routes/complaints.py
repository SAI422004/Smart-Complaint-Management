import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ComplaintResponse, SummaryRequest, SummaryResponse
from app.services.complaint_service import ComplaintService
from app.agent.nodes import summary_node
from app.agent.state import initial_state

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.get("/", response_model=list[ComplaintResponse])
def list_complaints(db: Session = Depends(get_db)):
    svc = ComplaintService(db)
    complaints = svc.get_all_complaints()
    return [c.to_dict() for c in complaints]


@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(complaint_id: int, db: Session = Depends(get_db)):
    svc = ComplaintService(db)
    complaint = svc.get_complaint(complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    return complaint.to_dict()


@router.get("/{complaint_id}/risk", response_model=dict)
def get_risk_assessment(complaint_id: int, db: Session = Depends(get_db)):
    svc = ComplaintService(db)
    risk = svc.get_latest_risk_assessment(complaint_id)
    if not risk:
        raise HTTPException(status_code=404, detail="No risk assessment found")
    return risk.to_dict()


@router.post("/summary", response_model=SummaryResponse)
def generate_summary(request: SummaryRequest, db: Session = Depends(get_db)):
    """Generate an AI summary of a complaint record."""
    svc = ComplaintService(db)
    complaint = svc.get_complaint(request.complaint_id)
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    state = initial_state("summarize this complaint")
    state["active_complaint_id"] = request.complaint_id
    result = summary_node(state, db)
    return SummaryResponse(summary=result.get("reply_text", ""))
