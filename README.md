# あと一杯ナビ

名古屋・錦三丁目／栄で飲んでいるときに、**今帰るか、あと少し残るか**を判断するためのWebアプリです。

単なる乗換検索ではなく、現在地から帰宅先までの「最後に間に合う境界」を使って、今帰る場合と少し残る場合を比較します。

## Production

利用者向けの正式URLはCloudflare Pagesに統一します。

- Top: `https://ato-ippai.pages.dev`
- 今日の終電: `https://ato-ippai.pages.dev/last-train`

独自ドメインは使用しません。朝マズメ潮ナビと同じ `*.pages.dev` 公開ルールです。

裏側のAPI WorkerはGoogle Routes APIキーを保持するため当面維持しますが、`workers.dev` URLは利用者向けの正式URLとして扱いません。

## 現在の状態

2026-09-05時点で確認済み:

- ブラウザGPSから現在地を取得
- Google Routes API / WALKで、目的駅に必要な出発hubまでの徒歩時間を取得
- 日本の公共交通TRANSITには依存せず、内部のverified終電境界JSONで判定
- 今 / +15 / +30 / +60分の到達可否を比較
- 直通経路と1回乗換経路に対応
- 終電後はGoogle Routes API / DRIVEを使ったタクシー概算へ接続
- 帰宅先最寄り駅をlocalStorageへ保存・復元
- 出発hub自身が帰宅先の場合は徒歩帰宅として判定
- Cloudflare Pagesを利用者向け公開入口とする
- Pages Functionsから既存API Workerへ `/api/*`, `/ops/*`, `/health` を同一オリジン中継する
- Google Routes APIキーはAPI Worker Secretで保持し、GitHub/ブラウザ/Pagesへ保存しない
- GitHub Actions + WranglerでPagesとWorkerを分離デプロイ
- 公式ソースとのgenerated-vs-production CI
- Core API production smoke / 路線別production smoke / Pages production smoke

## 対応範囲

### 名古屋市営地下鉄

- 東山線 H01〜H22
- 鶴舞線 T01〜T20
- 名城線 M01〜M28
- 名港線 E01〜E07
- 桜通線 S01〜S21
- 上飯田線 K01

### その他

- 名鉄瀬戸線 ST01〜ST12
- 名鉄名古屋本線 NH24〜NH38
- 名鉄常滑線 TA01〜TA05
- 名鉄犬山線 IY02〜IY03
- 名鉄築港線 CH01
- 名鉄小牧線 KM12
- あおなみ線 AN01〜AN11
- 近鉄名古屋線 KT-E01〜KT-E07
- JR関西本線 JR-CJ00〜JR-CJ02
- JR中央本線 JR-CF01〜JR-CF06
- JR東海道本線 JR-CA62〜JR-CA68

対象はMVPとして定義した**名古屋市内の登録最寄り駅**です。

## アーキテクチャ

```text
Browser
  |
  v
https://ato-ippai.pages.dev
  |-- static assets: public/
  |-- Pages Functions
        |
        | /api/* /ops/* /health
        v
Cloudflare API Worker
  |
  |-- Google Routes API / WALK + DRIVE
  |-- verified last-train JSON
  `-- taxi estimate
```

主な原則:

- DBなし
- ログインなし
- 現在地はブラウザGeolocation API
- 個人設定は端末内localStorage
- 終電境界の正本は `src/data/last-trains-nagoya.json`
- GitHubをコード・設計・CI/CDの正本とする
- 全時刻表や自前の汎用乗換検索エンジンは持たない
- Google Routesの任意WALK/DRIVEプロキシを公開しない
- タクシー目的地はverified destination駅からAPI Worker側で生成する

## 主要API

利用者からはPagesの同一オリジンでアクセスします。

- `POST /api/tonight-decision`
  - 終電境界、徒歩hub、タクシー概算をまとめて返す
- `POST /api/last-train-boundary`
  - 今日の終電画面と路線別production smokeで利用
- `GET /ops/last-train-boundaries.csv`
  - production終電境界のread-only運用出力
- `GET /health`
  - API Workerの稼働状態を確認

外部公開しない低レベルAPI:

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

## デプロイ

### Pages

- config: `wrangler.jsonc`
- project: `ato-ippai`
- workflow: `.github/workflows/deploy-pages.yml`
- production: `https://ato-ippai.pages.dev`

### API Worker

- config: `wrangler.worker.jsonc`
- Worker: `ato-ippai-api-poc`
- entry: `src/index.js`
- workflow: `.github/workflows/deploy-worker.yml`

Pages変更とAPI変更は別々にデプロイします。

## ドキュメント

- `docs/architecture.md` — 現行アーキテクチャ
- `docs/deployment.md` — Pages / API WorkerのCI/CD
- `docs/last-train-json.md` — 終電境界JSONの設計
- `docs/jr-kansai.md` / `docs/jr-chuo.md` / `docs/jr-tokaido.md`
- `docs/meitetsu-main.md` / `docs/meitetsu-inuyama.md`
- `docs/poc/` — PoC・検証記録

## 開発運用

- 本番変更は原則PR経由
- 未検証の終電データは本番判定に使わない
- verification不能時はfail-closed
- Cloudflare Dashboardでコードを直接編集しない
- APIキーやSecret値をリポジトリへコミットしない
- `workers.dev` は内部API originであり、利用者向け公開URLは `ato-ippai.pages.dev` とする
