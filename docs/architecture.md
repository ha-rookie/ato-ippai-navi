# アーキテクチャ概要

## 目的

「あと一杯ナビ」は、錦三丁目／栄で飲んでいる利用者が、今帰るか、あと少し残るかを短時間で判断するための意思決定支援Webアプリとする。

## MVP構成

```text
スマホブラウザ / PWA
  ├─ Geolocation API
  ├─ localStorage（将来）
  │   ├─ 帰宅先の最寄り駅
  │   ├─ 任意の帰宅地点
  │   ├─ 追加注文額
  │   ├─ 追加滞在時間
  │   └─ 起床時刻
  │
  └─ Cloudflare Worker
       ├─ Google Routes API / TRANSIT
       ├─ Google Routes API / DRIVE
       ├─ 終電境界判定
       ├─ タクシー概算（将来）
       └─ 睡眠時間計算（将来）
```

## データベース

MVPでは使用しない。

ユーザー設定は端末内の localStorage に保存する想定。サーバー側へ自宅住所・自宅座標を永続保存しない。

## 帰宅先モード

### 標準: 最寄り駅モード

- 自宅住所不要
- 自宅座標不要
- 公共交通は登録駅まで
- タクシー概算も登録駅まで
- プライバシー優先

### 任意: 帰宅地点モード

- より正確なタクシー距離・帰宅時間を計算
- 将来、端末内だけに座標を保存
- サーバー側で永続保存しない

## APIキー

Google Routes APIキーはGitHubに保存しない。

Cloudflare WorkerのSecret:

```text
GOOGLE_MAPS_API_KEY
```

からのみ参照する。

## 現在のPoC

UIはまだ作らない。まず以下だけ検証する。

1. TRANSITルート取得
2. 深夜帯の境界判定
3. DRIVE距離取得
4. transitFare取得可否
5. 実GPS座標でのルーティング
