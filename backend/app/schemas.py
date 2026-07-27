from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re


def sanitize_text(text: str) -> str:
    """Strip HTML tags and dangerous characters for safe rendering."""
    if not text:
        return text
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#x27;")
    return text


class QuantityModel(BaseModel):
    value: Optional[float] = None
    unit: Optional[str] = None


class ComplaintCreate(BaseModel):
    complainant: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    affected_quantity: Optional[QuantityModel] = None
    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None
    market_region: Optional[str] = None

    @validator("*", pre=True, always=False)
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class ComplaintPatch(BaseModel):
    complainant: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    affected_quantity: Optional[QuantityModel] = None
    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None
    market_region: Optional[str] = None

    @validator("*", pre=True, always=False)
    def sanitize_strings(cls, v):
        if isinstance(v, str):
            return sanitize_text(v)
        return v


class ComplaintResponse(BaseModel):
    complaint_id: int
    display_id: str
    date_received: Optional[str] = None
    complainant: Optional[str] = None
    product_name: Optional[str] = None
    product_strength: Optional[str] = None
    batch_number: Optional[str] = None
    manufacturing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    affected_quantity_value: Optional[float] = None
    affected_quantity_unit: Optional[str] = None
    complaint_category: Optional[str] = None
    complaint_description: Optional[str] = None
    market_region: Optional[str] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RiskAssessmentResponse(BaseModel):
    id: int
    complaint_id: int
    severity: str
    next_action: str
    rationale: str
    confidence: Optional[float] = None
    created_at: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    complaint_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    complaint: Optional[ComplaintResponse] = None
    risk_assessment: Optional[RiskAssessmentResponse] = None
    updated_fields: Optional[List[str]] = None


class DuplicateInfo(BaseModel):
    is_duplicate: bool
    existing_complaint: Optional[ComplaintResponse] = None
    match_reason: Optional[str] = None


class UploadResponse(BaseModel):
    filename: str
    extracted_text: str
    complaint: Optional[ComplaintResponse] = None
    risk_assessment: Optional[RiskAssessmentResponse] = None
    error: Optional[str] = None


class SummaryRequest(BaseModel):
    complaint_id: int


class SummaryResponse(BaseModel):
    summary: str
