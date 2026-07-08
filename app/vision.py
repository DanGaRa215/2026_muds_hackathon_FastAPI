import base64
import json
import logging

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from app.config import (
    get_openrouter_api_key,
    get_openrouter_base_url,
    get_openrouter_model,
)
from app.constants import DETECTION_PROMPT
from app.parser import normalize_detection, parse_json_response

logger = logging.getLogger(__name__)


class VisionDetectionError(Exception):
    """Raised when vision detection fails after retries."""


def _build_model() -> ChatOpenAI:
    api_key = get_openrouter_api_key()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is required")

    return ChatOpenAI(
        model=get_openrouter_model(),
        api_key=api_key,
        base_url=get_openrouter_base_url(),
        temperature=0.1,
        max_tokens=1024,
    )


def _media_type(image_bytes: bytes, content_type: str | None) -> str:
    if content_type == "image/png":
        return "image/png"
    if content_type == "image/jpeg":
        return "image/jpeg"
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    return "image/jpeg"


def _invoke_once(model: ChatOpenAI, image_bytes: bytes, media_type: str) -> dict:
    b64 = base64.b64encode(image_bytes).decode()
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {"url": f"data:{media_type};base64,{b64}"},
            },
            {"type": "text", "text": DETECTION_PROMPT},
        ]
    )
    response = model.invoke([message])
    raw_text = response.content if isinstance(response.content, str) else str(response.content)
    parsed = parse_json_response(raw_text)
    return normalize_detection(parsed)


def vision_detect(image_bytes: bytes, content_type: str | None = None) -> dict:
    model = _build_model()
    media_type = _media_type(image_bytes, content_type)

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return _invoke_once(model, image_bytes, media_type)
        except (json.JSONDecodeError, ValueError, TypeError) as exc:
            last_error = exc
            logger.warning("Vision JSON parse failed on attempt %s: %s", attempt + 1, exc)
        except Exception as exc:
            logger.exception("Vision API call failed on attempt %s", attempt + 1)
            raise VisionDetectionError("Vision API call failed") from exc

    raise VisionDetectionError("Vision response JSON parse failed") from last_error
