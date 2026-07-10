# ============================================================
# 出典: [NILIM] 国総研「什器の転倒・滑動・落下」評価法
#       [JMA]   気象庁 震度⇔加速度換算
#       [TFD-H] 東京消防庁 熊本地震実態調査 戸建編
#       [TFD-M] 同 マンション編
#       [DESIGN] 設計判断値（出典数値ではない）
# ============================================================

from enum import Enum

MAX_IMAGE_BYTES = 5 * 1024 * 1024  # [DESIGN]
CONF_THRESHOLD = 0.5
SAFETY_FACTOR = 0.7  # [DESIGN]
STAT_HIGH_RATE = 30.0  # [DESIGN]
STAT_MID_RATE = 15.0  # [DESIGN]
COMBO_SHIFT = -2  # [TFD-M] n=8参考値
HIGH_FLOOR_THRESHOLD = 11

VALID_FURNITURE_CLASSES = {
    "furniture_bookshelf",
    "furniture_wardrobe",
    "furniture_cupboard",
    "furniture_refrigerator",
    "furniture_tv",
    "furniture_microwave_stand",
    "furniture_desk",
    "furniture_other",
}

VALID_BRACE_CLASSES = {
    "brace_tension_rod",
    "brace_l_bracket",
    "brace_mat",
    "brace_belt",
    "brace_stopper",
}

VALID_INSTALL_QUALITIES = {
    "correct",
    "loose",
    "wrong_position",
    "unverified",
}

VALID_IMAGE_ISSUES = {
    "too_dark",
    "furniture_cut_off",
    "no_furniture",
    "blurry",
}

WARDROBE_PROFILES = {None, "tall", "chest"}

# v2.4: クライアント由来 detection JSON の長さ上限 [DESIGN]
MAX_DETECTION_JSON_BYTES = 64 * 1024

VALID_SHINDO = {"s5weak", "s5strong", "s6weak", "s6strong", "s7"}
VALID_SOIL = {"hard", "normal", "soft"}
VALID_STRUCTURE = {"wood", "rc", "steel"}

# API入力廃止時の既定値 [DESIGN]
DEFAULT_SHINDO = "s6weak"
DEFAULT_SOIL = "normal"

UNKNOWN_DISCLAIMERS = [
    "収納物の重さ・重心",
    "壁・天井の下地強度",
    "床材の滑りやすさ",
    "固定具の劣化・締め付け",
    "実際の揺れの周期・継続時間",
]


class Shindo(str, Enum):
    s5weak = "s5weak"
    s5strong = "s5strong"
    s6weak = "s6weak"
    s6strong = "s6strong"
    s7 = "s7"


BASE_GAL = {  # [JMA]
    Shindo.s5weak: 50,
    Shindo.s5strong: 100,
    Shindo.s6weak: 200,
    Shindo.s6strong: 350,
    Shindo.s7: 600,
}

PHYSICS_TRACK = {  # [NILIM]
    "furniture_bookshelf": (174, 205),
    "furniture_cupboard": (232, 287),
    "furniture_wardrobe_tall": (327, 436),
    "furniture_wardrobe_chest": (315, 416),
    "furniture_desk": (535, 826),
}

STAT_TRACK_RATE = {  # [TFD-H]
    "furniture_tv": 38.2,
    "furniture_microwave_stand": 25.7,
    "furniture_refrigerator": 17.6,
}

STAT_SHINDO_SHIFT = {  # [DESIGN]
    Shindo.s7: 1,
    Shindo.s6strong: 0,
    Shindo.s6weak: -1,
    Shindo.s5strong: -2,
    Shindo.s5weak: -2,
}

FIXING_SHIFT_CORRECT = {  # [TFD-H]
    "brace_l_bracket": -1,
    "brace_tension_rod": -1,
    "brace_stopper": -1,
    "brace_belt": -1,
    "brace_mat": 0,
}

SOIL_SHIFT = {"hard": 0, "normal": 0, "soft": 1}  # [DESIGN]

HEAVY_FURNITURE = {
    "furniture_bookshelf",
    "furniture_cupboard",
    "furniture_wardrobe_tall",
    "furniture_wardrobe_chest",
    "furniture_refrigerator",
}

RISK_LEVELS = ("low", "mid", "high")

FIX_MODIFIER_FACTORS = {
    "brace_l_bracket": "fix_l_bracket_correct",
    "brace_tension_rod": "fix_tension_rod_correct",
    "brace_stopper": "fix_stopper_correct",
    "brace_belt": "fix_belt_correct",
    "brace_mat": "fix_mat_correct",
}

DETECTION_PROMPT = """あなたは家具の耐震固定を診断するための画像解析器です。
写真から以下だけを検出し、JSONのみを出力してください。説明文・マークダウン・コードブロック記号は一切出力しない。

# 検出対象
家具クラス（写っているものすべて）:
furniture_bookshelf（本棚）/ furniture_wardrobe（タンス）/ furniture_cupboard（食器棚）/
furniture_refrigerator（冷蔵庫）/ furniture_tv（テレビ。テレビ台と一体で1件として扱う）/
furniture_microwave_stand（電子レンジ台）/ furniture_desk（机）/ furniture_other（その他の大型家具）

固定具クラス（家具に取り付けられているものだけ）:
brace_tension_rod（突っ張り棒）/ brace_l_bracket（L字金具）/ brace_mat（耐震マット）/
brace_belt（ベルト・チェーン）/ brace_stopper（ストッパー・転倒防止板）

# ルール
- 写真に写っているものだけを報告する。見えない・推測の固定具を絶対に追加しない
  （例: 家具の下が見えない場合、マットが「あるはず」と推測しない）
- 家具ごとに、その家具に取り付いている固定具を braces 配列に入れる
- furniture_wardrobe の場合のみ profile を判定:
  背の高い洋服だんす="tall" / 背の低い整理だんす="chest" / 判別不能=null
- install_quality:
  correct（適切に設置されている）/ loose（緩み・傾き・浮きが見える）/
  wrong_position（取付位置が不適切。例: 突っ張り棒が家具の前面側・端に寄りすぎ）/
  unverified（写真からは判定できない）
- confidence: 0.0〜1.0
- bbox: 画像全体に対する [x, y, w, h]（0〜1の概算）。不明なら null
- 上記enum以外のクラス名・値を絶対に使わない

# 出力形式（このJSON構造のみ）
{
  "furniture": [
    {
      "class": "furniture_bookshelf",
      "confidence": 0.9,
      "bbox": [0.1, 0.05, 0.3, 0.8],
      "profile": null,
      "braces": [
        {"class": "brace_tension_rod", "confidence": 0.8,
         "install_quality": "correct", "bbox": [0.15, 0.02, 0.1, 0.06]}
      ]
    }
  ],
  "image_issues": []
}
image_issues に入れられる値: "too_dark" / "furniture_cut_off" / "no_furniture" / "blurry"
"""
