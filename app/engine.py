from typing import Any

from app.constants import (
    BASE_GAL,
    COMBO_SHIFT,
    CONF_THRESHOLD,
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
from app.display import FURNITURE_TITLES, build_display
from app.suggestions import build_suggestions

# structure は現行v1.0係数表に対応する出典値が存在しないためリスク計算に未使用。
# レスポンスの input エコーバックと、将来の木造/RC別係数（要追加調査）のために受け取る。

SHINDO_LABELS = {
    Shindo.s5weak: "震度5弱",
    Shindo.s5strong: "震度5強",
    Shindo.s6weak: "震度6弱",
    Shindo.s6strong: "震度6強",
    Shindo.s7: "震度7",
}

PHYSICS_TITLES = {
    "furniture_bookshelf": "本棚",
    "furniture_cupboard": "食器棚",
    "furniture_wardrobe_tall": "タンス（洋服だんす）",
    "furniture_wardrobe_chest": "タンス（整理だんす）",
    "furniture_desk": "机",
}

BRACE_LABELS = {
    "brace_tension_rod": "突っ張り棒",
    "brace_l_bracket": "L字金具",
    "brace_mat": "耐震マット",
    "brace_belt": "ベルト・チェーン",
    "brace_stopper": "ストッパー",
}

BRACE_FACTOR_SUFFIX = {
    "brace_l_bracket": "l_bracket",
    "brace_tension_rod": "tension_rod",
    "brace_stopper": "stopper",
    "brace_belt": "belt",
    "brace_mat": "mat",
}


def resolve_physics_key(furniture: dict) -> str | None:
    cls = furniture["class"]
    if cls == "furniture_wardrobe":
        profile = furniture.get("profile")
        return "furniture_wardrobe_tall" if profile == "tall" else "furniture_wardrobe_chest"
    return cls if cls in PHYSICS_TRACK else None


def _round_shift_toward_zero(shift: int) -> int:
    """loose 用: シフトを +1 側へ丸める（-2→-1, -1→0, 0→0）。"""
    return min(shift + 1, 0)


def _shift_from_correct_like(braces: list[dict]) -> tuple[int, list[dict[str, Any]]]:
    """correct（または loose-only 時の loose）からシフトと modifier を算出。"""
    modifiers: list[dict[str, Any]] = []
    non_mat = [b for b in braces if b["class"] != "brace_mat"]
    unique_classes = {b["class"] for b in non_mat}

    # [TFD-M] 異種2点以上の correct 併用（例:ポール+ストッパー）: 転倒0%（n=8のため参考値）
    # [DESIGN][要確認] brace_mat は FIXING_SHIFT_CORRECT==0 のため併用カウントから除外。
    # マット+L字を併用扱いにすると出典（ポール+ストッパー n=8）の外挿になる。
    if len(unique_classes) >= 2:
        modifiers.append(
            {
                "factor": "fix_combo_correct",
                "shift": COMBO_SHIFT,
                "label": "2種類の固定具の併用で大幅に低減（参考値）",
            }
        )
        return COMBO_SHIFT, modifiers

    if len(unique_classes) == 1:
        brace_class = next(iter(unique_classes))
        shift = FIXING_SHIFT_CORRECT.get(brace_class, 0)
        suffix = BRACE_FACTOR_SUFFIX.get(brace_class, brace_class.removeprefix("brace_"))
        label = BRACE_LABELS.get(brace_class, brace_class)
        if shift != 0:
            modifiers.append(
                {
                    "factor": f"fix_{suffix}_correct",
                    "shift": shift,
                    "label": f"{label}（適切に設置）で1段階低減",
                }
            )
        return shift, modifiers

    if len(braces) == 1 and braces[0]["class"] == "brace_mat":
        return FIXING_SHIFT_CORRECT["brace_mat"], modifiers

    return 0, modifiers


def fixing_shift_of(braces: list[dict]) -> tuple[int, list[dict[str, Any]]]:
    """[DESIGN] install_quality 補正付きの固定具シフト。シフト値と modifiers を返す。"""
    valid = [b for b in braces if b.get("confidence", 0) >= CONF_THRESHOLD]
    modifiers: list[dict[str, Any]] = []

    correct = [b for b in valid if b.get("install_quality") == "correct"]
    loose = [b for b in valid if b.get("install_quality") == "loose"]
    wrong = [b for b in valid if b.get("install_quality") == "wrong_position"]
    unverified = [b for b in valid if b.get("install_quality") == "unverified"]

    shift = 0
    if correct:
        shift, fix_mods = _shift_from_correct_like(correct)
        modifiers.extend(fix_mods)
    elif loose:
        raw_shift, fix_mods = _shift_from_correct_like(loose)
        shift = _round_shift_toward_zero(raw_shift)
        for mod in fix_mods:
            suffix = mod["factor"].removeprefix("fix_").removesuffix("_correct")
            modifiers.append(
                {
                    "factor": f"fix_{suffix}_loose",
                    "shift": shift,
                    "label": f"{BRACE_LABELS.get('brace_' + suffix, suffix)}に緩みがあるため低減を見込めません",
                }
            )

    for brace in loose:
        if correct:
            suffix = BRACE_FACTOR_SUFFIX.get(brace["class"], brace["class"].removeprefix("brace_"))
            label = BRACE_LABELS.get(brace["class"], brace["class"])
            modifiers.append(
                {
                    "factor": f"fix_{suffix}_loose",
                    "shift": 0,
                    "label": f"{label}に緩みがあるため低減を見込めません",
                }
            )

    for brace in wrong:
        modifiers.append(
            {
                "factor": "fix_wrong_position",
                "shift": 0,
                "label": "取付位置が不適切なため低減を見込めません",
            }
        )

    for brace in unverified:
        modifiers.append(
            {
                "factor": "fix_unverified",
                "shift": 0,
                "label": "写真から設置状態を確認できないため低減を見込めません",
            }
        )

    return shift, modifiers


def _level_to_name(level: int) -> str:
    return RISK_LEVELS[max(0, min(2, level))]


def _level_to_int(level_name: str) -> int:
    return {"low": 0, "mid": 1, "high": 2}[level_name]


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
    structure: str,
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
            display = build_display("furniture_other", "low", "topple", [])
            results.append(
                {
                    "furniture": furniture,
                    "braces": [],
                    "risk": None,
                    "display": display,
                    "warnings": [],
                    "suggestions": build_suggestions(
                        furniture, [], 0, "topple", floor_no
                    ),
                    "reference_only": True,
                    "out_of_scope": True,
                }
            )
            continue

        braces = [
            b for b in furniture.get("braces", []) if b.get("confidence", 0) >= CONF_THRESHOLD
        ]
        modifiers: list[dict[str, Any]] = []

        physics_key = resolve_physics_key(furniture)
        if physics_key:
            a0, ar50 = PHYSICS_TRACK[physics_key]
            a_eff = BASE_GAL[shindo_enum]
            level = 0 if a_eff < SAFETY_FACTOR * a0 else (1 if a_eff < ar50 else 2)
            title = PHYSICS_TITLES.get(physics_key, physics_key)
            if a_eff >= SAFETY_FACTOR * a0:
                compare = "上回っています" if a_eff >= a0 else "基準付近です"
            else:
                compare = "下回っています"
            modifiers.append(
                {
                    "factor": "track_physics",
                    "shift": 0,
                    "label": (
                        f"想定{SHINDO_LABELS[shindo_enum]}の床応答{a_eff}galが、"
                        f"{title}の転倒限界{a0}galを{compare}"
                    ),
                }
            )
        else:
            rate = STAT_TRACK_RATE.get(furniture["class"], 20.0)
            title = FURNITURE_TITLES.get(furniture["class"], furniture["class"])
            level = 2 if rate >= STAT_HIGH_RATE else (1 if rate >= STAT_MID_RATE else 0)
            modifiers.append(
                {
                    "factor": "track_stat",
                    "shift": 0,
                    "label": f"調査での転倒率{rate}%（{title}）を基準にしています",
                }
            )
            shift = STAT_SHINDO_SHIFT[shindo_enum]
            if shift != 0:
                level += shift
                direction = "引き上げ" if shift > 0 else "引き下げ"
                modifiers.append(
                    {
                        "factor": "shindo_shift",
                        "shift": shift,
                        "label": f"想定{SHINDO_LABELS[shindo_enum]}のため1段階{direction}",
                    }
                )

        base_level = max(0, min(2, level))

        if SOIL_SHIFT[soil] != 0:
            level += SOIL_SHIFT[soil]
            modifiers.append(
                {
                    "factor": "soil_soft",
                    "shift": SOIL_SHIFT[soil],
                    "label": "軟弱地盤のため1段階引き上げ",
                }
            )

        if floor_no >= HIGH_FLOOR_THRESHOLD:
            level += 1
            modifiers.append(
                {
                    "factor": "high_floor",
                    "shift": 1,
                    "label": "11階以上のため1段階引き上げ",
                }
            )

        fix_shift, fix_modifiers = fixing_shift_of(braces)
        level += fix_shift
        modifiers.extend(fix_modifiers)

        pre_clamp = level
        level = max(0, min(2, level))
        if level != pre_clamp:
            modifiers.append(
                {
                    "factor": "clamp",
                    "shift": 0,
                    "label": "これ以上は下がりません（3段階評価の下限/上限）",
                }
            )

        risk_type = "topple"
        if base_isolated and level == 2:
            level = 1
            risk_type = "slide"
            modifiers.append(
                {
                    "factor": "base_isolated_cap",
                    "shift": -1,
                    "label": "免震構造のため、転倒ではなく移動のリスクとして評価しています",
                }
            )

        level_name = _level_to_name(level)
        warnings: list[str] = []
        if floor_no >= HIGH_FLOOR_THRESHOLD:
            warnings.append("slide_on_high_floor")

        effective = [
            b
            for b in braces
            if b.get("confidence", 0) >= CONF_THRESHOLD
            and b.get("install_quality") != "wrong_position"
        ]
        has_mat_only = (
            len(effective) == 1
            and effective[0]["class"] == "brace_mat"
            and effective[0].get("install_quality") in ("correct", "loose")
        )
        heavy_key = physics_key or furniture["class"]
        if has_mat_only and heavy_key in HEAVY_FURNITURE:
            warnings.append("mat_ineffective_on_heavy")
        if braces:
            warnings.append("recheck_after_quakes")

        display = build_display(
            furniture["class"],
            level_name,
            risk_type,
            modifiers,
        )
        suggestions = build_suggestions(
            {**furniture, "_physics_key": physics_key},
            braces,
            _level_to_int(level_name),
            risk_type,
            floor_no,
        )

        results.append(
            {
                "furniture": furniture,
                "braces": braces,
                "risk": {
                    "level": level_name,
                    "type": risk_type,
                    "base_level": _level_to_name(base_level),
                    "modifiers": modifiers,
                },
                "display": display,
                "warnings": warnings,
                "suggestions": suggestions,
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
        "input": {
            "shindo": shindo,
            "soil": soil,
            "structure": structure,
            "floor_no": floor_no,
            "base_isolated": base_isolated,
        },
        "results": results,
        "unknowns": UNKNOWN_DISCLAIMERS,
    }
