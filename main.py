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
from app.constants import MAX_IMAGE_BYTES, VALID_SHINDO, VALID_SOIL, VALID_STRUCTURE
from app.engine import diagnose
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


def _validate_form_fields(
    shindo: str,
    soil: str,
    structure: str,
) -> None:
    if shindo not in VALID_SHINDO:
        raise HTTPException(status_code=422, detail=f"Invalid shindo: {shindo}")
    if soil not in VALID_SOIL:
        raise HTTPException(status_code=422, detail=f"Invalid soil: {soil}")
    if structure not in VALID_STRUCTURE:
        raise HTTPException(status_code=422, detail=f"Invalid structure: {structure}")


@app.post("/diagnose")
@limiter.limit("10/minute")
async def diagnose_endpoint(
    request: Request,
    image: UploadFile = File(...),
    shindo: str = Form(...),
    soil: str = Form(...),
    structure: str = Form(...),
    floor_no: int = Form(...),
    base_isolated: bool = Form(...),
    x_app_key: str | None = Header(default=None, alias="X-App-Key"),
):
    verify_app_key(x_app_key, get_app_shared_secret())
    _validate_form_fields(shindo, soil, structure)

    if image.content_type not in {None, "image/jpeg", "image/png", "image/jpg"}:
        raise HTTPException(status_code=422, detail="image must be jpg or png")

    image_bytes = await image.read()
    if len(image_bytes) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="image too large")

    # structure is reserved for future rule extensions.
    _ = structure

    try:
        detection = vision_detect(image_bytes, image.content_type)
    except VisionDetectionError:
        return JSONResponse(status_code=502, content={"status": "api_error"})
    except RuntimeError as exc:
        logger.exception("Vision configuration error")
        return JSONResponse(status_code=502, content={"status": "api_error", "detail": str(exc)})

    return diagnose(detection, shindo, soil, floor_no, base_isolated)
