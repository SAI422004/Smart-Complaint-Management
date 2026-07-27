# 05 - Directory & Project Structure

## Overview
This document maps out the complete repository layout of the **AIVOA Copilot** Customer Complaint Management System. It details every file, directory, and layer responsibility across backend and frontend modules.

---

## 1. Complete Project Directory Tree

```
Complaint Management System/
├── .env.example                # Example environment variables template for project root
├── .gitignore                  # Git ignore rules for root (ignores node_modules, venv, .env)
├── demo.sh                     # Automated bash script for setting up & launching backend/frontend
├── interview-prep/             # Topic-by-topic technical interview preparation documentation
│   ├── 01-ARCHITECTURE.md
│   ├── 02-TECH-STACK-RATIONALE.md
│   ├── 03-MODEL-AND-SECURITY-PLACEMENT.md
│   ├── 04-REQUEST-FLOW-TRACE.md
│   ├── 05-FOLDER-AND-PROJECT-STRUCTURE.md
│   ├── 06-KEY-CODE-WALKTHROUGH.md
│   └── 07-INTERVIEW-QUESTIONS-AND-ANSWERS.md
│
├── backend/                    # FastAPI + LangGraph Python Backend
│   ├── .env                    # Secrets & config file (GROQ_API_KEY, DATABASE_URL)
│   ├── .env.example            # Backend environment template
│   ├── requirements.txt        # Python package dependencies (fastapi, langgraph, groq, etc.)
│   ├── seed_data.py            # Database seeding script generating sample pharma complaints
│   ├── uploads/                # File upload directory stored outside web root
│   ├── app/                    # Primary application package
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings management (loads .env)
│   │   ├── database.py         # SQLAlchemy engine, SessionLocal, and Base metadata
│   │   ├── main.py             # FastAPI main entrypoint, CORS, rate-limiter middleware
│   │   ├── models.py           # SQLAlchemy database models (Complaint, RiskAssessment, ComplaintChange)
│   │   ├── schemas.py          # Pydantic schemas for request/response validation & XSS sanitization
│   │   ├── agent/              # LangGraph AI agent module
│   │   │   ├── __init__.py
│   │   │   ├── graph.py        # LangGraph StateGraph workflow definition & entrypoint
│   │   │   ├── llm.py          # Groq API client initialization, call_groq_json, retry logic
│   │   │   ├── nodes.py        # All 9 agent graph nodes (router, extractor, validator, merge, etc.)
│   │   │   ├── state.py        # TypedDict AgentState definition & initial_state factory
│   │   │   └── tools.py        # System prompts & helper utility tools (date parsing, category mapping)
│   │   ├── routes/             # FastAPI APIRouter endpoints
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         # POST /api/complaint/chat endpoint handler
│   │   │   ├── complaints.py   # GET /api/complaints list, get, risk, & summary endpoints
│   │   │   └── upload.py       # POST /api/complaint/upload document processing endpoint
│   │   ├── services/           # Core business logic service layer
│   │   │   ├── __init__.py
│   │   │   ├── complaint_service.py    # Complaint CRUD operations & append-only audit logging
│   │   │   └── duplicate_detection.py  # Exact & Jaccard text similarity duplicate detection
│   │   └── utils/              # Helper utilities
│   │       ├── __init__.py
│   │       ├── file_handler.py # File storage and multi-format text extraction (PDF, DOCX, TXT, EML)
│   │       └── sanitization.py  # HTML tag stripping and MIME type validation
│   └── tests/                  # Backend test scripts & PDF generators
│
└── frontend/                   # React 18 + Redux Toolkit Client
    ├── package.json            # Node.js dependencies and build scripts
    ├── vite.config.js          # Vite build tool config with API proxy settings
    ├── public/                 # Static asset public directory
    └── src/                    # React source code
        ├── App.css             # Main stylesheet (layout, glowing animations, dark/light theme tokens)
        ├── App.jsx             # Root React layout component (header, banner, left/right split panel)
        ├── index.jsx           # React DOM render entrypoint wrapped in Redux Provider
        ├── api/                # API client configuration
        │   └── client.js       # Fetch client wrapper
        ├── components/         # React UI Components
        │   ├── ComplaintForm.jsx   # Left Panel: Read-only complaint form with glowing field highlights
        │   ├── CopilotChat.jsx     # Right Panel: Interactive chat interface, inputs, file upload button
        │   ├── LeftPanel.jsx       # Left Panel container (ComplaintForm + RiskAssessment)
        │   ├── MessageBubble.jsx   # Individual chat message renderer (user vs assistant bubbles)
        │   ├── RightPanel.jsx      # Right Panel container (Header + CopilotChat)
        │   └── RiskAssessment.jsx  # Left Panel: Severity badge, confidence rating, next action card
        └── store/              # Redux State Store
            ├── index.js        # Redux store configuration combining complaint & chat reducers
            ├── chatSlice.js    # Chat history, async thunks (sendMessage, uploadDocument), error state
            └── complaintSlice.js # Active complaint form data, risk assessment, updated field list
```

---

## 2. Key Code Location Quick Reference

When asked in an interview where specific logic resides, reference these authoritative paths:

| Logical Component | File Path | Key Symbol / Function |
| :--- | :--- | :--- |
| **LangGraph Graph Construction** | [`backend/app/agent/graph.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/graph.py) | `workflow = StateGraph(AgentState)`, `run_agent()` |
| **Agent Nodes & Business Prompts** | [`backend/app/agent/nodes.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/nodes.py) & [`tools.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/tools.py) | `router_node`, `extractor_node`, `merge_node`, `SYSTEM_PROMPT_*` |
| **Pydantic Schemas & Sanitization** | [`backend/app/schemas.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/schemas.py) | `ComplaintCreate`, `ChatRequest`, `sanitize_text` |
| **SQL Database Models** | [`backend/app/models.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/models.py) | `Complaint`, `RiskAssessment`, `ComplaintChange` |
| **Duplicate Detection Engine** | [`backend/app/services/duplicate_detection.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/services/duplicate_detection.py) | `DuplicateDetectionService.find_duplicate()` |
| **Redux Store & Async Actions** | [`frontend/src/store/chatSlice.js`](file:///home/saistack/Complaint%20Management%20System/frontend/src/store/chatSlice.js) & [`complaintSlice.js`](file:///home/saistack/Complaint%20Management%20System/frontend/src/store/complaintSlice.js) | `sendMessage`, `uploadDocument`, `setComplaint` |
| **Read-Only Complaint Form** | [`frontend/src/components/ComplaintForm.jsx`](file:///home/saistack/Complaint%20Management%20System/frontend/src/components/ComplaintForm.jsx) | `ComplaintForm`, `Field`, `isHighlight` |

---

## 3. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **Lack of Database Migration Tool (Alembic)**:
   - *Current Implementation*: Database tables are auto-created on startup via `Base.metadata.create_all(bind=engine)` in `app/main.py`.
   - *Interview Defense*: Acknowledge that `create_all()` does not handle schema migrations for existing databases. In a production enterprise system, Alembic (`alembic init`) should manage version-controlled database schema migrations.
2. **Monolithic Component Placement**:
   - *Current Implementation*: All React components reside flatly inside `frontend/src/components/`.
   - *Interview Defense*: For a larger team deployment, grouping components by feature domain (e.g., `src/features/chat/`, `src/features/complaint-form/`) provides better modularity.
