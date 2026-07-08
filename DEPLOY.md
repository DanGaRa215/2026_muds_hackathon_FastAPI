# Render デプロイ手順

## 1. Render Web Service を作成

1. [Render Dashboard](https://dashboard.render.com/) → **New +** → **Web Service**
2. この Git リポジトリを接続
3. 以下を設定:

| 項目 | 値 |
|---|---|
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |

## 2. 環境変数

Render の **Environment** タブで設定:

| Key | 必須 | 例 |
|---|---|---|
| `APP_SHARED_SECRET` | ✅ | チーム共有シークレット |
| `ANTHROPIC_API_KEY` | ✅ | Anthropic API キー |
| `ANTHROPIC_MODEL` | — | `claude-sonnet-4-6` |
| `LANGSMITH_TRACING` | — | `false` |
| `LANGSMITH_API_KEY` | — | （任意） |
| `LANGSMITH_PROJECT` | — | `furniture-diagnosis` |

**注意:** シークレットは GitHub / README / スクリーンショットに載せないこと。

## 3. デプロイ確認

```bash
curl https://<your-service>.onrender.com/health
# => {"status":"ok"}
```

## 4. Flutter 側設定

デプロイ後の URL を Flutter に `--dart-define` で注入:

```bash
flutter run \
  --dart-define=API_BASE_URL=https://<your-service>.onrender.com \
  --dart-define=APP_KEY=<APP_SHARED_SECRETと同じ値>
```

## 5. コールドスタート対策

Render 無料枠はスリープ後に起動が遅くなります。デモ 5 分前に `/health` を叩いてウォームアップしてください。

```bash
curl https://<your-service>.onrender.com/health
```

## 6. セキュリティチェックリスト

- [ ] Anthropic Console で Spend Limit を設定
- [ ] `APP_SHARED_SECRET` をチーム外に公開しない
- [ ] ハッカソン終了後にキーをローテーション

## 7. ローカル開発 (ngrok)

Render デプロイ前は ngrok で Flutter と接続できます:

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8000
ngrok http 8000
```

Flutter の `API_BASE_URL` に ngrok の HTTPS URL を指定してください。
