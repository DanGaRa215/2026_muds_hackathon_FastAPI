import json
import re

from app.constants import (
    VALID_BRACE_CLASSES,
    VALID_FURNITURE_CLASSES,
    VALID_IMAGE_ISSUES,
    VALID_INSTALL_QUALITIES,
    WARDROBE_PROFILES,
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


def _normalize_brace(raw: dict) -> dict | None:
    cls = raw.get("class", "")
    if cls not in VALID_BRACE_CLASSES:
        return None

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

    braces = [
        brace
        for b in raw.get("braces", [])
        if isinstance(b, dict)
        for brace in [_normalize_brace(b)]
        if brace is not None
    ]

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


def _valid_bbox(value) -> bool:
    if value is None:
        return True
    if not isinstance(value, list) or len(value) != 4:
        return False
    return all(isinstance(v, (int, float)) for v in value)


def validate_schema(obj) -> tuple[bool, str]:
    """評価スイートと共有する検出JSONスキーマ検証。enum外は弾く。"""
    if not isinstance(obj, dict):
        return False, "root_not_dict"

    furniture = obj.get("furniture")
    if not isinstance(furniture, list):
        return False, "furniture_not_list"

    for item in furniture:
        if not isinstance(item, dict):
            return False, "furniture_item_not_dict"

        cls = item.get("class")
        if cls not in VALID_FURNITURE_CLASSES:
            return False, f"invalid_furniture_class:{cls}"

        conf = item.get("confidence")
        if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
            return False, f"invalid_confidence:{conf}"

        if not _valid_bbox(item.get("bbox")):
            return False, f"invalid_bbox:{item.get('bbox')}"

        profile = item.get("profile", None)
        if profile not in WARDROBE_PROFILES:
            return False, f"invalid_profile:{profile}"

        braces = item.get("braces")
        if not isinstance(braces, list):
            return False, "braces_not_list"

        for brace in braces:
            if not isinstance(brace, dict):
                return False, "brace_not_dict"

            bcls = brace.get("class")
            if bcls not in VALID_BRACE_CLASSES:
                return False, f"invalid_brace_class:{bcls}"

            iq = brace.get("install_quality")
            if iq not in VALID_INSTALL_QUALITIES:
                return False, f"invalid_install_quality:{iq}"

            bconf = brace.get("confidence")
            if not isinstance(bconf, (int, float)) or not (0.0 <= bconf <= 1.0):
                return False, f"invalid_brace_confidence:{bconf}"

            if not _valid_bbox(brace.get("bbox")):
                return False, f"invalid_brace_bbox:{brace.get('bbox')}"

    issues = obj.get("image_issues")
    if not isinstance(issues, list):
        return False, "image_issues_not_list"

    for issue in issues:
        if issue not in VALID_IMAGE_ISSUES:
            return False, f"invalid_image_issue:{issue}"

    return True, ""
