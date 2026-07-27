# 07 - Interview Questions & First-Person Answers

## Overview
This document contains realistic technical interview questions specifically focused on the **AIVOA Copilot** Customer Complaint Management System. Every answer is written in a **first-person, conversational voice** directly referencing code symbols, file paths, and actual architecture from this codebase.

---

## Category 1: Architecture & Design Decisions

### Q1: Why did you use LangGraph instead of just chaining prompts manually or using standard sequential LangChain?
**Answer**:
> *"When building a pharmaceutical QMS application, a single sequential chain falls apart because real user interaction is non-linear. A user might report a brand-new complaint, follow up with a minor field edit, upload a lab PDF, or send an off-topic greeting. 
> 
> Manually chaining prompts using if-else logic quickly becomes spaghetti code. LangGraph gave us an explicit stateful graph using `StateGraph(AgentState)` in `app/agent/graph.py`. We defined discrete nodes—like `router_node`, `extractor_node`, `merge_node`, `validator_node`, `duplicate_check_node`, and `risk_assessment_node`—and connected them via conditional edges. 
> 
> For example, if `router_node` detects off-topic intent, a conditional edge immediately skips heavy extraction nodes and routes directly to `responder_node`. If extraction discovers invalid fields, a retry conditional edge routes back to `extractor_node` up to 2 times. LangGraph gave us explicit state control, clear node isolation, and full observability over state transitions."*

### Q2: Why is the left panel complaint form read-only and driven entirely by AI, rather than allowing users to edit fields manually?
**Answer**:
> *"In pharmaceutical manufacturing, regulatory compliance—specifically GxP and FDA 21 CFR Part 11—demands absolute data integrity, standardization, and auditability. In standard CRUD forms, users frequently enter ambiguous dates (like '10/12/26'), freeform units, or informal issue categories. 
> 
> By making the `ComplaintForm.jsx` component read-only and driving updates strictly through our LangGraph backend:
> 1. All dates are parsed and standardized into ISO `YYYY-MM-DD` format via `parse_date()`.
> 2. Issues are classified into standardized regulatory categories via `map_category()`.
> 3. Every single field mutation is recorded in our append-only `complaint_changes` audit table with an explicit `changed_by='AI_Copilot'` provenance stamp.
> 4. It eliminates client-side form editing race conditions and guarantees that what's rendered on screen matches our MySQL backend single source of truth."*

### Q3: How would this architecture scale if 100 QA managers were using the system simultaneously?
**Answer**:
> *"Currently, Uvicorn runs as a single process with an in-memory rate-limiter dictionary in `app/main.py` and a synchronous SQLAlchemy session (`SessionLocal`). To scale to 100+ concurrent active sessions:
> 1. **Stateless Web Tier**: Replace the in-memory rate-limiter dictionary with Redis (`slowapi` + Redis) so rate-limiting state is shared across multiple Uvicorn worker processes managed by Gunicorn.
> 2. **Async Database Engine**: Convert SQLAlchemy database sessions from synchronous `SessionLocal` to `sqlalchemy.ext.asyncio` with `asyncmy` driver. This prevents thread pool blocking during database I/O.
> 3. **Groq Rate-Limits & Connection Pooling**: External LLM calls to Groq API are network-bound. We would implement a queue worker (Celery or Redis Queue) to manage background document extraction jobs without blocking HTTP request-response cycles."*

---

## Category 2: LLM & AI Specifics

### Q4: Why did you choose Groq, and why did you configure two different model sizes?
**Answer**:
> *"In a QMS copilot, user experience requires sub-second response times. Traditional cloud APIs like GPT-4 can take 3 to 6 seconds per request, which feels sluggish when chaining multiple agent steps. Groq’s custom Language Processing Units (LPUs) deliver inference speeds over 300 tokens/second, allowing our multi-node LangGraph pipeline (router -> extractor -> validator -> risk) to execute in under 1.5 seconds.
> 
> We configured a dual-model tier in `app/config.py` and `app/agent/llm.py`:
> - `LLM_MODEL_PRIMARY` (`openai/gpt-oss-20b`): Used for lightweight intent routing, fast entity extraction, and crafting responder messages.
> - `LLM_MODEL_LARGE_CONTEXT` (`openai/gpt-oss-120b`): Triggered dynamically by `select_model(text_length)` whenever input text exceeds 4,000 characters (such as multi-page uploaded PDF lab reports or long email threads). This gives us high speed for chat while reserving deep reasoning models for dense context."*

### Q5: How do you prevent the LLM from hallucinating complaint details that weren't in the user input?
**Answer**:
> *"We attack hallucination at three distinct layers:
> 1. **System Prompt Rules**: `SYSTEM_PROMPT_EXTRACTOR` in `app/agent/tools.py` starts with strict directives: *'NEVER invent data. If information is not present, set it to null. Do NOT speculate about batch numbers, dates, or quantities.'*
> 2. **Pydantic Validation**: Extracted fields pass through validation in `extractor_node()` and `validator_node()`. If the LLM generates impossible dates (e.g., expiry date earlier than manufacturing date), code in `nodes.py` catches it and attaches a warning flag (`Expiry date is not later than manufacturing date`).
> 3. **Validation Retry Node**: If extracted data fails basic sanity checks, `validator_node()` increments `validation_retries` and routes back to `extractor_node` with error context to repair the payload."*

### Q6: What happens if the LLM returns malformed JSON or markdown-wrapped JSON?
**Answer**:
> *"In `app/agent/llm.py`, our `call_groq_json()` function handles markdown wrapper sanitization:
> ```python
> cleaned = content.strip()
> if cleaned.startswith("```json"):
>     cleaned = cleaned[7:]
> if cleaned.endswith("```"):
>     cleaned = cleaned[:-3]
> return json.loads(cleaned)
> ```
> If `json.loads()` raises a `JSONDecodeError`, `call_groq_json` catches it, logs raw content, and raises a clear `ValueError`. In `extractor_node`, this exception is caught safely in a try-except block, logging validation errors and routing the agent to `responder_node` to ask the user for clarification rather than crashing the API."*

### Q7: How do you defend against prompt injection inside uploaded documents?
**Answer**:
> *"When a document (PDF, DOCX, TXT, EML) is uploaded, raw text is extracted using `file_handler.py`. In `nodes.py`, the text is wrapped cleanly inside delimiter headers (`[Uploaded file: filename.pdf] Content: ...`) and passed to `call_groq_json()`. 
> 
> Crucially, document text is **never injected into system prompts**. System prompts in `tools.py` strictly define the extractor role and mandate that document text must be treated as passive data to extract entities from, not as instructions to execute. Furthermore, input sanitization in `schemas.py` strips dangerous characters before data is processed."*

### Q8: Walk me through your risk assessment logic — is it rule-based, LLM-based, or hybrid?
**Answer**:
> *"It's a hybrid approach. In `app/agent/nodes.py`, `risk_assessment_node()` collects key complaint context—product name, category, issue description, batch number, market region—and passes it to `call_groq_json()` using `SYSTEM_PROMPT_RISK`. 
> 
> The LLM evaluates severity (`Minor`, `Major`, `Critical`), recommends a QA next action (e.g., *'Initiate batch retention sampling'*), and provides a confidence rating (0.0–1.0). 
> 
> However, if the LLM call fails or times out, our try-except block falls back to a deterministic, conservative safety default: severity `Major`, action `'Route to QA investigation.'`, and confidence `0.3`. This ensures the system never leaves a pharmaceutical complaint unclassified."*

---

## Category 3: Data & Backend

### Q9: Why did you choose MySQL over PostgreSQL or MongoDB?
**Answer**:
> *"A pharmaceutical customer complaint system requires structured data tables, strict column data types, composite indexes, and ACID compliance across multi-table updates (`complaints`, `risk_assessments`, `complaint_changes`). 
> 
> NoSQL options like MongoDB lack enforcement for consistent field schemas and relational integrity. While PostgreSQL is also a great option, MySQL was selected because of its light footprint, native support for composite string indexes (`idx_complaint_product_batch`), and widespread adoption in enterprise QMS infrastructures. Using SQLAlchemy ORM (`app/database.py`), the codebase remains database-agnostic should we migrate to PostgreSQL in the future."*

### Q10: What does your database schema look like, and how is the audit log implemented?
**Answer**:
> *"Our database schema in `app/models.py` has three core tables:
> 1. `complaints`: Stores primary fields (`complaint_id`, `display_id` like `CMP-2026-0001`, `complainant`, `product_name`, `batch_number`, `manufacturing_date`, `expiry_date`, `affected_quantity_value`, `affected_quantity_unit`, `complaint_category`, `complaint_description`, `market_region`, `status`).
> 2. `risk_assessments`: Stores linked AI severity classifications (`severity`, `next_action`, `rationale`, `confidence`) with a foreign key (`complaint_fk`) to `complaints`.
> 3. `complaint_changes`: An append-only audit trail table (`id`, `complaint_fk`, `field_name`, `old_value`, `new_value`, `changed_by`, `changed_at`).
> 
> Whenever `ComplaintService.update_complaint()` runs in `complaint_service.py`, it calculates the diff for modified fields and inserts an immutable change record into `complaint_changes`. This fulfills regulatory audit trail requirements."*

### Q11: How do you prevent SQL injection?
**Answer**:
> *"Zero raw SQL queries are written in this codebase. All database reads and writes use SQLAlchemy ORM (`db.query(Complaint).filter(...)`). SQLAlchemy automatically parameterizes all inputs using database bind variables (`?` / `%s`). Additionally, string inputs are sanitized via `sanitize_text()` in `schemas.py` before hitting ORM models."*

---

## Category 4: Bugs & Debugging Stories

### Q12: Tell me about a real bug you encountered during development and how you debugged it.
**Answer**:
> *"A great example was an unhandled server crash: `AttributeError: 'NoneType' object has no attribute 'lower'`.
> 
> **Symptoms**: Sending simple conversational inputs like 'Hello' caused Uvicorn to throw HTTP 500 errors.
> **Investigation**: I checked Uvicorn traceback logs and traced the crash to `extractor_node()` in `app/agent/nodes.py`.
> **Root Cause**: When inputs lacked complaint data, the extractor set `complaint_description` to `None`. Line 109 executed:
> ```python
> description = data.get("complaint_description")
> product_count = description.lower().count("product")
> ```
> Calling `.lower()` on `None` raised `AttributeError`.
> **Resolution**: I fixed it by enforcing defensive string fallback: `description = data.get("complaint_description") or ""`. I added unit checks to verify that optional text fields evaluate cleanly to empty strings."*

### Q13: How did you handle the Groq LLM model deprecation issue?
**Answer**:
> *"During active development, upstream Groq API endpoints retired older model identifiers like `gemma2-9b-it` and `llama-3.3-70b-versatile`. 
> 
> Because we had decoupled model configuration into `LLM_MODEL_PRIMARY` and `LLM_MODEL_LARGE_CONTEXT` in `app/config.py` and `app/agent/llm.py`, we resolved the deprecation across the entire application in under 2 minutes. We updated `backend/.env` to point to supported endpoints (`openai/gpt-oss-20b` and `openai/gpt-oss-120b`). No node logic, graph structure, or API endpoints had to be altered."*

### Q14: How do you handle a Groq API timeout or rate limit mid-conversation?
**Answer**:
> *"In `app/agent/llm.py`, all Groq API calls are wrapped with Tenacity retry decorators:
> ```python
> @retry(
>     stop=stop_after_attempt(3),
>     wait=wait_exponential(multiplier=1, min=2, max=10),
>     retry=retry_if_exception_type(Exception),
> )
> def call_groq(...)
> ```
> If Groq encounters rate limits or transient network hiccups, Tenacity retries up to 3 times with exponential backoff (waiting 2s, 4s, 8s). If all retries fail, try-except blocks in `nodes.py` catch the error gracefully and return helpful user error replies rather than crashing the system."*

---

## Category 5: Security & Product Logic

### Q15: Where is your API key stored, and what would happen if it leaked?
**Answer**:
> *"The key is stored exclusively in `backend/.env` (`GROQ_API_KEY`). It is loaded via Pydantic `BaseSettings` into backend memory. `backend/.env` is strictly excluded in `.gitignore`. The React frontend communicates strictly with FastAPI endpoints and has zero visibility into backend keys. If leaked, the key could be revoked immediately in the Groq console without affecting database records or client build assets."*

### Q16: How does the Edit tool know which fields to update without wiping existing data?
**Answer**:
> *"When a follow-up message arrives, `router_node` sets intent to `edit_complaint`. The extractor extracts only specified fields, leaving missing fields as `None`. In `nodes.py`, `merge_node()` checks `active_complaint_id`, pulls existing complaint data, and iterates through extracted fields. It patches only fields where `value is not None` and value differs from existing data. Fields with `None` are ignored, preserving existing database values."*

### Q17: What would you build next if given another week?
**Answer**:
> *"Three key enhancements:
> 1. **Semantic Vector Search for Duplicate Detection**: Replace Jaccard text similarity with pgvector or OpenAI embeddings (`text-embedding-3-small`) to catch semantic duplicates (e.g., 'discolored tablets' matching 'yellowish discoloration').
> 2. **Async Database Engine**: Migrate SQLAlchemy from synchronous `SessionLocal` to `asyncio` with `asyncmy` driver.
> 3. **Tesseract OCR Integration**: Add OCR parsing for scanned image PDFs in `file_handler.py`."*

---

## 6. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **Jaccard Threshold Choice (`0.5`)**:
   - *Current Implementation*: Hardcoded Jaccard threshold in `duplicate_detection.py`.
   - *Interview Defense*: Explain that `0.5` was tuned empirically on demo data; in production, this threshold would be configurable via `settings.py` or replaced with vector cosine similarity.
