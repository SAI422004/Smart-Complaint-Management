import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ChatRequest, ChatResponse
from app.agent.graph import run_agent
from app.services.complaint_service import ComplaintService
from app.services.duplicate_detection import DuplicateDetectionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complaint", tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Main chat endpoint for the AIVOA Copilot.
    Accepts a natural-language message and optional complaint_id for edits.
    Returns the AI reply, updated complaint data, and risk assessment.
    """
    # Rate limiting is handled via middleware in main.py

    result = run_agent(
        user_message=request.message,
        db=db,
        active_complaint_id=request.complaint_id,
    )

    svc = ComplaintService(db)
    complaint = None
    risk = None

    if result.get("active_complaint_id"):
        complaint = svc.get_complaint(result["active_complaint_id"])
        if complaint:
            risk = svc.get_latest_risk_assessment(complaint.complaint_id)

    return ChatResponse(
        reply=result.get("reply_text", ""),
        complaint=complaint.to_dict() if complaint else None,
        risk_assessment=risk.to_dict() if risk else None,
        updated_fields=result.get("updated_fields", []),
    )
