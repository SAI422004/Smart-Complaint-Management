# 06 - Key Code Walkthrough & Interview Snippets

## Overview
This document breaks down the 7 most technical, interview-worthy code snippets in the **AIVOA Copilot** codebase. For each snippet, the actual project code is shown, followed by a **first-person conversational explanation** formatted exactly as you should present it out loud to an interviewer.

---

## Snippet 1: LangGraph Graph Construction & Conditional Edges

### Code Excerpt
**File**: [`backend/app/agent/graph.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/graph.py#L63-L135)

```python
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
```

### Conversational Explanation to Interviewer
> *"Here is how I structured the core LangGraph execution graph. Rather than relying on a single monolith prompt, I built a stateful directed graph using `StateGraph(AgentState)`. 
> 
> Entry begins at the `router` node, which classifies the user's intent. Notice the `add_conditional_edges` call right after router: if the intent is off-topic or needs clarification, execution bypasses complex extraction nodes and routes directly to the `responder` node to save latency and token costs. 
> 
> If intent involves complaint logging or document extraction, it routes to `extractor`. After extraction, another conditional edge `is_edit_path` checks whether an `active_complaint_id` already exists in state. If it does, execution routes to `merge` to patch existing fields; if not, it routes to `validator` for new complaint creation rules."*

---

## Snippet 2: Pydantic Schema Validation & Pre-Sanitization

### Code Excerpt
**File**: [`backend/app/schemas.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/schemas.py#L7-L39)

```python
def sanitize_text(text: str) -> str:
    """Strip HTML tags and dangerous characters for safe rendering."""
    if not text:
        return text
    text = re.sub(r"<[^>]*>", "", text)
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace('"', "&quot;").replace("'", "&#x27;")
    return text

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
```

### Conversational Explanation to Interviewer
> *"To ensure LLM outputs and user inputs never introduce cross-site scripting (XSS) or database corruption, I used Pydantic schemas equipped with a wildcard pre-validator. 
> 
> Before any field in `ComplaintCreate` or `ComplaintPatch` is assigned, the `@validator("*", pre=True)` decorator intercepts all incoming string fields and passes them through `sanitize_text()`. This function strips HTML tags using regex and HTML-escapes special characters like ampersands and quotes. Because this happens at the schema validation boundary, any un-sanitized string from either the UI or the LLM JSON payload is sanitized automatically before entering business logic or database queries."*

---

## Snippet 3: The Edit Path Merge Engine

### Code Excerpt
**File**: [`backend/app/agent/nodes.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/nodes.py#L176-L209)

```python
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
```

### Conversational Explanation to Interviewer
> *"Handling follow-up edits in a conversational AI system is tricky because the user might only specify one updated field—like 'The batch number is actually BMX240699'—without re-stating the rest of the complaint. 
> 
> My `merge_node` function solves this by comparing incoming extracted fields against `active_complaint_data`. It iterates through extracted key-value pairs, ignoring nulls and metadata fields. When it detects a non-null new value that differs from existing state, it patches that field in place and appends the key to `updated_fields`. This list of modified fields is returned to the frontend Redux store so the UI can highlight modified fields in yellow on the read-only form."*

---

## Snippet 4: Hybrid Duplicate Detection Engine

### Code Excerpt
**File**: [`backend/app/services/duplicate_detection.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/services/duplicate_detection.py#L30-L76)

```python
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
    all_complaints = self.db.query(Complaint).filter(Complaint.complaint_description.isnot(None)).all()
    words_new = set(description.lower().split())
    if len(words_new) < 5:
        return None

    best_match = None
    best_score = 0.0
    for c in all_complaints:
        words_existing = set(c.complaint_description.lower().split())
        intersection = words_new & words_existing
        union = words_new | words_existing
        jaccard = len(intersection) / len(union) if union else 0.0
        if jaccard > best_score:
            best_score = jaccard
            best_match = c

    if best_score > 0.5 and best_match:
        logger.info(f"Duplicate found: text similarity {best_score:.2f} -> {best_match.display_id}")
        return best_match
```

### Conversational Explanation to Interviewer
> *"To prevent duplicate complaints from cluttering QA workflows, I implemented a two-tier duplicate detection service. 
> 
> Priority 1 performs a fast indexed SQL query checking for an exact match on `product_name` and `batch_number`. If a match is found, it immediately flags the existing display ID. 
> 
> If product/batch info is incomplete, Priority 2 falls back to a text similarity algorithm over complaint descriptions. It calculates Jaccard word set similarity (intersection over union). If word overlap score exceeds `0.5`, the system flags the existing complaint as a duplicate. This provides reliable duplicate catching without external vector database dependencies."*

---

## Snippet 5: Redux Complaint Slice Nullish Coalescing Reducer

### Code Excerpt
**File**: [`frontend/src/store/complaintSlice.js`](file:///home/saistack/Complaint%20Management%20System/frontend/src/store/complaintSlice.js#L29-L47)

```python
reducers: {
  setComplaint(state, action) {
    const data = action.payload;
    if (!data) return;
    state.complaintId = data.complaint_id ?? state.complaintId;
    state.displayId = data.display_id ?? state.displayId;
    state.dateReceived = data.date_received ?? state.dateReceived;
    state.complainant = data.complainant ?? state.complainant;
    state.productName = data.product_name ?? state.productName;
    state.productStrength = data.product_strength ?? state.productStrength;
    state.batchNumber = data.batch_number ?? state.batchNumber;
    state.manufacturingDate = data.manufacturing_date ?? state.manufacturingDate;
    state.expiryDate = data.expiry_date ?? state.expiryDate;
    state.affectedQuantityValue = data.affected_quantity_value ?? state.affectedQuantityValue;
    state.affectedQuantityUnit = data.affected_quantity_unit ?? state.affectedQuantityUnit;
    state.complaintCategory = data.complaint_category ?? state.complaintCategory;
    state.complaintDescription = data.complaint_description ?? state.complaintDescription;
    state.marketRegion = data.market_region ?? state.marketRegion;
    state.status = data.status ?? state.status;
  },
}
```

### Conversational Explanation to Interviewer
> *"On the client side, updating Redux complaint state requires careful handling so partial payload responses don't wipe out existing form fields. 
> 
> In `setComplaint`, I used ECMAScript nullish coalescing operators (`??`). Unlike logical OR (`||`), nullish coalescing only falls back if the incoming value is strictly `null` or `undefined`. This ensures that existing form values in Redux are preserved when partial backend updates are dispatched."*

---

## Snippet 6: Real Production Bug Fix (`AttributeError: 'NoneType' object has no attribute 'lower'`)

### Code Excerpt
**File**: [`backend/app/agent/nodes.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/nodes.py#L108-L111)

```python
# Multiple products detected?
description = data.get("complaint_description") or ""
product_count = description.lower().count("product") + description.lower().count("complaint")
if product_count > 3 and not data.get("product_name"):
    warnings.append("Multiple products or complaints may be described in this message.")
```

### Conversational Explanation to Interviewer
> *"During initial testing of the extraction pipeline, we hit an unhandled server error: `AttributeError: 'NoneType' object has no attribute 'lower'`. 
> 
> **Root Cause**: When a user sent a short input like 'Hello', the extractor LLM set `complaint_description` to `None`. Line 109 directly invoked `.lower()` on `data.get("complaint_description")`, which evaluates to `None` and crashed Uvicorn. 
> 
> **Fix**: I patched it by adding `or ""` defensive fallback (`description = data.get("complaint_description") or ""`). This guarantees `description` is always a valid string object before string methods are invoked, completely eliminating runtime `NoneType` crashes."*

---

## Snippet 7: Document Upload Endpoint Handler

### Code Excerpt
**File**: [`backend/app/routes/upload.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/routes/upload.py#L20-L55)

```python
@router.post("/upload", response_model=UploadResponse)
async def upload_endpoint(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.max_upload_size_mb} MB.",
        )

    if not validate_mime_type(file.filename or "unknown", file.content_type):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT, EML.",
        )

    filepath = save_upload(contents, file.filename or "upload")
    extracted_text = extract_text(filepath, file.filename or "upload")

    result = run_agent(
        user_message=f"Document uploaded: {file.filename}",
        db=db,
        uploaded_text=extracted_text,
        uploaded_filename=file.filename,
    )
    ...
```

### Conversational Explanation to Interviewer
> *"The document upload endpoint processes uploaded files through validation and extraction pipelines before feeding extracted text directly into our agent. 
> 
> It enforces file size constraints (max 10MB) and checks MIME types against allowed extensions (`PDF`, `DOCX`, `TXT`, `EML`). Once validated, `save_upload()` writes the file to disk using SHA-256 hashed filenames outside the web root to prevent arbitrary execution attacks. `extract_text()` parses document text, which is then passed as context into `run_agent()`."*

---

## 8. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **Jaccard Similarity Performance at Scale**:
   - *Current Implementation*: Memory iteration over all database complaints in `DuplicateDetectionService`.
   - *Interview Defense*: For thousands of records, loading all complaints into Python memory causes performance bottlenecks. Mention that moving similarity search into database SQL triggers or pgvector indexes is the production remedy.
