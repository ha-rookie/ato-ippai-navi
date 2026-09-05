# あと一杯ナビ

名古屋・錦三丁目／栄で飲んでいるときに、**今帰るか、あと少し残るか**を判断するためのWebアプリです。

単なる乗換検索ではなく、現在地から帰宅先までの「最後に間に合う境界」を使って、今帰る場合と少し残る場合を比較します。

## 現在の状態

**終電JSON基盤のMVPは完了し、Cloudflare Workerへproduction deploy済みです。**

2026-09-05時点で確認済み:

- ブラウザGPSから現在地を取得
- Google Routes API / WALKで、目的駅に必要な出発hubまでの徒歩時間を取得
- 日本の公共交通TRANSITには依存せず、内部のverified終電境界JSONで判定
- 今 / +15 / +30 / +60分の到達可否を比較
- 直通経路と1回乗換経路に対応
- 終電後はGoogle Routes API / DRIVEを使ったタクシー概算へ接続
- 帰宅先最寄り駅をlocalStorageへ保存・復元
- 出発hub自身が帰宅先の場合は徒歩帰宅として判定
- GitHub Actions + WranglerでCloudflare Workerへデプロイ
- 公式ソースとのgenerated-vs-production CI
- Core production smoke / 路線別production smoke
- Google Routes APIキーをCloudflare Worker Secretで保持
- 本番画面からのGoogle Routes利用は統合API経由に限定し、任意WALK/DRIVEプロキシを公開しない

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

対象はMVPとして定義した**名古屋市内の登録最寄り駅**です。市外への拡張は別スコープで扱います。

## アーキテクチャ方針

- DBなし
- ログインなし
- 現在地はブラウザGeolocation API
- 個人設定は端末内localStorage
- 終電境界の正本は `src/data/last-trains-nagoya.json`
- APIキーはCloudflare Worker Secretで管理
- GitHubをコード・設計・CI/CDの正本とする
- 全時刻表や自前の汎用乗換検索エンジンは持たない
- 公式ソースで検証できた「最後に到達できる経路」だけを本番判定に使う
- Google RoutesのWALK/DRIVE helperはWorker内部実装とし、任意origin/destinationを受ける公開APIにはしない
- タクシー目的地はverified destination駅からサーバ側で生成し、クライアントによる任意上書きを許可しない

## 主要API

- `POST /api/tonight-decision`
  - 本番画面が利用する統合API
  - 現在地→必要hubのWALK、内部終電境界、終電後のタクシー概算をまとめて返す
  - タクシー目的地は選択済みのverified destination駅からWorker側で決定する
- `POST /api/last-train-boundary`
  - 終電境界の詳細検証・路線別production smokeで使用する
  - 本番画面は直接利用しない
- `GET /health`
  - Workerの稼働状態とbuild SHAを確認する

次の低レベルAPIは外部公開しません。

- `/api/walk`
- `/api/drive`
- `/api/taxi-estimate`

## デプロイ

`main` への本番変更はGitHub ActionsからWranglerでCloudflare Workerへ反映します。

Production Worker:

```text
ato-ippai-api-poc.edward-se-pg.workers.dev
```

デプロイ後はCore production smokeに加え、必要な路線別smokeを自動実行します。Core smokeでは、非公開化した低レベルAPIが404であることも確認します。

## ドキュメント

- `docs/architecture.md` — 現行アーキテクチャ
- `docs/deployment.md` — CI/CD・Cloudflareデプロイ
- `docs/last-train-json.md` — 終電境界JSONの設計
- `docs/jr-kansai.md` / `docs/jr-chuo.md` / `docs/jr-tokaido.md`
- `docs/meitetsu-main.md` / `docs/meitetsu-inuyama.md`
- `docs/poc/` — PoC・検証記録

## 開発運用

- 本番変更は原則PR経由
- 未検証の終電データは本番判定に使わない
- 公式ページやデータ構造が変わり、検証できなくなった場合はfail-closedでCIを失敗させる
- Cloudflare DashboardでWorkerコードを直接編集しない
- APIキーやSecret値をリポジトリへコミットしない
- Google Routes APIの公開面は最小化し、Worker経由の任意プロキシを作らない
