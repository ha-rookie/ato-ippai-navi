# 名鉄名古屋本線の終電境界設計

## 対象

あと一杯ナビでは、名鉄名古屋本線のうち名古屋市内にある NH24〜NH38 を対象にする。

- NH24 中京競馬場前
- NH25 有松
- NH26 左京山
- NH27 鳴海
- NH28 本星崎
- NH29 本笠寺
- NH30 桜
- NH31 呼続
- NH32 堀田
- NH33 神宮前
- NH34 金山
- NH35 山王
- NH36 名鉄名古屋
- NH37 栄生
- NH38 東枇杷島

NH36 名鉄名古屋は `nagoya` 徒歩ハブに含め、目的駅として選ばれた場合は walk-home として扱う。

## なぜ「名鉄名古屋の最終列車」だけでは判定しないのか

名鉄名古屋本線は列車種別・行先・停車駅が複数あるため、名鉄名古屋を最後に発車する列車がすべての目的駅へ行くとは限らない。

実際に検証した終電境界には次の差がある。

| 目的駅 | 名鉄名古屋発 | 到着 | 種別 | 行先 |
| --- | ---: | ---: | --- | --- |
| NH26 左京山 | 23:21 | 23:50 | 普通 | 新安城 |
| NH27 鳴海 | 00:01 | 00:21 | 普通 | 鳴海 |
| NH34 金山 | 00:06 | 00:10 | 急行 | 金山 |
| NH38 東枇杷島 | 23:50 | 23:54 | 普通 | 須ケ口 |

したがって、アプリ側で「最終列車の時刻」や「種別の停車駅」を推測せず、**目的駅ごとの公式『乗換なし時刻表』で最後に到達できる列車**を終電境界の source of truth とする。

## 公式ソース

名古屋鉄道の公式「ダイヤ・運賃検索 / 乗換なし時刻表」の `DepArrTimeList` を利用する。

production source ID:

`meitetsu-main-official-direct-timetable`

GitHub Actions からは通常ブラウザ相当の User-Agent / Accept / Referer と Cookie セッションを使って取得する。単純な curl では 403 になる場合があるため、この取得条件も検証処理の一部とする。

## GitHub Actionsでの検証

`.github/workflows/poc-meitetsu-main-nagoya.yml` はPoC完了後、production verifierとして使う。

1. 直近の平日と土曜を代表サービス日として解決する
2. NH24〜NH38について公式の目的駅別直通時刻表を再取得する
3. `<ul class="time-detail">` ごとに発時刻・着時刻・種別・行先を抽出する
4. 最終直通列車を目的駅別の終電境界として生成する
5. `src/data/last-trains-nagoya.json` と完全一致することを検証する

公式ページを取得できない、HTML構造を解析できない、目的駅が一致しない、保存済みproduction境界と差が出る、といった場合は fail-closed でCIを失敗させる。差分を自動でproductionへ反映はしない。

なお、NH36の通常駅時刻表 `TrainDiagram` はGitHub-hosted runner上では路線選択画面までしか返らないことがある。そのためこれはsecondary diagnosticに限定し、production境界の主ソースにはしない。

## runtime設計

runtimeには全時刻表を保持しない。

`src/data/last-trains-nagoya.json` に保持するのは、目的駅・平日/土休日ごとの最終直通境界だけとする。

各routeには次を保持する。

- `lastDeparture`
- `lastArrival`
- `routeSummary`
- `trainClass`
- `trainTerminal`
- `transfers: 0`
- `status: verified`
- `sourceIds`

`lastArrival` は公式時刻表から実際に取得できた値のみを保存し、推測値は入れない。

## WALKとGoogle Routes API

NH24〜NH35、NH37、NH38の `eligibleOriginIds` は `nagoya` のみ。

現在地から名古屋駅エリアへのGoogle WALKを1回だけ取得し、その徒歩時間と内部終電境界を比較する。名鉄名古屋専用に別のGoogle WALKを増やさず、既存の `nagoya` ハブを共有する。

これにより、名鉄追加によるGoogle Routes API呼び出し数の増加を最小化する。

## 関連Issue / PR

- #103 名鉄系統の全体設計
- #104 名鉄名古屋本線PoC
- #105 PoC実装
- #106 production化
