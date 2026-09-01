# デプロイ設計

## 方針

朝マズメ潮ナビと同じく、Cloudflare標準のGitリポジトリ連携ではなく、**GitHub Actions + Wrangler Direct Upload** を採用する。

```text
main
  |
  v
GitHub Actions
  |
  v
Wrangler
  |
  v
Cloudflare Worker
  |
  v
ato-ippai-api-poc.edward-se-pg.workers.dev
```

## 対象

- GitHub repository: `ha-rookie/ato-ippai-navi`
- Production branch: `main`
- Cloudflare Worker: `ato-ippai-api-poc`
- Wrangler config: `wrangler.jsonc`
- Worker entry point: `src/index.js`

リポジトリ名とWorker名は一致させる必要はない。

既存Workerへ更新デプロイするため、`wrangler.jsonc` の `name` はCloudflare上のWorker名 `ato-ippai-api-poc` と一致させる。

## GitHub Actions

Workflow:

```text
.github/workflows/deploy-worker.yml
```

実行条件:

- `main` のWorker関連ファイル変更
- GitHub Actionsからの手動実行

処理:

1. Checkout
2. `node --check src/index.js`
3. `wrangler deploy`
4. 公開Workerの `GET /health` をスモークテスト

## GitHub Repository Secrets

GitHub側には次の2つだけ登録する。

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

値はリポジトリへコミットしない。

Cloudflare API TokenはWorkerデプロイに必要な範囲だけに絞る。

## Cloudflare Worker Secret

Google Routes APIキーはGitHub Actions Secretへ移動しない。

既存Worker `ato-ippai-api-poc` に設定済みの次のSecretを維持する。

```text
GOOGLE_MAPS_API_KEY
```

Secretの値は `wrangler.jsonc` に記載しない。
Workerコードは `env.GOOGLE_MAPS_API_KEY` から参照する。

既存Workerへの通常の `wrangler deploy` では、Dashboardで登録済みのSecretをそのまま利用する前提とする。初回デプロイ後は `/health` の `googleApiKeyConfigured: true` で存在確認する。

## 完了判定

- GitHub Actionsのdeploy job成功
- Cloudflareに新しいWorkerバージョンが作成される
- `GET /health` がHTTP 200
- `ok: true`
- `googleApiKeyConfigured: true`

## 運用原則

- GitHubをコード・設計の正本とする
- Cloudflare DashboardでWorkerコードを直接編集しない
- APIキーをGitHubへコミットしない
- 本番変更は原則としてPRでレビューしてからmainへ反映する
