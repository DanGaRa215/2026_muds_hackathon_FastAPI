import asyncio
import json
import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.auth import verify_app_key
from app.config import configure_langsmith, get_app_shared_secret
from app.constants import (
    DEFAULT_SHINDO,
    DEFAULT_SOIL,
    MAX_DETECTION_JSON_BYTES,
    MAX_IMAGE_BYTES,
    VALID_STRUCTURE,
)
from app.detection import detection_retake_reason
from app.engine import diagnose
from app.parser import validate_schema
from app.vision import VisionDetectionError, vision_detect

load_dotenv()
configure_langsmith()

logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO)
    yield


app = FastAPI(title="Furniture Diagnosis API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


async def _read_and_validate_image(image: UploadFile) -> bytes:
    if image.content_type not in {None, "image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(status_code=422, detail="image must be jpg or png")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large")
    return image_bytes


async def _vision_detect_from_upload(image: UploadFile) -> dict:
    image_bytes = await _read_and_validate_image(image)
    try:
        return await asyncio.to_thread(vision_detect, image_bytes, image.content_type)
    except VisionDetectionError:
        return JSONResponse(status_code=502, content={"status": "api_error"})
    except RuntimeError:
        logger.exception("Vision configuration error")
        return JSONResponse(status_code=502, content={"status": "api_error"})


def _parse_detection_form(detection: str) -> dict:
    # Vision APIコストが発生しないため /detect より緩めてよい。
    # ただしエンジンのCPU消費と踏み台化を防ぐため無制限にはしない [DESIGN v2.4]
    if len(detection.encode("utf-8")) > MAX_DETECTION_JSON_BYTES:
        raise HTTPException(status_code=400, detail="detection JSON too large")

    try:
        parsed = json.loads(detection)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid detection JSON") from exc

    ok, reason = validate_schema(parsed)
    if not ok:
        raise HTTPException(status_code=400, detail=f"invalid detection: {reason}")

    if not parsed.get("furniture"):
        raise HTTPException(status_code=400, detail="furniture must not be empty")

    return parsed


@app.post("/detect")
@limiter.limit("10/minute")
async def detect_endpoint(
    request: Request,
    image: UploadFile = File(...),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    verify_app_key(x_app_key, get_app_shared_secret())

    detection_or_error = await _vision_detect_from_upload(image)
    if isinstance(detection_or_error, JSONResponse):
        return detection_or_error

    reason = detection_retake_reason(detection_or_error)
    if reason:
        return {"status": "retake", "reason": reason}

    return {"status": "ok", "detection": detection_or_error}


@app.post("/diagnose")
@limiter.limit("30/minute")
async def diagnose_endpoint(
    request: Request,
    structure: str = Form(...),
    floor_no: int = Form(...),
    base_isolated: bool = Form(...),
    image: UploadFile | None = File(None),
    detection: str | None = Form(None),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    verify_app_key(x_app_key, get_app_shared_secret())

    if structure not in VALID_STRUCTURE:
        raise HTTPException(status_code=422, detail=f"Invalid structure: {structure}")

    has_image = image is not None and image.filename
    has_detection = detection is not None and detection.strip() != ""

    if has_image and has_detection:
        raise HTTPException(
            status_code=400,
            detail="provide either image or detection, not both",
        )
    if not has_image and not has_detection:
        raise HTTPException(
            status_code=422,
            detail="either image or detection is required",
        )

    if has_image:
        detection_or_error = await _vision_detect_from_upload(image)
        if isinstance(detection_or_error, JSONResponse):
            return detection_or_error
        detection_obj = detection_or_error
    else:
        detection_obj = _parse_detection_form(detection)

    return diagnose(
        detection_obj,
        DEFAULT_SHINDO,
        DEFAULT_SOIL,
        structure,
        floor_no,
        base_isolated,
    )
