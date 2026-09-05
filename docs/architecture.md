# アーキテクチャ概要

## 目的

「あと一杯ナビ」は、栄・伏見周辺で飲んでいる利用者が、**今帰るか、あと少し残るか**を短時間で判断するための意思決定支援Webアプリです。

汎用の乗換案内サービスは作りません。

必要なのは「今の場所から帰宅先最寄り駅へ、最後に間に合う境界」です。そのため、全時刻表や自前の経路探索エンジンではなく、公式ソースから検証した終電境界だけを保持します。

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
  └─ Cloudflare Worker
       ├─ Google Routes API / WALK
       │    └─ 現在地→destinationに必要な徒歩hub
       │
       ├─ 内部 終電境界JSON
       │    ├─ destination
       │    ├─ eligible hub
       │    ├─ weekday / saturday_holiday
       │    ├─ lastDeparture / lastArrival
       │    └─ 乗換metadata
       │
       ├─ 終電境界判定
       │    └─ 今 / +15 / +30 / +60
       │
       └─ Google Routes API / DRIVE
            └─ 終電後のタクシー概算
```

## 公共交通の基本方針

2026-09-02の成立性PoCでは、Google Routes APIのTRANSITは日本の試験ケースで安定して経路を返さなかったため、MVPの日本公共交通判定には使用しません。

代わりに、次を組み合わせます。

1. 現在地→出発hubはGoogle WALK
2. hub→目的駅は内部のverified終電境界JSON
3. 終電後はGoogle DRIVEによるタクシー概算

これにより、Google TRANSITの可用性に依存せず「あと何分残れるか」を判定します。

## 終電境界JSON

正本:

```text
src/data/last-trains-nagoya.json
```

詳細設計:

```text
docs/last-train-json.md
```

JSONは全時刻表を保存しません。目的駅ごとに、本番判定に必要な最後の到達可能経路だけを保持します。

代表フィールド:

- `lastDeparture`
- `lastArrival`
- `routeSummary`
- `trainTerminal`
- `transfers`
- `status`
- `sourceIds`

乗換経路では追加で次を保持します。

- `transferAt`
- `transferStationCodes`
- `transferReadyTime`
- `connectionDeparture`
- `connectionTerminal`
- `minimumTransferLeadMinutes`
- `transferMarginMinutes`

`status=verified` の経路だけを本番判定に使用します。

## hub設計

現在地から常に栄・伏見だけへ歩かせるのではなく、**選択したdestinationにverified routeがあるhubだけ**をGoogle WALKの候補にします。

これにより、路線に応じて次のような入口を利用できます。

- 栄 / 伏見
- 丸の内 / 久屋大通
- 栄町
- 名古屋
- 金山など、検証済み経路で必要なhub

目的駅自身が出発hubと同一の場合は、不要な電車の折返し経路を作らず徒歩帰宅として扱います。

## 直通と乗換

直通経路と乗換経路を同じ推測ロジックに押し込みません。

### 直通

例:

```text
名鉄名古屋 → 名古屋本線の目的駅
名古屋 → JR中央本線の目的駅
```

公式のdestination-specific結果や公式オープンデータで、目的駅へ本当に到達する列車を確認します。

### 乗換

例:

```text
栄 → 金山 → 名港線
名鉄名古屋 → 大江 → 東名古屋港
栄 → 平安通 → 味鋺
```

乗換地点、接続列車、最低乗換余裕をデータとして保持し、APIにも返します。

## 同一列車の照合

同じ行先名だけでは、近い時刻の別列車を誤って結合する可能性があります。

KM12味鋺のPoCでこの問題を検出したため、複数駅の時刻表を結合する場合は、所要時間など**同一列車であることを確認できる条件**を追加します。

例:

- 栄→平安通は公式時刻表上の所要12分一致を必須にする

## 対応範囲

MVPでは名古屋市内の登録最寄り駅を対象に、次をproduction化済みです。

### 市営地下鉄

- 東山線
- 鶴舞線
- 名城線
- 名港線
- 桜通線
- 上飯田線

### その他

- 名鉄瀬戸線
- 名鉄名古屋本線
- 名鉄常滑線
- 名鉄犬山線
- 名鉄築港線
- 名鉄小牧線
- あおなみ線
- 近鉄名古屋線
- JR関西本線
- JR中央本線
- JR東海道本線

MVP親Issue #42は2026-09-05に完了しています。

## 公式データとfail-closed

事業者ごとに取得方法は異なりますが、共通原則は次です。

- 名古屋市交通局は公式オープンデータを優先
- 他事業者も公式ページ・公式時刻表を優先
- 取得結果から生成した境界とproduction JSONをCIで比較
- 駅名、駅番号、時刻表構造、最終列車などを一意に検証できない場合はCIを失敗させる
- 推測値を `verified` として本番投入しない

## データベースと個人情報

MVPではデータベースを使用しません。

- 終電データ: Git管理の静的JSON
- ユーザー設定: 端末内localStorage
- 自宅住所・自宅座標・起床時刻をサーバーへ永続保存しない

標準の帰宅先は「自宅最寄り駅」です。

## APIキー

Google Routes APIキーはGitHubに保存しません。

Cloudflare Worker Secret:

```text
GOOGLE_MAPS_API_KEY
```

から参照します。

## 主要API

### `POST /api/last-train-boundary`

- destinationから利用可能hubを決定
- Google WALKで現在地→hubの所要時間を取得
- 内部JSONで今 / +15 / +30 / +60分の到達可否を判定
- 直通・乗換metadataを返す

### `POST /api/taxi-estimate`

- Google DRIVEを利用
- 終電後のタクシー概算を返す

### `GET /health`

- Workerの稼働状態を確認する

## 運用上の正本

- コード・設計・ワークフロー: GitHub
- 終電境界: `src/data/last-trains-nagoya.json`
- Cloudflare Dashboard: Secret・実行環境の管理

WorkerコードをCloudflare Dashboardで直接編集せず、変更はGitHub PR経由で反映します。
