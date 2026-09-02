# Google Routes API PoC

## 実施日

2026-09-02

## 目的

「あと一杯ナビ」の公共交通判定を、Google Routes APIだけで成立させられるか確認する。

## 結論

**2026-09-02時点の実測では、日本の公共交通判定をGoogle Routes APIのTRANSITだけで実装する案はNo-Goとする。**

Google Routes APIへの通信やリクエスト構造が壊れているわけではない。
同一Worker・同一APIキー・同一実装で、海外の対照ケースは正常に公共交通ルートを返した。

一方、日本の11ケースはすべて HTTP 200 だが `routes: []` 相当で、公共交通ルートは0件だった。

この結果は「Googleが日本のTRANSITを公式に非対応と明記している」という意味ではない。
公式仕様はTRANSITを「利用可能な地域」で提供するとしているが、Routes APIの公開カバレッジ表から日本のTRANSIT可否を直接確認できなかったため、ここでは**本プロジェクト環境での制御試験結果**として扱う。

## 検証結果

### 日本

以下11ケースはすべて `HTTP 200 / routeFound=false / rawRouteCount=0`。

- 名古屋 栄→藤が丘：現在時刻・座標
- 名古屋 栄→藤が丘：15:00 JST明示・座標
- 名古屋 栄→藤が丘：駅名住所
- 名古屋 栄→藤が丘：regionCode省略
- 名古屋 栄→藤が丘：alternative routes有効
- 名古屋 栄→藤が丘：SUBWAY preference
- 名古屋 栄→藤が丘：RAIL preference
- 名古屋 栄→藤が丘：LESS_WALKING
- 名古屋 栄→金山
- 名古屋 伏見→名古屋
- 東京 東京駅→新宿駅

### 海外対照

- New York: Times Square → Grand Central
  - `routeFound=true`
  - 42 St Shuttleを取得
  - Transit fare USD 3も取得
- Lisbon: Google公式サンプル相当
  - `routeFound=true`
  - 6 routes取得
  - 複数のTRANSIT stepを取得

### 自動判定

```json
{
  "japanCaseCount": 11,
  "japanSuccessCount": 0,
  "controlCaseCount": 2,
  "controlSuccessCount": 2,
  "googleOnlyTransitCandidate": false
}
```

GitHub Actions:

```text
PoC Google Routes Japan Transit
run #6
run_id: 33595421765
result: success
```

PoC結果JSONはGitHub Actions Artifact `google-routes-japan-transit` として保存した。

## 確認済みのGoogle Routes機能

- Worker → Google Routes API通信
- WALK
- DRIVE
- TRANSITリクエスト自体
- departureTime省略（Google既定のnow）
- departureTime明示
- computeAlternativeRoutes
- transitPreferences.allowedTravelModes
- transitPreferences.routingPreference
- regionCode有無
- 座標 / 住所指定

## プロジェクトへの影響

### Google Routes APIだけに限定する場合

現状では、公共交通を使った「今 / +15 / +30 / +60分後に帰れるか」を日本で信頼して判定できない。

そのため、Google Routes APIだけに限定するなら、現在の「あと一杯ナビ」の公共交通要件は満たせない。

### 既存PoCについて

名古屋市交通局公式時刻表を使った栄→藤が丘判定は別方式として成立済みだが、栄・伏見周辺の複数路線・複数事業者へ拡張すると自前の乗換案内実装に近づく。

したがって、次の設計判断はコード追加より先に行う。

1. Google Routes APIだけ、という制約を優先して公共交通機能を縮小する
2. 公共交通判定のため別データ/APIを許可する
3. プロダクト要件自体を見直す

## 判定

- Google Routes API 通信PoC: **OK**
- WALK: **OK**
- DRIVE: **OK**
- 海外TRANSIT: **OK**
- 日本TRANSIT: **本プロジェクトの制御試験では0/11**
- Google Routes APIだけで日本の公共交通判定: **No-Go**
