# アーキテクチャ概要

## 目的

「あと一杯ナビ」は、栄・伏見周辺で飲んでいる利用者が、**今帰るか、あと少し残るか**を短時間で判断するための意思決定支援Webアプリです。

汎用の乗換案内サービスは作りません。必要なのは「今の場所から帰宅先最寄り駅へ、最後に間に合う境界」です。

## 公開URL

利用者向けの正式URLはCloudflare Pagesに統一します。

- Top: `https://ato-ippai.pages.dev`
- 今日の終電: `https://ato-ippai.pages.dev/last-train`

独自ドメインは使用しません。`workers.dev` は内部API originとしてのみ扱います。

## 現行構成

```text
スマホブラウザ
  ├─ Geolocation API
  ├─ localStorage
  │   ├─ 帰宅先の最寄り駅
  │   ├─ 最寄り駅→自宅の所要分
  │   ├─ 就寝準備時間
  │   └─ 起床時刻
  │
  └─ Cloudflare Pages
       ├─ public/ 静的画面
       │    ├─ /
       │    └─ /last-train
       │
       └─ Pages Functions
            ├─ /api/*
            ├─ /ops/*
            └─ /health
                 |
                 v
            Cloudflare API Worker
                 ├─ Google Routes API / WALK helper
                 ├─ verified終電境界JSON
                 ├─ 終電境界判定
                 ├─ Google Routes API / DRIVE helper
                 └─ タクシー概算
```

### Pagesの責務

- 利用者向け正式URLを提供する
- `public/` を配信する
- `/last-train` をSPAとして配信する
- `/api/*`, `/ops/*`, `/health` をPages FunctionsからAPI Workerへ中継する
- ブラウザから見たAPIを同一オリジンに保つ

### API Workerの責務

- Google Routes APIキーをSecretとして保持する
- WALK / DRIVEを内部helperとして実行する
- production終電JSONを読み込む
- 終電境界、タクシー概算、統合判定を返す
- read-onlyの運用CSVを生成する

Pages移行時点ではGoogle APIキーをPagesへ複製しません。既存WorkerをAPI専用バックエンドとして維持することで、URL整理とSecret移行を分離します。

## 公共交通の基本方針

Google Routes APIのTRANSITはMVPの日本公共交通判定には使用しません。

1. 現在地→出発hubはAPI Worker内部のGoogle WALK
2. hub→目的駅は内部のverified終電境界JSON
3. 終電後はAPI Worker内部のGoogle DRIVEによるタクシー概算

これにより、Google TRANSITの可用性に依存せず「あと何分残れるか」を判定します。

## 終電境界JSON

正本:

```text
src/data/last-trains-nagoya.json
```

JSONは全時刻表を保存せず、本番判定に必要な最後の到達可能経路だけを保持します。

代表フィールド:

- `lastDeparture`
- `lastArrival`
- `routeSummary`
- `trainTerminal`
- `transfers`
- `status`
- `sourceIds`

`status=verified` の経路だけを本番判定に使用します。

## hub設計

現在地から常に栄・伏見だけへ歩かせるのではなく、**選択destinationにverified routeがあるhubだけ**をGoogle WALKの候補にします。

代表例:

- 栄 / 伏見
- 丸の内 / 久屋大通
- 栄町
- 名古屋
- 金山

目的駅自身が出発hubと同一の場合は、不要な電車経路を作らず徒歩帰宅として扱います。

## 直通と乗換

直通経路と乗換経路を同じ推測ロジックに押し込みません。

乗換経路では次をmetadataとして保持します。

- `transferAt`
- `transferStationCodes`
- `transferReadyTime`
- `connectionDeparture`
- `connectionTerminal`
- `minimumTransferLeadMinutes`
- `transferMarginMinutes`

複数駅の公式時刻表を結合する場合は、行先名だけでなく所要時間などを使い、同一列車であることを検証します。

## データベースと個人情報

MVPではデータベースを使用しません。

- 終電データ: Git管理の静的JSON
- ユーザー設定: 端末内localStorage
- 自宅住所・自宅座標・起床時刻をサーバーへ永続保存しない

## Google Routes APIキーと公開面

Google Routes APIキーはGitHubやブラウザへ保存・公開しません。

API Worker Secret:

```text
GOOGLE_MAPS_API_KEY
```

公開面は次に限定します。

- `POST /api/tonight-decision`
- `POST /api/last-train-boundary`
- `GET /ops/last-train-boundaries.csv`
- `GET /health`

Pages Functionsは上記パスをAPI Workerへ中継します。

次は公開しません。

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

また、タクシー目的地はverified destination駅からサーバー側で生成し、クライアントからの任意上書きを拒否します。

## Cloudflare設定の正本

### Pages

```text
wrangler.jsonc
```

- name: `ato-ippai`
- output: `./public`
- production: `https://ato-ippai.pages.dev`

### API Worker

```text
wrangler.worker.jsonc
```

- name: `ato-ippai-api-poc`
- entry: `src/index.js`
- Google API key: Cloudflare Worker Secret

Worker側ではStatic Assetsを配信しません。UI配信責務はPagesへ移します。

## 運用上の正本

- コード・設計・ワークフロー: GitHub
- 終電境界: `src/data/last-trains-nagoya.json`
- 利用者向け公開URL: `https://ato-ippai.pages.dev`
- Secret・実行環境: Cloudflare

Cloudflare Dashboardでコードを直接編集せず、変更はGitHub PR経由で反映します。
