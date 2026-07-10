# 20260710_jan_diagnosis-v2_3 — FastAPI 作業記録

ブランチ: `20260710_jan_diagnosis-v2_3`  
対象: 診断結果の単一化（API 側）・根拠の平易化・出典表示  
Flutter 側の表示変更は `2026_muds_hackathon` リポジトリの別ブランチで実施。

---

## 背景

v2.2 で `display` / `suggestions` を導入したが、ユーザー試用で以下が問題になった。

1. 複数家具検出時に結果カードが増えすぎる → **UI は代表1件**、API は全件評価を維持
2. `reason_chain` が「200gal」「下回っている」のみで、中判定の理由が伝わらない
3. 出典（NILIM / 気象庁 / 東京消防庁調査）が画面に出てこない

本ブランチは **FastAPI の `/diagnose` レスポンス拡張のみ**（係数・閾値は変更なし）。

---

## 実施内容

### 1. `primary_index` の追加（Part A・API 側）

| 項目 | 内容 |
|---|---|
| 変更ファイル | `app/engine.py` |
| 挙動 | `diagnose()` は従来どおり全家具を評価し `results[]` に高リスク降順で格納 |
| 追加フィールド | レスポンス直下に `"primary_index": 0` |
| 意図 | Flutter が `results[0]` を代表カードとして描画するための明示インデックス |

**エンジンは家具を捨てない。** 表示の単一化は Flutter 側の責務。

---

### 2. 根拠文言の平易化（Part B）

| 項目 | 内容 |
|---|---|
| 変更ファイル | `app/engine.py` |
| Pトラック | 低 / 中 / 高の3分岐テンプレートに変更 |
| gal 説明 | `reason_chain` 先頭に「1ガル＝1cm/s²、気象庁換算」を必ず含める |
| 中判定の説明 | `0.7×A₀`（安全側マージン、例: 食器棚 162.4ガル）を明記し、「限界未満なのに中」の理由を説明 |
| Sトラック | 東京消防庁・熊本地震実態調査の転倒率を平易文に |
| 震度シフト | 「調査地域（震度6強相当）より強い/弱い」表現に変更 |
| modifier ラベル | 地盤・高層階・固定具・免震・clamp を一般向け文章に置換 |

`display.reason_chain` は `modifiers[].label` から生成（`app/display.py` の仕組みは維持）。

**変更していないもの:** `BASE_GAL` / `PHYSICS_TRACK` / `SAFETY_FACTOR(0.7)` / `FIXING_SHIFT_CORRECT` / `COMBO_SHIFT` 等の係数テーブル。

---

### 3. 出典 `sources[]` の追加（Part C）

| 項目 | 内容 |
|---|---|
| 新規ファイル | `app/sources.py` |
| 変更ファイル | `app/engine.py` |
| 挙動 | 診断中に実際に参照した出典 ID のみを集合収集 |
| 出力順 | `NILIM` → `JMA` → `TFD-H` → `TFD-M` |
| 各要素 | `id` / `title` / `summary` / `used_for` |

**収集ルール（例）**

| ケース | 含まれる ID |
|---|---|
| Pトラック本棚・未固定 | `NILIM`, `JMA`, `TFD-H`（L字提案のため） |
| Sトラックテレビ | `JMA`, `TFD-H` |
| 異種固定具併用 | 上記 + `TFD-M` |
| 判定対象外のみ | 空（Flutter はフォールバック辞書を使用） |

`summary` 内に「転倒0%」「絶対」等の断定表現は入れない（`constants.py` / `suggestions.py` 準拠）。

---

### 4. テスト追加

| ファイル | 内容 |
|---|---|
| `tests/test_v23.py` | v2.3 専用の回帰テスト 10 件 |

検証項目:

- `primary_index == 0`
- Pトラック低/中/高で `1ガル＝1cm/s²` が `reason_chain[0]` に含まれる
- 中判定（食器棚・震度6弱）で `162.4`（0.7×232）が含まれる
- Sトラック（テレビ）で `38.2%` と `東京消防庁`
- `sources[]` が実使用分のみ（physics 未固定で `TFD-M` なし）
- 複数家具でも `results` は2件返る（捨てない）
- 既存 T1〜T10 の `risk.level` は不変（`tests/test_engine.py` 32件 + v23 10件 = **42 passed**）

---

## コミット構成

| コミット | 概要 |
|---|---|
| `cfb80ab` | 出典メタデータ（`app/sources.py`）を追加 |
| `ad4e53f` | `primary_index`・平易化ラベル・`sources[]` を `engine.py` に実装 |
| `3dc3a02` | `tests/test_v23.py` を追加 |

---

## API レスポンス差分（概要）

```json
{
  "status": "ok",
  "input": { "...": "..." },
  "primary_index": 0,
  "results": [ "... 全件 ..." ],
  "unknowns": [ "..." ],
  "sources": [
    { "id": "NILIM", "title": "...", "summary": "...", "used_for": ["..."] }
  ]
}
```

---

## 後続（本ブランチのスコープ外）

- **Part E（v2.4）**: 検出確認ステップ（`/detect` 分割・ユーザー編集 UI）は未実装
- Flutter 側 v2.3（1件表示・出典折りたたみ・アイコン削減）は別リポジトリ

---

## セルフレビュー

- [x] `diagnose()` が家具を捨てず `results[]` 全件
- [x] `primary_index: 0` を追加
- [x] 中判定の `reason_chain` が 0.7×A₀ を説明
- [x] gal を「1ガル＝1cm/s²」と定義表記
- [x] `constants.py` / `suggestions.py` に無い数値を追加していない
- [x] `sources[]` が実使用分のみ
- [x] 係数テーブル未変更
- [x] `pytest` 42件通過
