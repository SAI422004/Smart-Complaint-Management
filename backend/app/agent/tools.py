import re
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple


NOT_SPECIFIED = "Not specified"

# Prompts for the LangGraph agents

SYSTEM_PROMPT_ROUTER = """You are an intent classifier for a pharmaceutical QMS complaint management system.
Classify the user's message into exactly one of these intents:

- new_complaint: User is reporting a new customer complaint about a pharmaceutical product.
- edit_complaint: User is providing additional details or corrections to an existing complaint.
- document_extraction: User has uploaded a document containing complaint information.
- summarize: User wants a summary of the current complaint.
- clarification_needed: The message is a greeting, general question, or lacks any complaint data.
- off_topic: The message is clearly unrelated to complaint management.

Respond ONLY with a JSON object: {"intent": "<intent>"}
No other text."""

SYSTEM_PROMPT_EXTRACTOR = """You are a pharmaceutical QMS data extraction specialist. Extract complaint information from the user's message into a structured JSON format.

Rules (CRITICAL — do not violate):
1. NEVER invent data. If information is not present, set it to null.
2. For text fields where information IS present, clean and standardize it.
3. Do NOT speculate about batch numbers, dates, or quantities.
4. If multiple conflicting values are mentioned for the same field (e.g., two batch numbers), set the field to null and add a warning.

Output schema:
{
  "complainant": "string or null",
  "product_name": "string or null",
  "product_strength": "string or null",
  "batch_number": "string or null",
  "manufacturing_date": "string or null (ISO date format YYYY-MM-DD if extractable)",
  "expiry_date": "string or null (ISO date format YYYY-MM-DD if extractable)",
  "affected_quantity": {"value": float or null, "unit": "string or null"},
  "complaint_category": "string or null (one of: Discoloration, Contamination, Packaging Defect, Short-fill, Labeling Error, Degradation, Other)",
  "complaint_description": "string or null (a brief factual summary of the issue)",
  "market_region": "string or null",
  "warnings": ["list of data-quality warnings if any"],
  "has_complaint_data": true/false
}

Set has_complaint_data to false only if the message truly contains no complaint information at all.
Add warnings for: conflicting values, impossible date ranges, unit mismatches."""

SYSTEM_PROMPT_RISK = """You are a pharmaceutical QMS risk assessment specialist. Based on the complaint data provided, classify the severity and recommend next actions.

Categories:
- Minor: Cosmetic issues, no patient safety impact, localized packaging flaw.
- Major: Quality defect that could impact product efficacy or patient experience, requires investigation.
- Critical: Potential patient safety risk, contamination, potency deviation, labeling error that could cause harm.

Output JSON:
{
  "severity": "Minor | Major | Critical",
  "next_action": "string describing the recommended action",
  "rationale": "string explaining the reasoning, referencing specific complaint facts",
  "confidence": 0.0-1.0 (how confident you are given the available data)
}"""

SYSTEM_PROMPT_SUMMARIZER = """You are a pharmaceutical QMS report writer. Generate a concise, professional plain-English summary of a complaint record suitable for a QA report or handoff email.

Include:
- Complaint ID
- Product and batch details
- Description of the issue
- Risk classification
- Current status
- Recommended next action

Output as a single JSON object: {"summary": "the summary text"}"""


def parse_date(date_str: Optional[str]) -> Optional[str]:
    """Try to parse a date string into ISO format YYYY-MM-DD."""
    if not date_str or date_str == "null":
        return None
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%Y/%m/%d", "%d %B %Y"]:
        try:
            return datetime.strptime(date_str.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return date_str


def resolve_quantity(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract quantity value and unit from a text fragment."""
    if not text:
        return None, None
    pattern = r"(\d+\.?\d*)\s*(capsules?|caps?|kg|g|mg|drums?|bottles?|vials?|tablets?|L|mL|units?)"
    match = re.search(pattern, text.lower())
    if match:
        return float(match.group(1)), match.group(2)
    return None, None


def map_category(text: str) -> Optional[str]:
    """Map a complaint description to a category."""
    if not text:
        return None
    t = text.lower()
    if any(w in t for w in ["discolor", "fading", "color change"]):
        return "Discoloration"
    if any(w in t for w in ["contamin", "foreign", "particle", "dust"]):
        return "Contamination"
    if any(w in t for w in ["packaging", "crack", "broken", "seal", "leak"]):
        return "Packaging Defect"
    if any(w in t for w in ["short", "underfill", "less", "missing", "incomplete"]):
        return "Short-fill"
    if any(w in t for w in ["label", "misprint", "wrong label"]):
        return "Labeling Error"
    if any(w in t for w in ["degrad", "expir", "potency"]):
        return "Degradation"
    return None
