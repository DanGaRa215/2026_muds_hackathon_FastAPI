# 提案文の統計値はすべて出典付き。出典なき数値の追加は禁止。
#   33.5% → 8.9%  : [TFD-H] 東京消防庁 熊本地震実態調査 戸建編（未対策 vs L字金具 n=79）
#   n=8            : [TFD-M] 異種2点以上の併用。母数が小さいため「参考値」と必ず併記
#   マット単独      : [TFD-H] 39.7%(n=56)。「悪化する」と断定せず「効果が確認されていない」に留める
#
# 併用(n=8)は「大幅低減（参考値）」、マット(n=56)は「効果が確認されていない」で統一。
# 0%との断定禁止。

from app.constants import CONF_THRESHOLD, HEAVY_FURNITURE

BRACE_LABELS = {
    "brace_tension_rod": "突っ張り棒",
    "brace_l_bracket": "L字金具",
    "brace_mat": "耐震マット",
    "brace_belt": "ベルト・チェーン",
    "brace_stopper": "ストッパー",
}

S1 = {
    "action": "reposition",
    "text": "取付位置の見直しを。突っ張り棒は壁側（奥）へ寄せてください。天井の強度が不足する場合は当て板を使います。",
    "source": "DESIGN",
    "priority": 50,
}
S2 = {
    "action": "retighten",
    "text": "締め直し・張り直しを。繰り返しの揺れで固定具は緩みます。",
    "source": "DESIGN",
    "priority": 45,
}
S3 = {
    "action": "add_l_bracket",
    "text": "L字金具の設置を推奨。実調査では転倒率33.5%→8.9%（約1/4）に下がっています。",
    "source": "TFD-H",
    "priority": 40,
}
S4 = {
    "action": "add_brace_with_mat",
    "text": "L字金具かポール式（突っ張り棒）を追加して併用を。併用は実調査で転倒が確認されていません（n=8のため参考値）。",
    "source": "TFD-M",
    "priority": 38,
}
S5 = {
    "action": "add_second_brace",
    "text": "異種の固定具を併用すると、さらに大幅に低減できます（参考値）。",
    "source": "TFD-M",
    "priority": 30,
}
S6 = {
    "action": "confirm_fixing",
    "text": "固定具の設置状態が写真から確認できませんでした。固定部分が写るように撮り直すと、より正確に診断できます。",
    "source": "DESIGN",
    "priority": 25,
}
S7 = {
    "action": "secure_casters",
    "text": "高層階・免震構造では家具が「移動」します。キャスターはロックし、床との間にストッパーを。",
    "source": "DESIGN",
    "priority": 20,
}
S8 = {
    "action": "out_of_scope_note",
    "text": "この家具は判定対象外です。背の高い家具は上部を壁に固定してください。",
    "source": "DESIGN",
    "priority": 15,
}
S9 = {
    "action": "stud_note",
    "text": "石膏ボードへの直接ビス止めは効きません。下地（間柱）を探して固定してください。",
    "source": "DESIGN",
    "priority": 5,
}


def _valid_braces(braces: list[dict]) -> list[dict]:
    return [b for b in braces if b.get("confidence", 0) >= CONF_THRESHOLD]


def _effective_for_shift(braces: list[dict]) -> list[dict]:
    return [
        b
        for b in _valid_braces(braces)
        if b.get("install_quality") != "wrong_position"
    ]


def _has_distinct_correct_combo(braces: list[dict]) -> bool:
    correct_non_mat = {
        b["class"]
        for b in braces
        if b.get("install_quality") == "correct" and b["class"] != "brace_mat"
    }
    return len(correct_non_mat) >= 2


def _has_single_correct_non_mat(braces: list[dict]) -> bool:
    correct_non_mat = {
        b["class"]
        for b in braces
        if b.get("install_quality") == "correct" and b["class"] != "brace_mat"
    }
    return len(correct_non_mat) == 1


def _heavy_key(furniture: dict) -> str:
    if furniture.get("_physics_key"):
        return furniture["_physics_key"]
    cls = furniture["class"]
    if cls == "furniture_wardrobe":
        profile = furniture.get("profile")
        return "furniture_wardrobe_tall" if profile == "tall" else "furniture_wardrobe_chest"
    return cls


def _has_mat_only(braces: list[dict], heavy_key: str) -> bool:
    effective = _effective_for_shift(braces)
    return (
        len(effective) == 1
        and effective[0]["class"] == "brace_mat"
        and effective[0].get("install_quality") in ("correct", "loose")
        and heavy_key in HEAVY_FURNITURE
    )


def _has_no_effective_fixing(braces: list[dict]) -> bool:
    """未固定 = wrong_position / unverified を除く有効固定具が0件。"""
    effective = _effective_for_shift(braces)
    useful = [
        b
        for b in effective
        if b.get("install_quality") in ("correct", "loose")
    ]
    return len(useful) == 0


def build_suggestions(
    furniture: dict,
    braces: list[dict],
    level: int,
    risk_type: str,
    floor_no: int,
) -> list[dict]:
    """v1.0 出力5 準拠の提案リスト。priority 降順ソート済みで返す。"""
    cls = furniture["class"]
    if cls == "furniture_other":
        return [dict(S8)]

    valid = _valid_braces(braces)
    heavy_key = _heavy_key(furniture)
    suggestions: list[dict] = []
    stud_note_needed = False

    if any(b.get("install_quality") == "wrong_position" for b in valid):
        suggestions.append(dict(S1))

    if any(b.get("install_quality") == "loose" for b in valid):
        suggestions.append(dict(S2))

    if _has_no_effective_fixing(braces) and cls != "furniture_other":
        suggestions.append(dict(S3))
        stud_note_needed = True
    elif _has_mat_only(braces, heavy_key):
        suggestions.append(dict(S4))
        stud_note_needed = True
    elif _has_single_correct_non_mat(valid) and not _has_distinct_correct_combo(valid):
        suggestions.append(dict(S5))

    if any(b.get("install_quality") == "unverified" for b in valid):
        suggestions.append(dict(S6))

    if floor_no >= 11 or risk_type == "slide":
        suggestions.append(dict(S7))

    suggestions.sort(key=lambda item: item["priority"], reverse=True)
    main = suggestions[:3]

    if stud_note_needed:
        main.append(dict(S9))

    return main
