# Google Routes API PoC

## 実施日

2026-09-02

## 目的

「あと一杯ナビ」に必要な、公共交通・自動車ルート取得が実用レベルで可能かを確認する。

## 確認済み

- Google Cloud Billing設定
- Routes API有効化
- APIキー作成
- APIキーをRoutes APIのみに制限
- Cloudflare Workers Secretへ `GOOGLE_MAPS_API_KEY` を登録
- WorkerからSecretを参照できることを確認
- WorkerからGoogle Routes APIへリクエストし HTTP 200 を確認

## 重要

HTTP 200は「通信経路が成立した」ことの確認であり、サービス成立性の確認ではない。

最初のTRANSIT試験では、HTTP 200に対しレスポンス本体が空のオブジェクトとなったため、公共交通ルート取得条件は未検証として扱う。

## 未確認

- 錦三丁目 → 藤が丘駅のTRANSITルート
- 錦三丁目 → 金山駅のTRANSITルート
- 深夜帯で今 / +15 / +30 / +60分の境界が取れるか
- 終電後に翌朝便が返った場合の判別
- transitFare
- DRIVE distanceMeters
- スマホGPSをoriginに使った場合のルート
- タクシー概算精度

## PoC合格条件

### 必須

- 23時台の通常TRANSITルートが返る
- 終電直前でもルートが返る
- 終電後とその夜のルートを区別できる
- 最初に乗る駅・発車時刻が取れる
- DRIVEの距離が取れる
- 最寄り駅モードで自宅情報なしでも成立する

### 任意

- transitFareが取得できる
- 最寄り乗車駅をRoutes API側で自然に選択できる

## 次の試験

GitHubをコードの正本にし、Cloudflare WorkerをGitHub経由でデプロイする。

テスト候補:

- 錦三丁目付近 → 藤が丘駅
- 錦三丁目付近 → 金山駅
- 22:30 / 23:30 / 23:45 / 00:00 / 00:15 JST
- TRANSITとDRIVEの両方を確認

## 判定

- 通信経路PoC: **OK**
- 公共交通成立性PoC: **継続**
- サービス成立性PoC: **未判定**
