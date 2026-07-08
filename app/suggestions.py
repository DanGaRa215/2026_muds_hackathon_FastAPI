from app.constants import HEAVY_FURNITURE


def build_suggestions(furniture: dict, braces: list[dict]) -> list[dict]:
    suggestions: list[dict] = []
    correct_braces = [b for b in braces if b.get("install_quality") == "correct"]
    loose_braces = [b for b in braces if b.get("install_quality") == "loose"]
    wrong_braces = [b for b in braces if b.get("install_quality") == "wrong_position"]

    has_mat_only = (
        len(braces) == 1
        and braces[0]["class"] == "brace_mat"
        and braces[0].get("install_quality") == "correct"
    )
    heavy_key = furniture.get("_physics_key") or furniture["class"]
    if not correct_braces:
        suggestions.append(
            {
                "action": "add_l_bracket",
                "text": (
                    "L字金具の設置を推奨。実調査で転倒率33.5%→8.9%（約1/4）。"
                    "石膏ボードへの直接ビス止めは効きません（下地に固定）"
                ),
                "source": "TFD-H",
            }
        )
    elif has_mat_only and heavy_key in HEAVY_FURNITURE:
        suggestions.append(
            {
                "action": "add_second_brace",
                "text": (
                    "L字金具かポール式を追加（併用）。"
                    "併用は実調査で転倒0件（n=8のため参考値）"
                ),
                "source": "TFD-M",
            }
        )
    elif len(correct_braces) == 1:
        suggestions.append(
            {
                "action": "add_second_brace",
                "text": "異種の固定具を併用するとさらに大幅低減（参考値）",
                "source": "TFD-M",
            }
        )

    if loose_braces:
        suggestions.append(
            {
                "action": "retighten_brace",
                "text": "締め直し・張り直しを。繰り返しの揺れで緩みます",
                "source": "TFD-H",
            }
        )

    if wrong_braces:
        suggestions.append(
            {
                "action": "fix_position",
                "text": (
                    "取付位置の見直しを。突っ張り棒は壁側（奥）へ、"
                    "天井強度不足時は当て板"
                ),
                "source": "DESIGN",
            }
        )

    return suggestions
