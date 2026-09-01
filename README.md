# あと一杯ナビ

名古屋・錦三丁目／栄で飲んでいるときに、**今帰るか、あと少し残るか**を判断するためのWebアプリです。

## コンセプト

単なる終電検索ではなく、次を1画面で比較します。

- 今帰れば公共交通で帰れるか
- 15分 / 30分 / 60分後でも帰れるか
- 終電を逃した場合のタクシー概算
- 追加滞在による実質コスト
- 将来は「今日あと何時間寝られるか」も表示

## MVP方針

- 対象地域: 名古屋・錦三丁目／栄
- DBなし
- ログインなし
- 現在地はブラウザGPSで取得
- 帰宅先は「最寄り駅のみ」を標準モード
- 自宅座標を登録する精密モードは任意
- 個人設定は将来 localStorage に保存
- APIキーはCloudflare WorkersのSecretで管理

## 現在のフェーズ

**Google Routes API の成立性PoC**

確認済み:

- Google Cloud Billing設定
- Routes API有効化
- APIキーをRoutes APIのみに制限
- Cloudflare WorkerのSecretへAPIキー格納
- Cloudflare Worker → Google Routes APIでHTTP 200を確認
- GitHubをコード・設計の正本として初期化
- GitHub Actions + Wranglerによるデプロイ構成を設計

未確認:

- GitHub Actionsから既存Workerへの初回デプロイ
- 錦三丁目 → 藤が丘駅のTRANSITルート取得
- 深夜帯の終電境界判定
- transitFare取得可否
- DRIVE距離
- 実GPS
- タクシー概算精度

## ドキュメント

- `docs/architecture.md`
- `docs/deployment.md`
- `docs/poc/google-routes-api.md`
- `docs/poc/test-cases.md`
