# 20260711_jan_detection-confirm-v2_4 — FastAPI 作業記録

**PRタイトル:** `v2.4: 検出確認用に /detect 分割と detection JSON 診断を追加`

ブランチ: `20260711_jan_detection-confirm-v2_4`  
前提: v2.3（`primary_index` / 平易化 `reason_chain` / `sources[]`）マージ済み

---

## 目的

Vision（LLM）の誤検出を、ルールエンジンに渡す前にユーザーが補正できるよう、
API を **検出（/detect）** と **判定（/diagnose）** の2段階に分離する。

```
旧: 画像 → POST /diagnose → vision_detect() → diagnose()
新: 画像 → POST /detect → ユーザー確認・編集 → POST /diagnose(JSON) → diagnose()
```

---

## 実施内容

### 1. `validate_schema()` の本番移植

| ファイル | 内容 |
|---|---|
| `app/parser.py` | 評価スイート `eval_common.validate_schema` と同等の検証を追加 |
| `app/constants.py` | `VALID_IMAGE_ISSUES` / `WARDROBE_PROFILES` / `MAX_DETECTION_JSON_BYTES`（64KB） |

クライアント由来の `detection` は信頼せず、enum 外・不正 confidence・不正 bbox は **400** で弾く。

### 2. `/detect` 新設

| 項目 | 内容 |
|---|---|
| 入力 | 画像のみ（multipart） |
| 処理 | `vision_detect()` → `detection_retake_reason()` |
| 成功 | `{"status":"ok","detection":{...}}` |
| retake | 家具0件 / `no_furniture` / `brace_only` |
| レート制限 | 10/minute（Vision コストのため） |

retake 判定ロジックは `app/detection.py` に切り出し。

### 3. `/diagnose` 拡張（後方互換）

| 入力 | 挙動 |
|---|---|
| `image` のみ | 従来どおり vision → diagnose（v2.2/v2.3 互換） |
| `detection` JSON のみ | vision スキップ → `validate_schema` → diagnose |
| 両方 | 400 |
| どちらも無し | 422 |

| 項目 | 値 |
|---|---|
| レート制限 | 30/minute（Vision コストなし [DESIGN v2.4]） |
| JSON 上限 | 64KB |

### 4. 変更していないもの

- `DETECTION_PROMPT` / enum 文字列
- 係数・閾値テーブル
- `diagnose()` エンジン本体のリスク計算ロジック

ユーザー申告固定具（`confidence: 1.0`, `install_quality: unverified`）は
既存 v2.2 どおり **リスクを下げない**（`fix_unverified`, shift==0）。

---

## コミット構成

| コミット | 概要 |
|---|---|
| `fd8e433` | `validate_schema` / `detection_retake_reason` / 定数追加 |
| `b993bea` | `POST /detect` と `/diagnose` detection JSON 対応 |
| `5b128a7` | `tests/test_v24.py` |

---

## テスト

- **pytest 51件通過**（既存 `/diagnose` 画像入力テスト含む）
- v2.4 新規: `/detect` ok/retake、JSON diagnose で vision 未呼び出し、
  image+detection 400、enum外 400、64KB超 400、401、unverified 非低減

---

## セルフレビュー

- [x] Vision と diagnose が2エンドポイントに分離
- [x] 既存 `/diagnose`（画像）後方互換
- [x] `validate_schema()` 必須（enum外 → 400）
- [x] detection JSON 64KB 上限
- [x] ユーザー ON 固定具は `unverified` で非低減
- [x] `DETECTION_PROMPT` / enum 未変更

---

## Flutter 側（別リポジトリ）

検出確認画面・`DiagnosisApiClient` 2段階化は
`2026_muds_hackathon` の同ブランチで実施。
