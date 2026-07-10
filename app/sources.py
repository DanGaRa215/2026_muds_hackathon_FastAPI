"""診断レスポンス用の出典メタデータ。数値は constants.py / suggestions.py が正本。"""

SOURCE_ORDER = ("NILIM", "JMA", "TFD-H", "TFD-M")

SOURCE_CATALOG: dict[str, dict] = {
    "NILIM": {
        "id": "NILIM",
        "title": "国土技術政策総合研究所「什器の転倒・滑動・落下」評価法",
        "summary": (
            "家具の種類ごとに、倒れ始める揺れの強さ（ガル）を実験から求めたデータです。"
        ),
        "used_for": ["家具ごとの転倒限界の判定"],
    },
    "JMA": {
        "id": "JMA",
        "title": "気象庁 震度と加速度の換算",
        "summary": "想定した震度を、床の揺れの強さ（ガル）に変換する際に使っています。",
        "used_for": ["想定震度から床応答への換算"],
    },
    "TFD-H": {
        "id": "TFD-H",
        "title": "東京消防庁「熊本地震における家具等の転倒等の実態調査」戸建編",
        "summary": (
            "L字金具で転倒率が33.5%から8.9%に低下（n=79）。"
            "耐震マット単独は39.7%（n=56）で効果が確認されていません。"
        ),
        "used_for": ["固定具の改善提案", "テレビ・冷蔵庫等の転倒率"],
    },
    "TFD-M": {
        "id": "TFD-M",
        "title": "東京消防庁「熊本地震における家具等の転倒等の実態調査」マンション編",
        "summary": (
            "異なる種類の固定具を2点以上併用した住戸では転倒が確認されていません"
            "（n=8のため参考値）。"
        ),
        "used_for": ["固定具の併用による低減", "免震構造での移動リスク"],
    },
}


def build_sources(used_ids: set[str]) -> list[dict]:
    return [SOURCE_CATALOG[sid] for sid in SOURCE_ORDER if sid in used_ids]
