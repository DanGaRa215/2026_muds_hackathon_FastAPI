# UI連携仕様書（メンバーC向け）

- 版: v2.2
- 対象: Flutter クライアント（家具診断画面）
- 前提: FastAPI `/diagnose` が `display` / `suggestions` を返す（v2.2以降）

---

## 1. 基本方針

Flutter は **APIを1本呼んで結果を表示するシンクライアント**。
表示に必要な日本語はバックエンドの `display` / `suggestions` を第一に使う。

---

## 2. 画面マッピング（§3）

### 3.1 レスポンス → UI 要素

| フィールド | UI 上の用途 | 備考 |
|---|---|---|
| `status` | 画面全体の分岐 | `ok` / `retake` / `api_error` |
| `results[]` | 家具カードのリスト | リスク降順ソート済み |
| `results[].furniture` | カード見出しの補助（クラス名） | **生の enum は表示しない** |
| `results[].display.headline` | カードのタイトル行 | **これを主表示にする。`risk.level` の生値は表示しない** |
| `results[].display.summary` | 1文の説明 | headline の直下 |
| `results[].display.reason_chain` | 「なぜこの判定？」折りたたみ内に箇条書き | 開くまで隠す |
| `results[].display.badge` | リスクバッジ（色＋形状） | §4 参照 |
| `results[].warnings` | 注意バナー | キーを §5 辞書で日本語化 |
| `results[].suggestions` | 対策提案リスト | §3.2 参照 |
| `results[].risk` | 内部判定（レベル・種別・modifiers） | デバッグ用。ユーザー向け主表示は `display` |
| `unknowns` | 免責・不確実性の一覧 | 画面下部または折りたたみ |
| `input` | 診断時の入力エコーバック | デバッグ・履歴保存用 |

**注記:** `bbox` はテキスト表示禁止。オーバーレイ描画のみに使う。

### 3.2 提案（suggestions）

`suggestions` は必ず配列で来る（空配列あり）。`priority` 降順ソート済み。
`text` をそのまま表示すればよい。`action` は将来のボタン化用キー。

### 3.3 bbox の扱い

LLM 由来の bbox は精度が低い可能性がある。枠がズレて見えるなら、
bbox 非依存の**カード UI のみ**に切り替える。

---

## 3. リスク表示（§4）

CUD 原則（色だけに頼らない）のため、`display.badge.shape` を併用する。

| level | label | shape |
|---|---|---|
| low | 低 | circle |
| mid | 中 | diamond |
| high | 高 | triangle |

---

## 4. 表示辞書（§5）

**日本語化はバックエンドの `display` を第一に使う。** 以下の辞書は
`display` が無い旧レスポンス／`braces[]` 表示のためのフォールバック。

### 家具クラス

| key | 日本語 |
|---|---|
| `furniture_bookshelf` | 本棚 |
| `furniture_wardrobe` | タンス |
| `furniture_cupboard` | 食器棚 |
| `furniture_refrigerator` | 冷蔵庫 |
| `furniture_tv` | テレビ（テレビ台含む） |
| `furniture_microwave_stand` | 電子レンジ台 |
| `furniture_desk` | 机 |
| `furniture_other` | その他の家具（判定対象外） |

### 固定具クラス

| key | 日本語 |
|---|---|
| `brace_tension_rod` | 突っ張り棒 |
| `brace_l_bracket` | L字金具 |
| `brace_mat` | 耐震マット |
| `brace_belt` | ベルト・チェーン |
| `brace_stopper` | ストッパー・転倒防止板 |

### install_quality

| key | 日本語 |
|---|---|
| `correct` | 適切に設置 |
| `loose` | 緩み・傾きあり（注意） |
| `wrong_position` | 取付位置が不適切（要見直し） |
| `unverified` | 写真では確認できず |

### warnings

| key | 日本語 |
|---|---|
| `recheck_after_quakes` | 繰り返しの揺れで固定具は緩みます。震度4程度の地震の後は点検を。 |
| `mat_ineffective_on_heavy` | 耐震マット単独は重い家具では効果が確認されていません。L字金具等の追加を推奨。 |
| `slide_on_high_floor` | 高層階では家具が「移動」するリスクがあります。キャスターは固定を。 |

### リスクレベル（フォールバック用）

| key | 日本語 |
|---|---|
| `high` | 高 |
| `mid` | 中 |
| `low` | 低 |

---

## 5. 状態分岐（§6）

| status | UI |
|---|---|
| `ok` | 結果カード一覧を表示 |
| `retake` | 撮り直し案内（`reason` に応じた文言） |
| `api_error` | エラーバナー＋再試行 |
