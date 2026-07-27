from typing import Optional, List, Dict, Any
from typing_extensions import TypedDict


class AgentState(TypedDict):
    """Represents the state of the LangGraph agent at any point in the graph."""

    # Original user input
    user_message: str
    uploaded_text: Optional[str]
    uploaded_filename: Optional[str]

    # Classification
    intent: Optional[str]

    # Extracted / structured complaint data
    extracted_data: Optional[Dict[str, Any]]

    # Validation
    validation_errors: List[str]
    validation_retries: int

    # The active complaint being worked on
    active_complaint_id: Optional[int]
    active_complaint_data: Optional[Dict[str, Any]]

    # Merge tracking
    updated_fields: List[str]

    # Duplicate detection
    duplicate_info: Optional[Dict[str, Any]]

    # Risk assessment output
    risk_assessment: Optional[Dict[str, Any]]

    # Final response to user
    reply_text: str

    # Warnings / flags for the user
    warnings: List[str]

    # Completion flag for conditional edges
    confirmation_needed: bool


def initial_state(user_message: str) -> AgentState:
    return {
        "user_message": user_message,
        "uploaded_text": None,
        "uploaded_filename": None,
        "intent": None,
        "extracted_data": None,
        "validation_errors": [],
        "validation_retries": 0,
        "active_complaint_id": None,
        "active_complaint_data": None,
        "updated_fields": [],
        "duplicate_info": None,
        "risk_assessment": None,
        "reply_text": "",
        "warnings": [],
        "confirmation_needed": False,
    }
