import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine, Base
from app.routes import chat, upload, complaints

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up… creating database tables if they don't exist.")
    Base.metadata.create_all(bind=engine)
    if not settings.groq_api_key:
        logger.warning("GROQ_API_KEY not set! AI features will fail. Set it in .env or environment.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="AIVOA Copilot - Customer Complaint Management System",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow the React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router)
app.include_router(upload.router)
app.include_router(complaints.router)


# Rate limiting middleware (simple in-memory)
request_counts: dict = {}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/complaint/chat") or request.url.path.startswith("/api/complaint/upload"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        minute_window = int(now / 60)

        key = f"{client_ip}:{minute_window}"
        request_counts[key] = request_counts.get(key, 0) + 1

        if request_counts[key] > settings.rate_limit_per_minute:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before sending another request."},
            )

        # Clean old entries periodically
        if len(request_counts) > 10000:
            cutoff = int((now - 120) / 60)
            request_counts.clear()

    response = await call_next(request)
    return response


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "aivoa-copilot"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
