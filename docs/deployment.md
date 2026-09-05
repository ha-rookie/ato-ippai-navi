# デプロイ設計

## 方針

「あと一杯ナビ」は、Cloudflare標準のGitリポジトリ連携ではなく、**GitHub Actions + Wrangler Direct Upload** でCloudflare Workerへデプロイします。

```text
main
  |
  v
GitHub Actions: Deploy Worker to Cloudflare
  |
  ├─ JavaScript syntax check
  ├─ npm test
  ├─ Wrangler deploy
  └─ Core production smoke
         |
         v
Cloudflare Worker
         |
         └─ workflow_run
              └─ 路線別 production smoke
```

## 対象

- GitHub repository: `ha-rookie/ato-ippai-navi`
- Production branch: `main`
- Cloudflare Worker: `ato-ippai-api-poc`
- Production URL: `https://ato-ippai-api-poc.edward-se-pg.workers.dev`
- Wrangler config: `wrangler.jsonc`
- Worker entry point: `src/index.js`

リポジトリ名とWorker名は一致させる必要はありません。

既存Workerへ更新デプロイするため、`wrangler.jsonc` の `name` はCloudflare上のWorker名 `ato-ippai-api-poc` と一致させます。

## GitHub Actions

メインWorkflow:

```text
.github/workflows/deploy-worker.yml
```

実行条件:

- `main` の `src/**`
- `public/**`
- `test/**`
- `wrangler.jsonc`
- `package.json` / `package-lock.json`
- deploy workflow自身
- 手動 `workflow_dispatch`

### Deploy job

処理順:

1. Checkout
2. JavaScript syntax check
3. `npm test`
4. Wrangler deploy
5. Core production smoke

syntax check対象にはWorkerだけでなく主要フロントエンドJavaScriptも含めます。

```text
src/index.js
src/last-train.js
public/app.js
public/js/sleep.js
public/js/settings.js
```

## BUILD_SHA

Wrangler deploy時にGitHub commit SHAをWorkerへ渡します。

```text
--var BUILD_SHA:${{ github.sha }}
```

`GET /health` の `buildSha` と比較し、**期待したcommitが実際にproductionへ見えていること**を確認してから後続smokeへ進みます。

これにより、Cloudflare側の反映待ちや旧バージョンを誤ってgreen判定することを防ぎます。

## 公開API面

本番画面が利用するGoogle Routes処理の入口は、原則として統合APIに限定します。

公開:

- `GET /health`
- `POST /api/tonight-decision`
- `POST /api/last-train-boundary` — 路線別production smoke・詳細検証用

非公開:

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

WALK / DRIVE / taxi estimateの関数はWorker内部helperとしてのみ使用します。

`/api/tonight-decision` のタクシー目的地は、選択されたverified destination駅からWorker側で生成します。リクエストの `taxiDestination` による任意上書きは拒否します。

また、同一オリジンのWebアプリから利用する構成のため、Workerレスポンスに `Access-Control-Allow-Origin: *` は付与しません。

CORSはブラウザ制御でありAPI乱用そのものを止める仕組みではないため、Cloudflare Rate Limitingなどのインフラ防御とは役割を分けます。

## Core production smoke

deploy workflow内で次を確認します。

### 1. Worker health

- HTTP 200
- `ok: true`
- `service: ato-ippai-api-poc`
- `googleApiKeyConfigured: true`
- `buildSha == github.sha`

期待SHAがまだ見えていない場合は短時間リトライします。

### 2. Web MVP

公開トップページを取得して、代表テキストを確認します。

- `<title>あと一杯ナビ</title>`
- `現在地から判定する`

### 3. 非公開化した低レベルAPI

次のエンドポイントへPOSTし、すべてHTTP 404になることを確認します。

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

これにより、コード上でGoogle Routes helperが残っていても、外部から任意origin/destinationを与える公開プロキシとして露出していないことをデプロイごとに検証します。

### 4. Core last-train boundary

代表destinationとして H22 藤が丘を使い、`POST /api/last-train-boundary` を本番Workerへ送ります。

確認項目:

- `routeFound=true`
- `dataSource=internal_last_train_json`
- destination H22
- WALK候補が栄・伏見
- 今 / +15 / +30 / +60 の4シナリオ
- 現在シナリオは到達可能
- 最後のシナリオは到達不可

### 5. 統合APIの終電 + タクシー

`POST /api/tonight-decision` をH22藤が丘で実行します。

確認項目:

- destination H22 / 藤が丘
- `taxiDestination` がWorker側で `藤が丘駅 愛知県名古屋市` に固定される
- train判定が正常
- 終電後シナリオではタクシーフォールバックになる
- taxi routeが取得できる
- 距離・深夜割増・概算金額が妥当な正値
- `method=distance_only_approximation`

従来の `/api/taxi-estimate` 単独smokeは使用しません。

### 6. 任意タクシー目的地の拒否

同じ `/api/tonight-decision` に、例えば次を追加して送ります。

```json
{
  "taxiDestination": "東京駅"
}
```

期待結果:

- HTTP 400
- `taxiDestination override is not allowed`

これにより、統合API経由でもGoogle DRIVEを任意目的地へ使えないことを確認します。

## 路線別 production smoke

一部の路線・destinationは、Core smokeだけでは検証できない固有条件を持ちます。

そのため専用workflowを用意し、`Deploy Worker to Cloudflare` の成功を `workflow_run` で受けて本番APIを検証します。

例:

- JR各線
- 名鉄各線
- 乗換経路
- destination-specificなhub制約

2026-09-05時点では、KM12味鋺などについて専用production smokeが動作しています。

KM12では次を本番APIで確認します。

- destination `KM12` / 味鋺
- WALK候補は `sakae` のみ
- 栄 23:42発
- 平安通 23:54着
- 平安通 00:06発
- 味鋺 00:10着
- transfer metadata
- 20分後シナリオでは到達不可

現在の路線別smokeは `/api/last-train-boundary` を使用します。そのため、このエンドポイントは現時点では公開ルーティングを維持します。

将来、路線別smokeを `/api/tonight-decision` へ移行できれば、`/api/last-train-boundary` の外部公開をさらに縮小できるか再評価します。

## 公式ソース検証CIとの役割分担

production smokeは「デプロイされたアプリが期待どおり動くか」を確認します。

終電時刻そのものの正当性は、各事業者の公式ソースを再取得するverification CIで確認します。

```text
公式ソース
  -> generator / PoC parser
  -> generated boundary
  -> production JSONと比較
```

公式ページ構造や時刻が変わり、一意に検証できない場合はfail-closedでCIを失敗させます。

## GitHub Repository Secrets

GitHub側にはCloudflareデプロイに必要なSecretだけを登録します。

```text
CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_API_TOKEN
```

値はリポジトリへコミットしません。

Cloudflare API TokenはWorkerデプロイに必要な範囲だけに絞ります。

## Cloudflare Worker Secret

Google Routes APIキーはCloudflare Worker Secretとして維持します。

```text
GOOGLE_MAPS_API_KEY
```

Secret値は `wrangler.jsonc` に記載しません。
Workerコードは `env.GOOGLE_MAPS_API_KEY` から参照します。

旧Google TRANSIT PoC用の `MAX_LATE_TRANSIT_WAIT_MINUTES` は、TRANSIT処理削除後は不要なため `wrangler.jsonc` から除去します。

## Rate Limiting / Google API restriction

公開面をコードで縮小する対策と、インフラ側の流量制御は分けて管理します。

Phase 2候補:

- Cloudflare Workers Rate Limiting binding
- Google API keyをRoutes APIのみにAPI restriction
- credential別Metricsの確認
- quota / budget alertの検討

Cloudflare Rate Limiting bindingの `namespace_id` はアカウント内で一意に管理する必要があるため、既存設定を確認せずリポジトリ側で番号を決めません。

## Compatibility date

Cloudflareは `compatibility_date` に未来日を指定できません。

GitHub Actions runnerはUTCで実行されるため、日本時間では日付が変わっていてもUTCでは前日の場合があります。compatibility dateを変更する場合はこの差に注意します。

初期PoCでは、日本時間2026-09-02に `2026-09-02` を指定した時点でrunner側が2026-09-01 UTCだったため、future dateとして失敗しました。

## 本番完了判定

本番変更は、最低でも次を満たして完了とします。

- PRのrequired/関連CIがgreen
- 公式ソースverificationが必要な変更ではそのCIもgreen
- mainへmerge
- deploy workflow success
- 期待BUILD_SHAが `/health` で確認できる
- Core production smoke success
- 対象に専用smokeがある場合はそのproduction smoke success

API公開面を変更した場合は追加で:

- 非公開化したendpointが404
- 統合APIが正常
- 不正な任意destination上書きが拒否される

ことをCore production smokeで確認します。

## 運用原則

- GitHubをコード・設計・ワークフローの正本とする
- 本番変更は原則PRでレビューしてからmainへ反映する
- Cloudflare DashboardでWorkerコードを直接編集しない
- APIキー・Secret値をGitHubへコミットしない
- Google Routes helperを任意origin/destinationの公開プロキシにしない
- 時刻表変更はproduction JSONを直接推測更新せず、公式ソース検証を通す
- verification不能時はfail-closedとする
