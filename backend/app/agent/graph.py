import logging
from typing import Dict, Any, Optional

from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session

from app.agent.state import AgentState, initial_state
from app.agent.nodes import (
    router_node,
    extractor_node,
    validator_node,
    duplicate_detection_node,
    merge_node,
    risk_assessment_node,
    persistence_node,
    responder_node,
    summary_node,
)

logger = logging.getLogger(__name__)


def is_edit_path(state: AgentState) -> str:
    """After extraction, decide: edit path (merge into existing) or new path (validate)."""
    if state.get("active_complaint_id"):
        return "merge"
    return "validator"


def should_retry_validation(state: AgentState) -> str:
    """After validation, retry extraction, ask for clarification, or continue."""
    if state["validation_errors"] and state["validation_retries"] < 2:
        return "extractor"
    if state["validation_errors"]:
        return "responder"
    return "duplicate_check"


def handle_duplicate(state: AgentState) -> str:
    """If duplicate found, respond to user; otherwise continue to risk assessment."""
    dup = state.get("duplicate_info")
    if dup and dup.get("is_duplicate"):
        return "responder"
    return "risk"


def run_agent(
    user_message: str,
    db: Session,
    active_complaint_id: Optional[int] = None,
    uploaded_text: Optional[str] = None,
    uploaded_filename: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the LangGraph agent end-to-end.
    Returns the final state with reply_text, complaint data, risk assessment, etc.
    """
    state = initial_state(user_message)
    state["active_complaint_id"] = active_complaint_id
    state["uploaded_text"] = uploaded_text
    state["uploaded_filename"] = uploaded_filename

    workflow = StateGraph(AgentState)

    workflow.add_node("router", lambda s: router_node(s))
    workflow.add_node("extractor", lambda s: extractor_node(s))
    workflow.add_node("validator", lambda s: validator_node(s))
    workflow.add_node("duplicate_check", lambda s: duplicate_detection_node(s, db))
    workflow.add_node("merge", lambda s: merge_node(s))
    workflow.add_node("risk", lambda s: risk_assessment_node(s))
    workflow.add_node("persist", lambda s: persistence_node(s, db))
    workflow.add_node("responder", lambda s: responder_node(s))
    workflow.add_node("summarizer", lambda s: summary_node(s, db))

    workflow.set_entry_point("router")

    # Router dispatches based on intent
    workflow.add_conditional_edges(
        "router",
        lambda s: s["intent"],
        {
            "new_complaint": "extractor",
            "edit_complaint": "extractor",
            "document_extraction": "extractor",
            "summarize": "summarizer",
            "clarification_needed": "responder",
            "off_topic": "responder",
        },
    )

    # Extractor branches: edit path goes to merge, new path goes to validator
    workflow.add_conditional_edges(
        "extractor",
        is_edit_path,
        {
            "merge": "merge",
            "validator": "validator",
        },
    )

    # Validator: retry, clarify, or continue to duplicate check
    workflow.add_conditional_edges(
        "validator",
        should_retry_validation,
        {
            "extractor": "extractor",
            "responder": "responder",
            "duplicate_check": "duplicate_check",
        },
    )

    # Duplicate check: respond if duplicate, otherwise assess risk
    workflow.add_conditional_edges(
        "duplicate_check",
        handle_duplicate,
        {
            "responder": "responder",
            "risk": "risk",
        },
    )

    # Merge -> risk assessment (for edit path)
    workflow.add_edge("merge", "risk")

    # Risk -> persist
    workflow.add_edge("risk", "persist")

    # Persist -> responder
    workflow.add_edge("persist", "responder")

    # Terminal nodes
    workflow.add_edge("summarizer", END)
    workflow.add_edge("responder", END)

    app = workflow.compile()

    try:
        final_state = app.invoke(state)
    except Exception as e:
        logger.error(f"LangGraph agent execution failed: {e}", exc_info=True)
        return {
            "reply_text": f"I encountered an error processing your request: {str(e)}. Please try again.",
            "active_complaint_id": active_complaint_id,
            "active_complaint_data": None,
            "risk_assessment": None,
            "updated_fields": [],
        }

    return {
        "reply_text": final_state.get("reply_text", ""),
        "active_complaint_id": final_state.get("active_complaint_id"),
        "active_complaint_data": final_state.get("active_complaint_data"),
        "risk_assessment": final_state.get("risk_assessment"),
        "updated_fields": final_state.get("updated_fields", []),
        "warnings": final_state.get("warnings", []),
        "duplicate_info": final_state.get("duplicate_info"),
    }
