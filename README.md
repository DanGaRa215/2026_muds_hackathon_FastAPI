# 家具安全診断 API (FastAPI)

Flutter クライアント向けの家具耐震診断バックエンドです。画像から LLM で家具・固定具を検出し、ルールベースエンジンでリスク判定した JSON を返します。

## 機能

- `GET /health` — ヘルスチェック
- `POST /diagnose` — 画像 + 補助入力から診断 JSON を返却

判定ロジック・API キーはすべてサーバー側に集約し、Flutter は返却 JSON を表示するだけです。

## ローカル起動

```bash
# 1. 依存関係
uv sync

# 2. 環境変数
cp .env.example .env
# .env を編集して APP_SHARED_SECRET / ANTHROPIC_API_KEY を設定

# 3. 起動
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

確認:

```bash
curl http://localhost:8000/health
```

## テスト

```bash
uv run pytest
```

診断エンジン (`tests/test_engine.py`) は LLM なしで T1〜T10 相当を検証します。

## 環境変数

| 変数 | 必須 | 説明 |
|---|---|---|
| `APP_SHARED_SECRET` | ✅ | Flutter から送る `X-App-Key` と照合 |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic Vision API キー |
| `ANTHROPIC_MODEL` | — | 既定: `claude-sonnet-4-6` |
| `LANGSMITH_TRACING` | — | `true` のときのみ LangSmith 有効 |
| `LANGSMITH_API_KEY` | — | LangSmith トレーシング用 |
| `LANGSMITH_PROJECT` | — | 既定: `furniture-diagnosis` |

## `/diagnose` 呼び出し例

```bash
curl -X POST http://localhost:8000/diagnose \
  -H "X-App-Key: your-secret" \
  -F "image=@/path/to/photo.jpg" \
  -F "shindo=s6weak" \
  -F "soil=normal" \
  -F "structure=wood" \
  -F "floor_no=1" \
  -F "base_isolated=false"
```

## レスポンス状態

| status | 意味 |
|---|---|
| `ok` | 診断成功。`results` をカード表示 |
| `retake` | 再撮影。`reason` で UI 分岐 |
| `api_error` | Vision 応答パース失敗 (502) |

## プロジェクト構成

```
app/
  constants.py   # 係数テーブル・プロンプト
  engine.py      # ルールベース判定（テスト可能）
  vision.py      # LangChain + Anthropic Vision
  suggestions.py # 改善提案生成
  parser.py      # LLM JSON 正規化
  auth.py        # X-App-Key 検証
main.py          # FastAPI エントリポイント
tests/           # 単体テスト
```

Render へのデプロイ手順は [DEPLOY.md](DEPLOY.md) を参照してください。
