import json
import time
import logging
from typing import Optional, Dict, Any

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings

logger = logging.getLogger(__name__)

client: Optional[Groq] = None


def get_client() -> Groq:
    global client
    if client is None:
        api_key = settings.groq_api_key
        if not api_key:
            raise ValueError("GROQ_API_KEY not set. Provide it via environment variable or .env file.")
        client = Groq(api_key=api_key)
    return client


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
)
def call_groq(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
    response_format: Optional[Dict[str, str]] = None,
) -> str:
    """Call the Groq LLM with retry logic and backoff."""
    groq_client = get_client()
    selected_model = model or settings.llm_model_primary

    kwargs = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        kwargs["response_format"] = response_format

    try:
        response = groq_client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Groq returned null content")
        return content.strip()
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        raise


def call_groq_json(
    system_prompt: str,
    user_prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.1,
    max_tokens: int = 2048,
) -> Dict[str, Any]:
    """Call Groq and parse the response as JSON."""
    content = call_groq(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    # Try to extract JSON from the response (handles markdown-wrapped JSON)
    # Ensure we have valid JSON
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        cleaned = "\n".join(lines[1:-1]) if len(lines) > 1 else cleaned
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Groq response as JSON: {content[:200]}")
        raise ValueError(f"Invalid JSON from LLM: {e}. Raw: {content[:300]}")


def select_model(text_length: int) -> str:
    """Select appropriate model based on input length."""
    if text_length > 4000:
        return settings.llm_model_large_context
    return settings.llm_model_primary
