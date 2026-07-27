# 02 - Technology Stack Rationale

## Overview
This document details the technical justification for every key framework, library, database, and API choice in the **AIVOA Copilot** Customer Complaint Management System. Instead of generic textbook reasons, each rationale addresses the specific requirements of pharmaceutical QMS complaint tracking, real-time AI extraction, and state reconciliation.

---

## 1. React 18 + Redux Toolkit (Frontend State Management)

### Why Redux Specifically Over Context API or Local Component State?
In AIVOA Copilot, client-side state is non-trivial and tightly coupled across two distinct UI panels:
- **`complaint` State**: Holds 15+ structured complaint attributes (`complaintId`, `displayId`, `complainant`, `productName`, `batchNumber`, `manufacturingDate`, `expiryDate`, `affectedQuantityValue`, `affectedQuantityUnit`, `complaintCategory`, `complaintDescription`, `marketRegion`, `status`, `riskAssessment`, `lastUpdatedFields`).
- **`chat` State**: Holds conversation turn objects, uploaded document metadata, pending execution flags (`isProcessing`), and global API error messages.

#### Key Reasons Redux Toolkit Was Chosen:
1. **Isolated Panel Re-renders**: With React Context, any change to the chat history or loading status forces every consumer component to re-render—including the complex read-only `ComplaintForm`. Redux Toolkit uses fine-grained subscription selectors (`useSelector((state) => state.complaint)` vs `useSelector((state) => state.chat.isProcessing)`), ensuring `ComplaintForm` only re-renders when complaint data or highlighted fields change.
2. **Asynchronous Lifecycle Handling (`createAsyncThunk`)**: `sendMessage` and `uploadDocument` in `frontend/src/store/chatSlice.js` require managing `pending`, `fulfilled`, and `rejected` states cleanly. Redux Toolkit centralizes spinner toggles (`isProcessing`), global error banners (`chatSlice.reducers.clearError`), and automated background store updates.
3. **Field-Level Highlight Tracking (`lastUpdatedFields`)**: When an edit message arrives (e.g., updating batch number), the backend returns `updated_fields: ["batch_number"]`. The `complaintSlice.reducers.setUpdatedFields` reducer updates state, allowing `ComplaintForm.jsx` to apply temporary CSS glowing animations (`.highlight`) specifically to affected input fields.

---

## 2. FastAPI (Backend Python Framework)

### Why FastAPI Over Flask or Django?
1. **Pydantic Schema Validation & Native LLM Integration**: FastAPI is built ground-up on Pydantic (`app/schemas.py`). The LLM returns structured JSON strings. Pydantic schemas (`ComplaintCreate`, `ComplaintPatch`, `ChatRequest`, `ChatResponse`) act as a type-safe bridge that validates, coerces, and sanitizes AI-generated JSON before it ever touches database queries or business logic. Django requires serializers; Flask requires manual validation or third-party extensions.
2. **Asynchronous I/O Performance**: The AI Copilot handles network-bound operations (calling Groq API endpoints, extracting multi-page PDF documents). FastAPI’s ASGI architecture (Uvicorn) natively handles high concurrency with minimal CPU overhead compared to synchronous WSGI frameworks like Flask.
3. **Automatic OpenAPI/Swagger Documentation**: `http://localhost:8000/docs` is automatically generated from FastAPI Pydantic route parameters. This allowed rapid verification of `/api/complaint/chat` and `/api/complaint/upload` request/response contracts during development.

---

## 3. LangGraph (Agentic Workflow Framework)

### Why a Graph Agent Over a Single Monolithic Prompt or Sequential Chain?
A single LLM prompt attempting intent classification, entity extraction, category mapping, date normalization, duplicate checking, and risk assessment consistently fails due to prompt drift and structured JSON parsing failures. Standard sequential chains (like basic LangChain LCEL) are rigid linear pipelines that cannot loop back or branch conditionally.

#### Specific Problems in AIVOA Copilot Solved by LangGraph (`app/agent/graph.py`):
1. **Intent-Based Dynamic Routing**:
   - The `router` node classifies intent into `new_complaint`, `edit_complaint`, `document_extraction`, `summarize`, `clarification_needed`, or `off_topic`.
   - Conditional edges immediately branch execution: off-topic messages bypass extraction and DB writes entirely, routing straight to the `responder` node.
2. **The Edit / Patch Branch (`is_edit_path`)**:
   - If `active_complaint_id` exists in `AgentState`, extraction output routes to `merge_node` (which patches specific fields while preserving existing data). If it's a new complaint, it routes to `validator_node`.
3. **Self-Correction & Retry Loops (`should_retry_validation`)**:
   - If `validator_node` detects missing or corrupted fields, it increments `validation_retries`. If `retries < 2`, it dynamically loops back to `extractor_node` with feedback instead of returning broken data to the database.
4. **Conditional Duplicate Detection (`handle_duplicate`)**:
   - If `duplicate_check` node identifies an existing complaint with identical `product_name` and `batch_number`, the graph conditionally routes straight to `responder` to flag the duplicate warning to the user before running risk assessment or persisting duplicate records blindly.

---

## 4. Groq Infrastructure & Dual LLM Strategy

### Why Groq Over OpenAI / Anthropic Direct APIs?
1. **Sub-Second Latency (LPUs - Language Processing Units)**: Pharmaceutical QA workflows require real-time interactive chat responses. Groq’s custom LPU hardware delivers inference speeds exceeding 300 tokens/second for 8B/20B class models, enabling multi-node LangGraph graph traversals (router -> extractor -> validator -> risk) to execute end-to-end in < 1.5 seconds.
2. **Cost-Effective Scalability**: Groq provides open-weight model hosting at a fraction of proprietary API costs.

### Dual-Model Tiering Strategy (`app/agent/llm.py`):
- **Primary Model (`LLM_MODEL_PRIMARY = openai/gpt-oss-20b` / `llama-3.1-8b-instant`)**: Used for lightweight intent routing, structured field extraction, and basic responder messages. Fast and low token footprint.
- **Large Context / Reasoning Model (`LLM_MODEL_LARGE_CONTEXT = openai/gpt-oss-120b` / `llama-3.3-70b-versatile`)**: Dynamically triggered via `select_model(text_length)` when user input or uploaded text exceeds 4,000 characters (e.g., dense multi-page lab reports or multi-email threads).

### Real-World Production Story: Adapting to Model Deprecations
> **Interview Talking Point:** During development, legacy model endpoints like `gemma2-9b-it` and `llama-3.3-70b-versatile` experienced upstream cloud provider deprecation / retirement cycles. 
> 
> **Resolution**: Instead of hardcoding model strings throughout the codebase, we abstracted model selection into `app/config.py` (`LLM_MODEL_PRIMARY` and `LLM_MODEL_LARGE_CONTEXT` environment variables) and `app/agent/llm.py` (`select_model()`). When deprecation occurred, the entire application was migrated to modern open-source endpoints (`openai/gpt-oss-20b` and `openai/gpt-oss-120b`) via configuration updates without altering a single line of business logic or LangGraph node code.

---

## 5. MySQL Database (Relational Store with Audit Logging)

### Why MySQL Relational DB Over NoSQL (MongoDB / Document Store)?
1. **Strict Schema Constraints**: Pharmaceutical complaints require strict column types (`display_id VARCHAR(20) UNIQUE`, `date_received DATETIME`, `affected_quantity_value FLOAT`, foreign keys for risk assessments and change logs).
2. **ACID Compliance & Multi-Table Audit Trails**: Updating a complaint (`complaints` table) must atomically insert risk assessments (`risk_assessments` table) and append field diffs (`complaint_changes` table) within a single database transaction (`db.commit()`). Relational foreign key cascades (`cascade="all, delete-orphan"`) ensure database integrity.
3. **Indexed Query Performance**: The duplicate detection engine executes composite indexed lookups:
   ```sql
   CREATE INDEX idx_complaint_product_batch ON complaints (product_name, batch_number);
   ```
   This guarantees O(1) indexed exact-match lookup speeds across millions of historical complaint records.

---

## 6. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **Jaccard Similarity vs Vector Embeddings**:
   - *Current Implementation*: Jaccard word-set intersection over MySQL string descriptions.
   - *Interview Defense*: Acknowledge that Jaccard similarity misses semantic synonyms (e.g., "discolored" vs "faded"). Defend it as a zero-dependency MVP choice that avoids vector database infrastructure overhead, while stating you would upgrade to pgvector / OpenAI embeddings (`text-embedding-3-small`) in V2.
2. **Groq Model Naming Scheme (`openai/gpt-oss-20b`)**:
   - *Current Implementation*: Configured in `backend/.env`.
   - *Interview Defense*: Explain that Groq hosts open-weight models under standardized API compatibility prefixes. Ensure you mention how fallback mechanisms in `call_groq()` handle API errors gracefully.
