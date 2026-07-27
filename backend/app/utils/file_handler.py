import os
import hashlib
import logging
from typing import Optional
from datetime import datetime

from app.config import settings

logger = logging.getLogger(__name__)

EXTRACTABLE_EXTENSIONS = {".pdf", ".txt", ".docx", ".eml"}


def save_upload(file_bytes: bytes, original_filename: str) -> str:
    """Save an uploaded file to the uploads directory (outside web root)."""
    upload_dir = settings.upload_dir
    os.makedirs(upload_dir, exist_ok=True)

    file_hash = hashlib.sha256(file_bytes).hexdigest()[:12]
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    safe_name = f"{timestamp}_{file_hash}_{original_filename}"
    filepath = os.path.join(upload_dir, safe_name)

    with open(filepath, "wb") as f:
        f.write(file_bytes)

    logger.info(f"Saved upload to {filepath}")
    return filepath


def extract_text_from_pdf(filepath: str) -> str:
    """Extract text from a PDF file using PyMuPDF (fitz) if available."""
    try:
        import fitz
        doc = fitz.open(filepath)
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()
        if not text.strip():
            # Image-only PDF detected
            return "[Image-only PDF — no extractable text. OCR not available.]"
        return text
    except ImportError:
        # Fallback: try pdfminer
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            text = pdfminer_extract(filepath)
            return text if text.strip() else "[No text could be extracted from this PDF.]"
        except ImportError:
            return "[PDF parsing libraries not available. Cannot extract text.]"
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        return f"[Could not extract text from PDF: {str(e)}]"


def extract_text_from_txt(filepath: str) -> str:
    """Extract text from a plain text file."""
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception as e:
        logger.error(f"TXT extraction failed: {e}")
        return f"[Could not read text file: {str(e)}]"


def extract_text(filepath: str, original_filename: str) -> str:
    """Extract text from an uploaded file based on its extension."""
    ext = os.path.splitext(original_filename)[1].lower()
    if ext == ".pdf":
        return extract_text_from_pdf(filepath)
    elif ext == ".txt":
        return extract_text_from_txt(filepath)
    elif ext == ".docx":
        try:
            import docx
            doc = docx.Document(filepath)
            return "\n".join(p.text for p in doc.paragraphs)
        except ImportError:
            return "[DOCX parsing library not available. Install python-docx.]"
        except Exception as e:
            return f"[Could not extract text from DOCX: {str(e)}]"
    elif ext == ".eml":
        try:
            from email import message_from_bytes
            with open(filepath, "rb") as f:
                msg = message_from_bytes(f.read())
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode("utf-8", errors="replace")
            else:
                body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
            return body
        except Exception as e:
            return f"[Could not extract text from EML: {str(e)}]"
    else:
        return f"[Unsupported file type: {ext}]"
