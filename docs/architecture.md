# アーキテクチャ概要

## 目的

「あと一杯ナビ」は、栄・伏見周辺で飲んでいる利用者が、今帰るか、あと少し残るかを短時間で判断するための意思決定支援Webアプリとする。

乗換案内サービスそのものは作らない。

## MVP構成

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
       │    ├─ 現在地→栄
       │    └─ 現在地→伏見
       │
       ├─ 内部 深夜帰宅JSON
       │    └─ 栄/伏見→目的駅の最終到達可能経路
       │
       ├─ 終電境界判定
       │    └─ 今 / +15 / +30 / +60
       │
       └─ Google Routes API / DRIVE
            └─ 終電後のタクシー概算
```

## 公共交通の方針

Google Routes APIのTRANSITは、2026-09-02の制御試験で日本11ケース中0件、海外対照2ケース中2件の取得となった。

そのためMVPでは日本の公共交通判定にGoogle TRANSITを使わない。

代わりに、全時刻表や自前乗換検索を持たず、栄・伏見から名古屋市内の目的駅へ**最後に到達できる経路だけ**をJSONで保持する。

正本:

```text
src/data/last-trains-nagoya.json
```

詳細:

```text
docs/last-train-json.md
```

## 現在のJSON実証範囲

目的駅:

- 藤が丘 H22

出発拠点:

- 栄 H10
- 伏見 H09

名古屋市交通局公式オープンデータで確認した最終藤が丘行:

- 栄: 平日/土休日 00:02
- 伏見: 平日/土休日 00:00
- 藤が丘着: 00:23

今後 #42 で名古屋市内の目的駅へ拡張する。

## データベース

MVPでは使用しない。

終電データはGit管理の静的JSON。
ユーザー設定は端末内localStorage。

サーバー側へ自宅住所・自宅座標・起床時刻を永続保存しない。

## 帰宅先

標準は「自宅最寄り駅」。

- 公共交通判定は最寄り駅まで
- タクシー概算も最寄り駅まで
- 自宅住所不要

## APIキー

Google Routes APIキーはGitHubに保存しない。

Cloudflare Worker Secret:

```text
GOOGLE_MAPS_API_KEY
```

からのみ参照する。

## 主要API

- `POST /api/last-train-boundary`
  - Google WALKで栄/伏見へのアクセス時間を取得
  - 内部JSONで最終到達可否を判定
- `POST /api/taxi-estimate`
  - Google DRIVE + 名古屋タクシー概算
- 既存PoC API
  - 段階的に新しい終電JSON方式へ置き換える
