import os
import logging
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.schemas import UploadResponse
from app.agent.graph import run_agent
from app.utils.sanitization import validate_mime_type
from app.utils.file_handler import save_upload, extract_text
from app.services.complaint_service import ComplaintService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/complaint", tags=["upload"])

MAX_UPLOAD_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.post("/upload", response_model=UploadResponse)
async def upload_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a document (PDF, DOCX, TXT, EML) for complaint data extraction.
    The file is saved outside the web root, text is extracted, and the
    LangGraph agent processes it.
    """
    # Validate file size
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )

    # Validate MIME type
    if not validate_mime_type(file.filename or "unknown", file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT, EML.",
        )

    # Save file outside web root
    filepath = save_upload(contents, file.filename or "upload")

    # Extract text
    extracted_text = extract_text(filepath, file.filename or "upload")

    # Run agent on the extracted text
    result = run_agent(
        user_message=f"Document uploaded: {file.filename}",
        db=db,
        uploaded_text=extracted_text,
        uploaded_filename=file.filename,
    )

    svc = ComplaintService(db)
    complaint = None
    if result.get("active_complaint_id"):
        complaint = svc.get_complaint(result["active_complaint_id"])

    return UploadResponse(
        filename=file.filename or "unknown",
        extracted_text=extracted_text[:2000],
        complaint=complaint.to_dict() if complaint else None,
        error=None,
    )
