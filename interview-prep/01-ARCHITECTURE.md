# 01 - Architecture & System Design

## 1. System Architecture Overview

The **AIVOA Copilot** Customer Complaint Management System is an AI-native pharmaceutical Quality Management System (QMS) application built using a modern decoupled stack: React/Redux on the frontend, FastAPI and LangGraph on the backend, Groq LLM infrastructure for inference, and MySQL for relational data persistence with complete audit traceability.

### High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Frontend["React 18 + Redux Toolkit Client (Port 3000)"]
        UI["User Interface (App.jsx)"]
        LP["Left Panel (Read-Only AI Form + Risk Assessment)"]
        RP["Right Panel (Copilot Chat + Doc Upload)"]
        Redux["Redux Store (complaintSlice & chatSlice)"]
        
        UI --> LP
        UI --> RP
        RP -->|User Chat / File Upload| Redux
        Redux -->|API Calls via Fetch| API Gateway
    end

    subgraph Backend["FastAPI REST API Server (Port 8000)"]
        API Gateway["FastAPI Main (app/main.py)"]
        Middleware["Rate Limiter Middleware (20 req/min)"]
        ChatRoute["Chat Endpoint (/api/complaint/chat)"]
        UploadRoute["Upload Endpoint (/api/complaint/upload)"]
        
        API Gateway --> Middleware
        Middleware --> ChatRoute
        Middleware --> UploadRoute
    end

    subgraph AgentFramework["LangGraph Agent Workflow (app/agent/graph.py)"]
        RouterNode["1. Router Node (Intent Classifier)"]
        ExtractorNode["2. Extractor Node (JSON Extraction)"]
        ValidatorNode["3. Validator Node (Field & Rule Check)"]
        MergeNode["4. Merge Node (Patch Engine)"]
        DupNode["5. Duplicate Detection Node (Exact/Jaccard)"]
        RiskNode["6. Risk Assessment Node (Pharma Severity)"]
        PersistNode["7. Persistence Node (DB Writer + Audit Log)"]
        ResponderNode["8. Responder Node (NLE Reply Builder)"]
        
        ChatRoute -->|Invoke run_agent()| RouterNode
        UploadRoute -->|Extract text -> run_agent()| RouterNode

        RouterNode -->|Intent: new / edit / doc| ExtractorNode
        ExtractorNode -->|New Complaint| ValidatorNode
        ExtractorNode -->|Edit Path| MergeNode
        ValidatorNode -->|Valid| DupNode
        ValidatorNode -->|Retry < 2| ExtractorNode
        DupNode -->|No Duplicate| RiskNode
        DupNode -->|Duplicate Found| ResponderNode
        MergeNode --> RiskNode
        RiskNode --> PersistNode
        PersistNode --> ResponderNode
    end

    subgraph ExternalServices["External APIs & Persistence"]
        GroqAPI["Groq Cloud LLM API (openai/gpt-oss-20b / 120b)"]
        MySQLDB[("MySQL Database (complaint_db)")]
        FileStore["Local Upload Directory (uploads/)"]

        RouterNode <-->|Groq API Call| GroqAPI
        ExtractorNode <-->|Groq API Call| GroqAPI
        RiskNode <-->|Groq API Call| GroqAPI
        
        DupNode <-->|Query Product + Batch / Descriptions| MySQLDB
        PersistNode <-->|Insert/Update Complaint + Change Log| MySQLDB
        UploadRoute -->|Save File outside Web Root| FileStore
    end

    ResponderNode -->|Return JSON ChatResponse| ChatRoute
    ChatRoute -->|200 OK + Updated State| Redux
    Redux -->|State Change Trigger| LP
```

---

## 2. The Two-Panel Design Constraint & Architectural Impact

### The Core Design Choice
The application split screen consists of:
1. **Left Panel (`LeftPanel.jsx` / `ComplaintForm.jsx` / `RiskAssessment.jsx`)**: A structured, read-only pharmaceutical QMS complaint form and risk assessment card. Users **cannot directly edit text inputs** in this form.
2. **Right Panel (`RightPanel.jsx` / `CopilotChat.jsx`)**: An interactive AI Copilot conversational interface accepting natural language inputs and document uploads (PDF, DOCX, TXT, EML).

### Why Read-Only AI-Driven Form vs. Standard CRUD?
In traditional CRUD applications, users fill out forms directly. In pharmaceutical QMS environments, non-technical users or field representatives often submit unstructured text (e.g., customer emails, phone transcripts, call logs) containing ambiguous or incomplete information. 

By making the form **read-only and driven entirely by AI extraction and state reconciliation**:
- **Data Integrity & Standardization**: The system prevents manual data entry errors, invalid formats, or skipped fields. The LLM extracts data, normalizes dates to ISO format (`YYYY-MM-DD`), maps informal issue descriptions to standardized pharma categories (`Discoloration`, `Contamination`, `Packaging Defect`, `Short-fill`, `Labeling Error`, `Degradation`), and validates quantities.
- **Auditability**: Every field modification originates from explicit AI state transitions logged in the `complaint_changes` audit table with the `changed_by="AI_Copilot"` provenance tag.
- **Single Source of Truth**: The UI guarantees that what is displayed on screen matches the exact state stored in the backend relational database, eliminating race conditions or client-side form editing inconsistencies.

---

## 3. End-to-End State Flow

```
[User Input] 
    │
    ▼
1. React Component (CopilotChat.jsx)
   Dispatches Redux Async Thunk: sendMessage({ message, complaintId })
    │
    ▼
2. HTTP POST Request (/api/complaint/chat)
   Payload: { "message": "...", "complaint_id": 101 }
    │
    ▼
3. FastAPI Router (app/routes/chat.py)
   Passes execution to `run_agent()` with DB session and active complaint ID.
    │
    ▼
4. LangGraph StateGraph Execution (app/agent/graph.py)
   - Initial State created with `initial_state(user_message)`
   - Router Node classifies intent via Groq LLM (`openai/gpt-oss-20b`).
   - Extractor Node parses structured JSON payload.
   - Routing: If `active_complaint_id` exists -> Merge Node; else -> Validator Node.
   - Duplicate Detection Node queries MySQL (`product_name` + `batch_number`).
   - Risk Assessment Node scores severity (`Minor`, `Major`, `Critical`) and next actions.
   - Persistence Node commits changes to MySQL `complaints`, `risk_assessments`, and `complaint_changes` tables.
   - Responder Node constructs a natural language response summary.
    │
    ▼
5. FastAPI HTTP Response
   Returns ChatResponse JSON: { reply, complaint, risk_assessment, updated_fields }
    │
    ▼
6. Redux Slice Processing (chatSlice.js & complaintSlice.js)
   - `sendMessage.fulfilled` appends messages to `chat.messages`.
   - Dispatches `setComplaint(payload.complaint)`, updating Redux `complaint` state.
   - Dispatches `setRiskAssessment(payload.risk_assessment)`.
   - Dispatches `setUpdatedFields(payload.updated_fields)`.
    │
    ▼
7. UI Re-Render (React)
   - LeftPanel re-renders `ComplaintForm` with updated values.
   - Updated fields glow temporarily via CSS class `.highlight`.
   - Risk assessment card updates severity badge and recommended QA action.
```

---

## 4. Key Architectural Tradeoffs & Design Choices

| Architectural Decision | Chosen Approach | Alternative Considered | Deliberate Tradeoff & Rationale |
| :--- | :--- | :--- | :--- |
| **Agent Framework** | **LangGraph Directed Acyclic / Cyclic Graph** | Single monolith prompt or sequential LangChain LCEL chain | A single prompt is fragile and hard to debug. Sequential chains cannot handle dynamic retries or conditional branching (e.g. edit path vs new complaint path). LangGraph provides explicit state schema, node isolation, and conditional edge control. |
| **Risk Assessment Node** | **Separate Dedicated Graph Node** | Combined Extraction + Risk Prompt | Bundling extraction and risk assessment into one prompt leads to cognitive overload for smaller LLMs and degrades structured JSON output compliance. Separating risk assessment into its own node allows using specific system prompts and distinct temperature settings (`0.2` vs `0.1`). |
| **State Management** | **Redux Toolkit (`complaintSlice` + `chatSlice`)** | React Context API | Context API triggers full sub-tree re-renders whenever any state property updates. Redux Toolkit provides granular selectors, cleanly isolates chat history from form data, handles async thunk states (`pending`/`fulfilled`/`rejected`), and supports field-level diff tracking. |
| **Duplicate Detection** | **Hybrid Rule-Based + Jaccard Word Similarity** | Vector Database (Pinecone / Pgvector) | For a lightweight QMS deployment, introducing vector database infrastructure (embedding models, index management) adds operational overhead. Exact match on `(product_name, batch_number)` + Jaccard similarity (`> 0.5` threshold) on description provides fast, deterministic duplicate identification directly over MySQL. |
| **Audit Log Design** | **Append-Only `complaint_changes` Table** | Overwriting database rows or storing JSON diffs | GxP / 21 CFR Part 11 pharmaceutical compliance demands full traceability. Storing old value, new value, field name, timestamp, and actor in an append-only table satisfies audit requirements without complex database triggers. |

---

## 5. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **In-Memory Rate Limiter**:
   - *Current Implementation*: Simple dictionary in `app/main.py` keyed by IP address.
   - *Interview Defense*: Highlight that in a production multi-worker deployment (e.g., Uvicorn with Gunicorn), in-memory dictionary state will not be shared across processes. A production upgrade would swap this for Redis rate limiting (`redis-py` + `slowapi`).
2. **Synchronous DB Calls in Async FastAPI Endpoints**:
   - *Current Implementation*: SQLAlchemy synchronous session (`SessionLocal`) wrapped inside FastAPI endpoint functions.
   - *Interview Defense*: Explain that FastAPI runs synchronous route handlers in a thread pool (`asyncio.to_thread`). For high-concurrency throughput, transitioning to `sqlalchemy.ext.asyncio` with `asyncmy` driver would prevent thread pool exhaustion.
3. **Optimistic Locking / Concurrency**:
   - *Current Implementation*: Active complaint edits assume single-user session flow.
   - *Interview Defense*: Be ready to explain how to add a `version_id` column to the `Complaint` SQL model to support optimistic concurrency control if multiple QA officers edit the same record concurrently.
