from typing import Any

from app.constants import (
    BASE_GAL,
    COMBO_SHIFT,
    CONF_THRESHOLD,
    FIX_MODIFIER_FACTORS,
    FIXING_SHIFT_CORRECT,
    HEAVY_FURNITURE,
    HIGH_FLOOR_THRESHOLD,
    PHYSICS_TRACK,
    RISK_LEVELS,
    SAFETY_FACTOR,
    SOIL_SHIFT,
    STAT_HIGH_RATE,
    STAT_MID_RATE,
    STAT_SHINDO_SHIFT,
    STAT_TRACK_RATE,
    UNKNOWN_DISCLAIMERS,
    Shindo,
)
from app.suggestions import build_suggestions


def resolve_physics_key(furniture: dict) -> str | None:
    cls = furniture["class"]
    if cls == "furniture_wardrobe":
        profile = furniture.get("profile")
        return "furniture_wardrobe_tall" if profile == "tall" else "furniture_wardrobe_chest"
    return cls if cls in PHYSICS_TRACK else None


def fixing_shift_of(braces: list[dict]) -> tuple[int, list[dict[str, Any]]]:
    corrects = [b for b in braces if b.get("install_quality") == "correct"]
    modifiers: list[dict[str, Any]] = []

    if len(corrects) >= 2:
        modifiers.append({"factor": "combo_fix", "shift": COMBO_SHIFT})
        return COMBO_SHIFT, modifiers

    if len(corrects) == 1:
        brace = corrects[0]
        shift = FIXING_SHIFT_CORRECT.get(brace["class"], 0)
        factor = FIX_MODIFIER_FACTORS.get(brace["class"])
        if factor and shift != 0:
            modifiers.append({"factor": factor, "shift": shift})
        return shift, modifiers

    return 0, modifiers


def _level_to_name(level: int) -> str:
    return RISK_LEVELS[max(0, min(2, level))]


def _retake_reason(all_furniture: list[dict]) -> str:
    if any(
        any(b.get("confidence", 0) >= CONF_THRESHOLD for b in f.get("braces", []))
        for f in all_furniture
    ):
        return "brace_only"
    return "nothing_detected"


def diagnose(
    detection: dict,
    shindo: str,
    soil: str,
    floor_no: int,
    base_isolated: bool,
) -> dict:
    all_furniture = detection.get("furniture", [])
    furniture_list = [
        f for f in all_furniture if f.get("confidence", 0) >= CONF_THRESHOLD
    ]

    if not furniture_list:
        if "no_furniture" in detection.get("image_issues", []):
            reason = "no_furniture"
        else:
            reason = _retake_reason(all_furniture)
        return {"status": "retake", "reason": reason}

    shindo_enum = Shindo(shindo)
    results: list[dict] = []

    for furniture in furniture_list:
        if furniture["class"] == "furniture_other":
            results.append(
                {
                    "furniture": furniture,
                    "braces": [],
                    "risk": None,
                    "warnings": [],
                    "suggestions": [],
                    "reference_only": True,
                    "out_of_scope": True,
                }
            )
            continue

        braces = [
            b for b in furniture.get("braces", []) if b.get("confidence", 0) >= CONF_THRESHOLD
        ]
        modifiers: list[dict] = []

        physics_key = resolve_physics_key(furniture)
        if physics_key:
            a0, ar50 = PHYSICS_TRACK[physics_key]
            a_eff = BASE_GAL[shindo_enum]
            level = 0 if a_eff < SAFETY_FACTOR * a0 else (1 if a_eff < ar50 else 2)
        else:
            rate = STAT_TRACK_RATE.get(furniture["class"], 20.0)
            level = 2 if rate >= STAT_HIGH_RATE else (1 if rate >= STAT_MID_RATE else 0)
            shift = STAT_SHINDO_SHIFT[shindo_enum]
            level += shift
            modifiers.append({"factor": "shindo_shift", "shift": shift})

        base_level = max(0, min(2, level))

        level += SOIL_SHIFT[soil]
        if floor_no >= HIGH_FLOOR_THRESHOLD:
            level += 1

        fix_shift, fix_modifiers = fixing_shift_of(braces)
        level += fix_shift
        modifiers.extend(fix_modifiers)
        level = max(0, min(2, level))

        risk_type = "topple"
        warnings: list[str] = []
        if base_isolated and level == 2:
            level, risk_type = 1, "slide"
        if floor_no >= HIGH_FLOOR_THRESHOLD:
            warnings.append("slide_on_high_floor")

        has_mat_only = len(braces) == 1 and braces[0]["class"] == "brace_mat"
        heavy_key = physics_key or furniture["class"]
        if has_mat_only and heavy_key in HEAVY_FURNITURE:
            warnings.append("mat_ineffective_on_heavy")
        if braces:
            warnings.append("recheck_after_quakes")

        results.append(
            {
                "furniture": furniture,
                "braces": braces,
                "risk": {
                    "level": _level_to_name(level),
                    "type": risk_type,
                    "base_level": _level_to_name(base_level),
                    "modifiers": modifiers,
                },
                "warnings": warnings,
                "suggestions": build_suggestions(
                    {**furniture, "_physics_key": physics_key}, braces
                ),
                "reference_only": True,
            }
        )

    results.sort(
        key=lambda r: {"low": 0, "mid": 1, "high": 2}.get(
            (r.get("risk") or {}).get("level"), -1
        ),
        reverse=True,
    )

    return {
        "status": "ok",
        "results": results,
        "unknowns": UNKNOWN_DISCLAIMERS,
    }
