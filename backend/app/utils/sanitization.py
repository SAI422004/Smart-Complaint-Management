import re
from typing import Optional


def sanitize_html(text: Optional[str]) -> Optional[str]:
    """Strip HTML tags and escape dangerous characters to prevent XSS."""
    if not text:
        return text
    # Remove HTML tags
    text = re.sub(r"<[^>]*>", "", text)
    # Escape special characters
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace('"', "&quot;")
    text = text.replace("'", "&#x27;")
    return text


def validate_mime_type(filename: str, content_type: Optional[str]) -> bool:
    """Validate that the uploaded file has an allowed MIME type."""
    allowed = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "message/rfc822",
        "application/octet-stream",
    }
    if content_type in allowed:
        return True
    # Fallback: allow by extension
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    return ext in {"pdf", "docx", "txt", "eml"}
