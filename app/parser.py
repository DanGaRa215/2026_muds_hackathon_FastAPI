import json
import re

from app.constants import (
    VALID_BRACE_CLASSES,
    VALID_FURNITURE_CLASSES,
    VALID_INSTALL_QUALITIES,
)


def extract_json_text(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def parse_json_response(raw: str) -> dict:
    return json.loads(extract_json_text(raw))


def _normalize_bbox(value) -> list[float] | None:
    if value is None:
        return None
    if isinstance(value, list) and len(value) == 4:
        return [float(v) for v in value]
    return None


def _normalize_brace(raw: dict) -> dict:
    cls = raw.get("class", "")
    if cls not in VALID_BRACE_CLASSES:
        cls = "brace_mat" if "mat" in cls else "brace_l_bracket"
        cls = cls if cls in VALID_BRACE_CLASSES else "brace_l_bracket"

    install_quality = raw.get("install_quality", "unverified")
    if install_quality not in VALID_INSTALL_QUALITIES:
        install_quality = "unverified"

    return {
        "class": cls,
        "confidence": float(raw.get("confidence", 0.0)),
        "install_quality": install_quality,
        "bbox": _normalize_bbox(raw.get("bbox")),
    }


def _normalize_furniture(raw: dict) -> dict:
    cls = raw.get("class", "furniture_other")
    if cls not in VALID_FURNITURE_CLASSES:
        cls = "furniture_other"

    profile = raw.get("profile")
    if profile not in {None, "tall", "chest"}:
        profile = None

    braces = [_normalize_brace(b) for b in raw.get("braces", []) if isinstance(b, dict)]

    return {
        "class": cls,
        "confidence": float(raw.get("confidence", 0.0)),
        "bbox": _normalize_bbox(raw.get("bbox")),
        "profile": profile,
        "braces": braces,
    }


def normalize_detection(raw: dict) -> dict:
    furniture = [
        _normalize_furniture(item)
        for item in raw.get("furniture", [])
        if isinstance(item, dict)
    ]
    image_issues = [
        issue
        for issue in raw.get("image_issues", [])
        if isinstance(issue, str)
    ]
    return {"furniture": furniture, "image_issues": image_issues}
