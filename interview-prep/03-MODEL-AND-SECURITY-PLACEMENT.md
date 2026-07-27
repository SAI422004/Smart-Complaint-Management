# 03 - Model Configuration & Security Architecture

## Overview
This document provides an exact inventory of where LLM models, credentials, and security controls are defined and enforced throughout the **AIVOA Copilot** codebase. It covers API key protection, model abstraction layers, prompt-injection defenses, input sanitization, database parameterization, file upload security, and rate limiting.

---

## 1. LLM Model Configuration & Injection Architecture

### Where Model Names Are Configured
Model names are defined in environment variables and injected via Pydantic settings:
- **Primary Configuration File**: `backend/.env`
  ```env
  LLM_MODEL_PRIMARY=openai/gpt-oss-20b
  LLM_MODEL_LARGE_CONTEXT=openai/gpt-oss-120b
  ```
- **Pydantic Settings Management**: [`backend/app/config.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/config.py#L11-L12)
  ```python
  class Settings(BaseSettings):
      ...
      llm_model_primary: str = "llama-3.1-8b-instant"
      llm_model_large_context: str = "llama-3.3-70b-versatile"
  ```

### How Models Are Injected into LangGraph Nodes
Model resolution is decoupled from individual node definitions using helper functions in [`backend/app/agent/llm.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/llm.py#L34-L104):
1. **Dynamic Model Selection**: `select_model(text_length: int)` evaluates character length:
   ```python
   def select_model(text_length: int) -> str:
       if text_length > 4000:
           return settings.llm_model_large_context
       return settings.llm_model_primary
   ```
2. **Node Invocation**: In [`backend/app/agent/nodes.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/nodes.py#L58-L66), `extractor_node` evaluates text size, resolves model string via `select_model()`, and passes it to `call_groq_json()`:
   ```python
   model = select_model(len(source_text))
   result = call_groq_json(
       system_prompt=SYSTEM_PROMPT_EXTRACTOR,
       user_prompt=f"Extract complaint data from:\n\n{source_text}",
       model=model,
       ...
   )
   ```

### Swapping Models — Impact & Dependencies
- **Files to Modify**: To switch model providers or endpoints (e.g., swapping `openai/gpt-oss-20b` for `claude-3-5-sonnet` or an Ollama local model), only `backend/.env` needs to be updated. If changing LLM client SDKs (e.g., from Groq SDK to OpenAI SDK), updates are isolated exclusively to `backend/app/agent/llm.py` inside `get_client()` and `call_groq()`.
- **JSON Output Defenses**: `call_groq_json()` in `llm.py` contains markdown codeblock strip logic (`cleaned.startswith("```json")`) and Pydantic field validation in `schemas.py` to remain model-agnostic, neutralizing model-specific output formatting quirks.

---

## 2. API Key Protection & Secrets Management

### Where the Groq API Key Lives
- **Environment File**: Stored exclusively in `backend/.env` (`GROQ_API_KEY=gsk_...`).
- **Loading Mechanism**: Loaded via `pydantic-settings` (`BaseSettings`) and `python-dotenv` during FastAPI application startup.
- **Client Instantiation**: Singleton initialization in `app/agent/llm.py`:
  ```python
  def get_client() -> Groq:
      global client
      if client is None:
          api_key = settings.groq_api_key
          if not api_key:
              raise ValueError("GROQ_API_KEY not set.")
          client = Groq(api_key=api_key)
      return client
  ```

### Source Control & Frontend Exposure Verification
- **`.gitignore` Compliance**: `backend/.env` is explicitly listed in `/.gitignore` and `/backend/.gitignore`.
- **Frontend Isolation**: The React frontend (`frontend/src/`) communicates solely with FastAPI endpoints (`/api/complaint/chat` and `/api/complaint/upload`). It **has zero direct access or visibility** into `GROQ_API_KEY`.
- **Commit History Security**: Only `backend/.env.example` containing dummy key placeholders is tracked in Git.

---

## 3. Comprehensive Security Controls Matrix

The codebase implements multi-layered security controls across all backend modules:

| Security Measure | Implementation Mechanism & Logic | Location in Codebase |
| :--- | :--- | :--- |
| **Input Sanitization & XSS Prevention** | RegEx HTML tag stripping (`<[^>]*>`) and character escaping (`&`, `<`, `>`, `"`, `'`) executed via Pydantic validators on all text inputs. | [`app/schemas.py:sanitize_text()`](file:///home/saistack/Complaint%20Management%20System/backend/app/schemas.py#L7-L14) & [`app/utils/sanitization.py:sanitize_html()`](file:///home/saistack/Complaint%20Management%20System/backend/app/utils/sanitization.py#L5-L17) |
| **Prompt Injection Protection (Uploaded Docs)** | Uploaded text is encapsulated within explicit system delimiters (`[Uploaded file: ...]`) and passed strictly as user context. System prompt rules mandate non-execution of embedded commands. | [`app/agent/nodes.py:router_node()`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/nodes.py#L30-L33) & [`app/agent/tools.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/agent/tools.py#L23-L48) |
| **SQL Injection Prevention** | All database interactions use SQLAlchemy ORM object mapping (`db.query(Complaint).filter(...)`) with parameterized bound variables. Zero raw SQL string concatenation. | [`app/services/complaint_service.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/services/complaint_service.py#L20-L40) & [`app/services/duplicate_detection.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/services/duplicate_detection.py#L33-L39) |
| **File Upload Validation & Sandboxing** | Multi-step file check: 1) Max size enforcement (10MB limit), 2) MIME type validation (`validate_mime_type`), 3) Cryptographic SHA-256 filename hashing (`timestamp_hash_name`), 4) Storage **outside web root** in `backend/uploads/`. | [`app/routes/upload.py`](file:///home/saistack/Complaint%20Management%20System/backend/app/routes/upload.py#L29-L43) & [`app/utils/file_handler.py:save_upload()`](file:///home/saistack/Complaint%20Management%20System/backend/app/utils/file_handler.py#L14-L28) |
| **Rate Limiting** | Sliding window rate-limiter middleware enforcing a maximum of 20 requests per minute per client IP for chat and upload routes. Returns `HTTP 429 Too Many Requests`. | [`app/main.py:rate_limit_middleware()`](file:///home/saistack/Complaint%20Management%20System/backend/app/main.py#L51-L73) |
| **Audit Trail Traceability** | Append-only audit table (`complaint_changes`) recording field changes, previous value, new value, timestamp, and actor (`AI_Copilot`). | [`app/services/complaint_service.py:_log_change()`](file:///home/saistack/Complaint%20Management%20System/backend/app/services/complaint_service.py#L136-L145) & [`app/models.py:ComplaintChange`](file:///home/saistack/Complaint%20Management%20System/backend/app/models.py#L110-L133) |

---

## 4. Things I Should Double-Check & Defend in the Interview

> [!WARNING]
> **Weak Points & Defensibility**

1. **Hardcoded API Key Placeholder in `.env.example`**:
   - *Current Implementation*: `.env.example` line 2 contains an example key format `gsk_ZlOLjJt...`.
   - *Interview Defense*: Explain that while `.env.example` provides developers with a visual template, ensuring real credentials are set via production environment secrets managers (e.g., AWS Secrets Manager, HashiCorp Vault) is essential.
2. **File MIME Type Verification**:
   - *Current Implementation*: `validate_mime_type()` relies on client-provided `file.content_type` header with extension fallback.
   - *Interview Defense*: Client headers can be spoofed. In enterprise production, we would use binary magic byte inspection libraries (e.g., `python-magic` / `libmagic`) to inspect raw header bytes before parsing documents.
