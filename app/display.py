"""表示用ブロック生成。ui_integration_spec_for_member_c.md §5 の辞書と一字一句同一。"""

FURNITURE_TITLES = {
    "furniture_bookshelf": "本棚",
    "furniture_wardrobe": "タンス",
    "furniture_cupboard": "食器棚",
    "furniture_refrigerator": "冷蔵庫",
    "furniture_tv": "テレビ（テレビ台含む）",
    "furniture_microwave_stand": "電子レンジ台",
    "furniture_desk": "机",
    "furniture_other": "その他の家具（判定対象外）",
}

LEVEL_LABELS = {"low": "低", "mid": "中", "high": "高"}

BADGE_SHAPES = {"low": "circle", "mid": "diamond", "high": "triangle"}

SUMMARY_TEMPLATES = {
    ("high", "topple"): "強い揺れで{title}が倒れる可能性が高い状態です。早めの対策をおすすめします。",
    ("high", "slide"): "強い揺れで{title}が床を滑って移動する可能性が高い状態です。",
    ("mid", "topple"): "揺れの条件によっては、{title}が倒れる可能性があります。",
    ("mid", "slide"): "揺れの条件によっては、{title}が移動する可能性があります。",
    ("low", "topple"): "想定した震度では、{title}は倒れにくい状態です。ただし参考値です。",
    ("low", "slide"): "想定した震度では、{title}は大きく移動しにくい状態です。ただし参考値です。",
}


def build_display(
    furniture_class: str,
    level_name: str,
    risk_type: str,
    modifiers: list[dict],
) -> dict:
    title = FURNITURE_TITLES.get(furniture_class, furniture_class)

    if furniture_class == "furniture_other":
        return {
            "title": title,
            "headline": "判定対象外",
            "summary": "この家具は判定に必要な基準値がないため、リスクを算出していません。",
            "reason_chain": [],
            "badge": {"level": "low", "label": "対象外", "shape": "circle"},
        }

    risk_word = "転倒" if risk_type == "topple" else "移動"
    level_label = LEVEL_LABELS[level_name]
    headline = f"{risk_word}リスク：{level_label}"
    summary = SUMMARY_TEMPLATES[(level_name, risk_type)].format(title=title)
    reason_chain = [m["label"] for m in modifiers if m.get("label")]

    return {
        "title": title,
        "headline": headline,
        "summary": summary,
        "reason_chain": reason_chain,
        "badge": {
            "level": level_name,
            "label": level_label,
            "shape": BADGE_SHAPES[level_name],
        },
    }
