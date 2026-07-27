import json
import logging
from datetime import datetime
from typing import Dict, Any

from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.agent.llm import call_groq_json, call_groq, select_model
from app.agent.tools import (
    SYSTEM_PROMPT_ROUTER,
    SYSTEM_PROMPT_EXTRACTOR,
    SYSTEM_PROMPT_RISK,
    SYSTEM_PROMPT_SUMMARIZER,
    parse_date,
    resolve_quantity,
    map_category,
    NOT_SPECIFIED,
)
from app.services.complaint_service import ComplaintService
from app.services.duplicate_detection import DuplicateDetectionService
from app.schemas import sanitize_text

logger = logging.getLogger(__name__)


def router_node(state: AgentState) -> Dict[str, Any]:
    """Classify the user's intent using the LLM."""
    user_message = state["user_message"]
    if state["uploaded_text"]:
        combined = f"[Uploaded file: {state['uploaded_filename']}]\nContent: {state['uploaded_text'][:3000]}"
    else:
        combined = user_message

    try:
        result = call_groq_json(
            system_prompt=SYSTEM_PROMPT_ROUTER,
            user_prompt=f"Classify this message:\n\n{combined}",
            temperature=0.0,
            max_tokens=100,
        )
        intent = result.get("intent", "clarification_needed")
    except Exception as e:
        logger.warning(f"Router LLM call failed, defaulting to clarification_needed: {e}")
        intent = "clarification_needed"

    # Check if a file was uploaded -> force document_extraction intent
    if state["uploaded_text"]:
        intent = "document_extraction"

    return {"intent": intent}


def extractor_node(state: AgentState) -> Dict[str, Any]:
    """Extract structured complaint data from user input using LLM."""
    source_text = state.get("uploaded_text") or state["user_message"]

    model = select_model(len(source_text))

    try:
        result = call_groq_json(
            system_prompt=SYSTEM_PROMPT_EXTRACTOR,
            user_prompt=f"Extract complaint data from:\n\n{source_text}",
            model=model,
            temperature=0.1,
            max_tokens=2048,
        )
    except Exception as e:
        logger.error(f"Extractor LLM call failed: {e}")
        return {
            "extracted_data": None,
            "validation_errors": [f"AI extraction failed: {str(e)}"],
            "intent": "clarification_needed",
        }

    has_data = result.get("has_complaint_data", True)
    if not has_data:
        return {
            "extracted_data": None,
            "intent": "clarification_needed",
        }

    # Clean and standardize the extracted data
    data = result

    # Parse dates
    data["manufacturing_date"] = parse_date(data.get("manufacturing_date"))
    data["expiry_date"] = parse_date(data.get("expiry_date"))

    # Auto-detect category if not explicitly extracted
    if not data.get("complaint_category") or data["complaint_category"] == "Other":
        cat = map_category(data.get("complaint_description", ""))
        if cat:
            data["complaint_category"] = cat

    # Collect warnings from the extraction
    warnings = data.get("warnings", [])
    if data.get("expiry_date") and data.get("manufacturing_date"):
        try:
            exp = datetime.strptime(data["expiry_date"], "%Y-%m-%d")
            mfg = datetime.strptime(data["manufacturing_date"], "%Y-%m-%d")
            if exp <= mfg:
                warnings.append("Expiry date is not later than manufacturing date — possible data error.")
        except ValueError:
            pass

    # Multiple products detected?
    description = data.get("complaint_description") or ""
    product_count = description.lower().count("product") + description.lower().count("complaint")
    if product_count > 3 and not data.get("product_name"):
        warnings.append("Multiple products or complaints may be described in this message.")

    return {
        "extracted_data": data,
        "warnings": warnings,
        "validation_errors": [],
    }


def validator_node(state: AgentState) -> Dict[str, Any]:
    """Validate extracted data. If invalid, increment retries and flag errors."""
    data = state.get("extracted_data")
    if not data:
        return {"validation_errors": ["No data extracted to validate."]}

    errors = []

    # Check for conflicting data (multiple batch numbers in description = conflict already flagged by LLM)
    if not data.get("batch_number") and "batch" in state["user_message"].lower():
        # User mentioned batch but no number -> it's OK, just not provided
        pass

    # Check if extracted data is too sparse (nothing useful)
    useful_fields = [k for k, v in data.items() if v is not None and k != "warnings" and k != "has_complaint_data"]
    if len(useful_fields) <= 1:
        errors.append("No meaningful complaint data could be extracted. Please provide more details.")

    retries = state["validation_retries"] + 1

    return {
        "validation_errors": errors,
        "validation_retries": retries,
    }


def duplicate_detection_node(state: AgentState, db: Session) -> Dict[str, Any]:
    """Check if the extracted complaint is a duplicate of an existing record."""
    data = state.get("extracted_data")
    if not data:
        return {"duplicate_info": None}

    product = data.get("product_name")
    batch = data.get("batch_number")
    description = data.get("complaint_description", "")

    dup_service = DuplicateDetectionService(db)
    duplicate = dup_service.find_duplicate(
        product_name=product,
        batch_number=batch,
        description=description,
    )

    if duplicate:
        return {
            "duplicate_info": {
                "is_duplicate": True,
                "existing_complaint_id": duplicate.complaint_id,
                "existing_display_id": duplicate.display_id,
                "match_reason": f"Same product '{product}' and batch '{batch}'" if (product and batch) else "Similar complaint description",
            }
        }

    return {"duplicate_info": None}


def merge_node(state: AgentState) -> Dict[str, Any]:
    """Merge extracted fields into the existing complaint record (edit path)."""
    existing = state.get("active_complaint_data")
    new_data = state.get("extracted_data")
    if not existing or not new_data:
        return {"updated_fields": []}

    updated_fields = []
    warnings = list(state.get("warnings", []))

    for field, value in new_data.items():
        if field in ("warnings", "has_complaint_data"):
            continue
        if value is not None and value != "":
            # Resolve field name mappings
            if field == "affected_quantity":
                qv = value.get("value") if isinstance(value, dict) else None
                qu = value.get("unit") if isinstance(value, dict) else None
                if qv is not None:
                    existing["affected_quantity_value"] = qv
                    updated_fields.append("affected_quantity_value")
                if qu is not None:
                    existing["affected_quantity_unit"] = qu
                    updated_fields.append("affected_quantity_unit")
            else:
                if existing.get(field) != value:
                    existing[field] = value
                    updated_fields.append(field)

    return {
        "active_complaint_data": existing,
        "updated_fields": updated_fields,
        "warnings": warnings,
    }


def risk_assessment_node(state: AgentState) -> Dict[str, Any]:
    """Run risk assessment on the complaint data using the LLM."""
    data = state.get("extracted_data") or state.get("active_complaint_data")
    if not data:
        return {"risk_assessment": None}

    context = {
        "product_name": data.get("product_name"),
        "complaint_category": data.get("complaint_category"),
        "complaint_description": data.get("complaint_description"),
        "batch_number": data.get("batch_number"),
        "market_region": data.get("market_region"),
    }

    try:
        result = call_groq_json(
            system_prompt=SYSTEM_PROMPT_RISK,
            user_prompt=f"Assess risk for this complaint:\n\n{json.dumps(context, indent=2)}",
            temperature=0.2,
            max_tokens=1024,
        )
        return {"risk_assessment": result}
    except Exception as e:
        logger.error(f"Risk assessment failed: {e}")
        return {
            "risk_assessment": {
                "severity": "Major",
                "next_action": "Route to QA investigation.",
                "rationale": "Default classification due to AI assessment failure.",
                "confidence": 0.3,
            }
        }


def persistence_node(state: AgentState, db: Session) -> Dict[str, Any]:
    """Save or update the complaint record in the database."""
    data = state.get("extracted_data") or state.get("active_complaint_data")
    risk = state.get("risk_assessment")
    active_id = state.get("active_complaint_id")

    svc = ComplaintService(db)

    if active_id:
        # Update existing complaint
        complaint = svc.update_complaint(
            complaint_id=active_id,
            data=data,
            updated_fields=state.get("updated_fields", []),
        )
    else:
        # Create new complaint
        duplicate_info = state.get("duplicate_info")
        if duplicate_info and duplicate_info.get("is_duplicate"):
            # Still create but flag as potential duplicate; we surface this in the response
            pass

        complaint = svc.create_complaint(data)

    # Save risk assessment
    if risk and complaint:
        svc.save_risk_assessment(
            complaint_id=complaint.complaint_id,
            severity=risk.get("severity", "Major"),
            next_action=risk.get("next_action", "Route to QA investigation."),
            rationale=risk.get("rationale", ""),
            confidence=risk.get("confidence"),
        )

    return {
        "active_complaint_id": complaint.complaint_id if complaint else active_id,
        "active_complaint_data": complaint.to_dict() if complaint else state.get("active_complaint_data"),
    }


def responder_node(state: AgentState) -> Dict[str, Any]:
    """Craft the natural-language reply to the user."""
    intent = state.get("intent")
    data = state.get("extracted_data") or state.get("active_complaint_data")
    risk = state.get("risk_assessment")
    warnings = state.get("warnings", [])
    updated = state.get("updated_fields", [])
    duplicate_info = state.get("duplicate_info")

    if intent == "clarification_needed":
        reply = "I'd be happy to help log a complaint. Could you please provide details about the product, the issue you're reporting, and any relevant batch or complainant information?"
        if state.get("validation_errors"):
            reply = "I wasn't able to extract clear complaint data from your message. Please provide details like product name, batch number, issue description, and complainant."
        return {"reply_text": reply}

    if intent == "off_topic":
        return {"reply_text": "I'm here to help with customer complaints for pharmaceutical products. Could you describe the complaint you'd like to log?"}

    # Build response based on what happened
    parts = []

    if duplicate_info and duplicate_info.get("is_duplicate"):
        parts.append(
            f"⚠️ **Potential Duplicate**: This looks similar to complaint "
            f"**{duplicate_info['existing_display_id']}** (same product and batch). "
            f"I'm logging it separately — you may want to review and link them."
        )

    if updated:
        product = data.get("product_name", "the complaint") if data else "the complaint"
        parts.append(f"Updated {product} with: {', '.join(updated)}.")
    elif data:
        product = data.get("product_name") or "complaint"
        complainant = data.get("complainant") or "Unknown"
        batch = data.get("batch_number") or "N/A"
        parts.append(f"Logged complaint for **{product}** from **{complainant}** (Batch: {batch}).")

    if risk:
        sev = risk.get("severity", "Unclassified")
        action = risk.get("next_action", "")
        parts.append(f"**Classification**: {sev} severity. {action}")

    if warnings:
        for w in warnings[:3]:
            parts.append(f"⚠️ *Note*: {w}")
        if len(warnings) > 3:
            parts.append(f"... and {len(warnings) - 3} more item(s).")

    if not parts:
        parts.append("I've processed your input but didn't find complaint data. Could you provide more details?")

    return {"reply_text": "\n\n".join(parts)}


def summary_node(state: AgentState, db: Session) -> Dict[str, Any]:
    """Generate a complaint summary for the report."""
    active_id = state.get("active_complaint_id")
    if not active_id:
        return {"reply_text": "No active complaint to summarize. Please log a complaint first."}

    svc = ComplaintService(db)
    complaint = svc.get_complaint(active_id)
    if not complaint:
        return {"reply_text": "Complaint not found."}

    risk = svc.get_latest_risk_assessment(active_id)

    context = complaint.to_dict()
    context["risk_assessment"] = risk.to_dict() if risk else None

    try:
        result = call_groq_json(
            system_prompt=SYSTEM_PROMPT_SUMMARIZER,
            user_prompt=f"Summarize this complaint:\n\n{json.dumps(context, indent=2)}",
            max_tokens=1024,
        )
        summary = result.get("summary", "Summary generation failed.")
    except Exception as e:
        summary = f"Summary generation failed: {e}"

    return {"reply_text": summary}
