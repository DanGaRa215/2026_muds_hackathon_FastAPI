"""Vision 検出結果の retake 判定（/detect 用）。"""

from app.constants import CONF_THRESHOLD


def _retake_reason(all_furniture: list[dict]) -> str:
    if any(
        any(b.get("confidence", 0) >= CONF_THRESHOLD for b in f.get("braces", []))
        for f in all_furniture
    ):
        return "brace_only"
    return "nothing_detected"


def detection_retake_reason(detection: dict) -> str | None:
    """信頼度閾値を通過した家具が無い場合の retake reason。通過時は None。"""
    all_furniture = detection.get("furniture", [])
    furniture_list = [
        f for f in all_furniture if f.get("confidence", 0) >= CONF_THRESHOLD
    ]

    if furniture_list:
        return None

    if "no_furniture" in detection.get("image_issues", []):
        return "no_furniture"
    return _retake_reason(all_furniture)
