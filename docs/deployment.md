# デプロイ設計

## 方針

「あと一杯ナビ」は、**Cloudflare Pagesを利用者向け公開入口、Cloudflare WorkerをAPIバックエンド**として分離します。

独自ドメインは使用せず、朝マズメ潮ナビと同じ `*.pages.dev` ルールで公開します。

```text
main
  |
  +--> Deploy Pages to Cloudflare
  |      ├─ syntax check
  |      ├─ npm test
  |      ├─ Pages build marker生成
  |      ├─ wrangler pages deploy
  |      └─ Pages production smoke
  |             |
  |             v
  |      https://ato-ippai.pages.dev
  |             |
  |             └─ Pages Functions
  |                    |
  |                    v
  +--> Deploy Worker to Cloudflare
         ├─ syntax check
         ├─ npm test
         ├─ wrangler deploy --config wrangler.worker.jsonc
         └─ Core API production smoke
                |
                v
         API Worker
                |
                └─ workflow_run
                     └─ 路線別 production smoke
```

## Production

### 利用者向け

- Cloudflare Pages project: `ato-ippai`
- Production URL: `https://ato-ippai.pages.dev`
- Pages config: `wrangler.jsonc`
- Static output: `public/`
- Pages Functions: `functions/`

### APIバックエンド

- Worker: `ato-ippai-api-poc`
- Worker config: `wrangler.worker.jsonc`
- entry: `src/index.js`
- Worker `workers.dev` URLは内部originとしてのみ利用する

## Pages deploy

Workflow:

```text
.github/workflows/deploy-pages.yml
```

主な実行条件:

- `main` の `public/**`
- `functions/**`
- `wrangler.jsonc`
- `package.json` / `package-lock.json`
- workflow自身
- 手動 `workflow_dispatch`

処理順:

1. Checkout
2. Pages Functions / frontend JavaScript syntax check
3. `npm test`
4. `public/build.json` にGit SHAを書き出す
5. `wrangler pages project create ato-ippai --production-branch main || true`
6. `wrangler pages deploy public --project-name=ato-ippai --branch=main`
7. Pages production smoke

### Pages build SHA

PagesはAPI Workerの `/health` と異なり、デプロイしたfrontend commitを返すendpointを持たないため、deploy時に次を生成します。

```text
public/build.json
```

内容:

```json
{"buildSha":"<github sha>"}
```

production smokeは `https://ato-ippai.pages.dev/build.json` を取得し、期待SHAと一致するまで短時間リトライします。

`build.json` はdeploy時の一時生成物であり、Git管理しません。

## Pages Functions proxy

```text
functions/[[path]].js
```

次のパスだけをAPI Workerへ中継します。

- `/api/*`
- `/ops/*`
- `/health`

それ以外は `context.next()` でPages Static Assetsへ渡します。

これにより、ブラウザは常に `ato-ippai.pages.dev` の同一オリジンでアクセスできます。

Google Routes APIキーはPagesへ置きません。既存API Worker Secretをそのまま利用します。

## Worker deploy

Workflow:

```text
.github/workflows/deploy-worker.yml
```

主な実行条件:

- `main` の `src/**`
- `test/**`
- `wrangler.worker.jsonc`
- `package.json` / `package-lock.json`
- workflow自身
- 手動 `workflow_dispatch`

`public/**` の変更ではWorkerを再デプロイしません。

Worker deploy:

```text
wrangler deploy --config wrangler.worker.jsonc --var BUILD_SHA:<github sha>
```

Worker側ではStatic Assetsを配信せず、API処理だけを担当します。

## Worker BUILD_SHA

`GET /health` の `buildSha` とGitHub commit SHAを比較し、期待したWorker commitがproductionへ反映されたことを確認します。

確認項目:

- `ok: true`
- `service: ato-ippai-api-poc`
- `googleApiKeyConfigured: true`
- `buildSha == github.sha`

## Pages production smoke

Pages deploy直後に次を確認します。

### 1. 新しいPages build

- `/build.json`
- `buildSha == github.sha`

### 2. UI / SPA

- `/` に `<title>あと一杯ナビ</title>`
- `/last-train` がindex.htmlへSPA fallbackされる
- `app.js` など主要assetが取得可能

### 3. Pages → Worker proxy

- `/health` が正常
- `/ops/last-train-boundaries.csv` が100行超のverified production dataを返す
- `/api/last-train-boundary` がH22藤が丘の代表ケースで正常

### 4. 非公開endpoint

Pages経由でも次が404であることを確認します。

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

## Core API production smoke

Worker deploy直後に次を確認します。

- Worker build SHA
- 非公開低レベルAPIが404
- operations CSV
- H22代表のlast-train boundary
- `/api/tonight-decision` の終電 + タクシー
- `taxiDestination` 任意上書きがHTTP 400

UIの取得確認はWorker smokeから外します。UIはPages側の責務です。

## 路線別 production smoke

路線別smokeはAPI Workerのデプロイ成功を `workflow_run` で受け、引き続きAPI Workerを直接検証します。

これはデータ/判定ロジックの検証であり、Pagesの配信確認とは責務を分離します。

`Smoke Last Train Production` だけはUI/SPA assetの検証なので、`Deploy Pages to Cloudflare` 成功後に `https://ato-ippai.pages.dev` を確認します。

## GitHub Repository Secrets

GitHub側にはCloudflare deploy用Secretだけを置きます。

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

Google Maps APIキーはGitHubへ追加しません。

## Cloudflare Worker Secret

```text
GOOGLE_MAPS_API_KEY
```

API Workerが `env.GOOGLE_MAPS_API_KEY` から参照します。

Pages FunctionsはAPI Workerへ中継するだけなので、このSecretをPagesへ複製する必要はありません。

## Wrangler config

### Pages

```text
wrangler.jsonc
```

```jsonc
{
  "name": "ato-ippai",
  "pages_build_output_dir": "./public",
  "compatibility_date": "2026-09-01"
}
```

### Worker

```text
wrangler.worker.jsonc
```

```jsonc
{
  "name": "ato-ippai-api-poc",
  "main": "src/index.js",
  "compatibility_date": "2026-09-01"
}
```

## npm scripts

```text
npm run dev            # Pages local development
npm run deploy         # Pages deploy
npm run dev:worker     # API Worker local development
npm run deploy:worker  # API Worker deploy
```

## 本番完了判定

### Pages変更

- PR CI green
- mainへmerge
- `Deploy Pages to Cloudflare` success
- Pages build SHA一致
- Pages production smoke success
- `/last-train` 専用smoke success（対象変更時）

### API Worker変更

- PR CI green
- 必要な公式ソースverification green
- mainへmerge
- `Deploy Worker to Cloudflare` success
- Worker BUILD_SHA一致
- Core API production smoke success
- 対象路線のproduction smoke success

## 運用原則

- GitHubをコード・設計・workflowの正本とする
- 利用者向け正式URLは `https://ato-ippai.pages.dev`
- `workers.dev` URLを利用者向け案内に使用しない
- Cloudflare Dashboardでコードを直接編集しない
- APIキー・Secret値をGitHubへコミットしない
- frontend変更とAPI変更を別デプロイにする
- verification不能時はfail-closedとする
