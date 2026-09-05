# 深夜帰宅JSON設計

## 目的

「あと一杯ナビ」は汎用の乗換案内サービスを作らない。

現在地から名古屋市内の登録最寄り駅へ、**最後に到達できる経路の境界だけ**を保持し、

- 今
- +15分
- +30分
- +60分

でまだ公共交通で帰れるかを判定する。

全時刻表や自前の経路探索エンジンをランタイムへ持たないことを、MVPの基本方針とする。

## 正本

本番終電データの正本は次のJSON。

```text
src/data/last-trains-nagoya.json
```

`status=verified` の経路だけを本番判定に使用する。

GitHub上のgenerator / parser / verification workflowは、公式ソースから境界を再生成・再検証するための仕組みであり、ランタイムでは全時刻表を解析しない。

## データ責務

### Google Routes API

- ブラウザGPSで取得した現在地から、必要な徒歩hubまでのWALK
- 終電後のDRIVE
- タクシー概算

### 内部JSON

- 目的駅
- 利用可能な出発hub
- 平日 / 土休日
- 最終出発時刻
- 確認できる場合の最終到着時刻
- 経路サマリ
- 列車行先
- 乗換回数
- 乗換metadata
- 出典
- 検証状態

## 本番徒歩hub

production JSONの `origins` と一致させる。

| origin id | 表示名 | 主なstationCodes | 用途 |
| --- | --- | --- | --- |
| `sakae` | 栄 | H10 / M05 | 東山・名城・名港・上飯田・KM12など |
| `fushimi` | 伏見 | H09 / T07 | 東山・鶴舞など |
| `marunouchi` | 丸の内 | T06 / S04 | 桜通線 |
| `hisayaodori` | 久屋大通 | M06 / S05 | 桜通線 |
| `sakaemachi` | 栄町 | ST01 | 名鉄瀬戸線 |
| `nagoya` | 名古屋 | H08 / S02 / AN01 / KT-E01 / JR-CJ00 / JR-CF01 / JR-CA68 / NH36 | あおなみ・近鉄・JR・名鉄本線系など |

毎回すべてのhubへWALKを実行しない。

選択されたdestinationに `status=verified` の経路が存在するhubだけをGoogle WALKの対象にする。

これにより、hub追加によるAPI呼出数・レイテンシ増加を抑える。

## destinationの基本構造

概念例:

```json
{
  "KM12": {
    "operator": "meitetsu",
    "line": "komaki",
    "officialStationCode": "KM12",
    "name": "味鋺",
    "city": "名古屋市",
    "stationCodes": ["KM12"],
    "enabled": true,
    "routes": {
      "sakae": {
        "weekday": {},
        "saturday_holiday": {}
      }
    }
  }
}
```

routeは原則として次を持つ。

- `lastDeparture`
- `lastArrival`
- `routeSummary`
- `trainTerminal`
- `transfers`
- `status`
- `sourceIds`

乗換経路では必要に応じて次を追加する。

- `transferAt`
- `transferStationCodes`
- `transferReadyTime`
- `connectionDeparture`
- `connectionTerminal`
- `minimumTransferLeadMinutes`
- `transferMarginMinutes`

## `lastArrival` の扱い

`lastArrival` は**最終列車の到着時刻**であり、「今店を出た場合に乗る次列車の到着予測」ではない。

公式ソースから正確な到着時刻を確認できない場合は推測せず `null` とする。

特にJR3線では、公式ソースから目的駅ごとの正確な最終到着時刻を今回の方式で検証できない範囲があるため、`lastArrival=null` を許容している。

したがって:

- 終電に間に合うか: 判定する
- 検証済み最終到着時刻: あれば表示可能
- 今出た場合の実到着時刻: 終電JSONだけでは算出しない
- 電車利用時の睡眠時間: 詳細ダイヤを持たないMVPでは推測しない
- タクシー利用時のETA: Google DRIVEから算出可能

## 判定の基本

1. destinationにverified routeがあるhubを抽出
2. 現在地→各hubのGoogle WALKを取得
3. 出発時刻 + WALK + 駅構内バッファをready timeとする
4. 必要な乗車安全マージンを加味する
5. routeの `lastDeparture` と比較
6. 複数hubが使える場合は、到達可能で余裕が大きい経路を推奨
7. 公共交通で到達不能ならタクシーへフォールバック

目的駅自身がhubと同一物理駅の場合は、不要な折返し電車を作らず徒歩帰宅モードを使用する。

## 対応路線

2026-09-05時点のproduction JSONは次を保持する。

### 名古屋市営地下鉄

- 東山線 H01〜H22
- 鶴舞線 T01〜T20
- 名城線 M01〜M28
- 名港線 E01〜E07
- 桜通線 S01〜S21
- 上飯田線 K01
  - K02平安通はM11と同一物理駅のため、帰宅先UIでは既存M11を利用

### 名古屋鉄道

- 瀬戸線 ST01〜ST12
- 名古屋本線 NH24〜NH38
- 常滑線 TA01〜TA05
- 犬山線 IY02〜IY03
- 築港線 CH01
- 小牧線 KM12

### その他

- あおなみ線 AN01〜AN11
- 近鉄名古屋線 KT-E01〜KT-E07
- JR関西本線 JR-CJ00〜JR-CJ02
- JR中央本線 JR-CF01〜JR-CF06
- JR東海道本線 JR-CA62〜JR-CA68

MVPの対象は、Issue #42で定義した名古屋市内の登録最寄り駅。市外拡張は別スコープとする。

---

## 東山線

東山線 H01〜H22 は栄 H10 / 伏見 H09 を徒歩hubとして利用する。

藤が丘 H22での初期実証値:

| 出発 | 平日 | 土休日 | 藤が丘着 |
| --- | --- | --- | --- |
| 栄 H10 | 00:02 | 00:02 | 00:23 |
| 伏見 H09 | 00:00 | 00:00 | 00:23 |

名古屋市交通局公式オープンデータをgeneratorで解析し、目的駅ごとの最後に到達可能な列車をproduction JSONへ保持する。

## 名城線

名城線は環状線のため、駅番号の大小ではなく方向別の円環距離で到達可能性を判定する。

- 右回り: 栄 M05 → 久屋大通 → 大曽根方面
- 左回り: 栄 M05 → 矢場町 → 金山 → 新瑞橋方面
- 無印の環状運転列車: 1周内の各駅へ到達可能
- 行先マーカー付き列車: その方向の終着駅まで到達可能
- 名古屋港行: 名城線上では金山 M01まで到達し、その後名港線へ分岐

公式XLSXはCI/生成時だけ解析する。

## 名港線の金山乗換

名港線 E01〜E07 は、栄 M05 から金山 M01/E01 を経由する。

- E01 金山: 名城線左回りで到達
- E02〜E07: 金山で名港線へ1回乗換
- 栄と金山の公式駅別時刻表を生成時に突合
- 金山 M01 / E01の時刻表が矛盾した場合はfail-closed
- 同時刻接続は不可とし、最低1分の乗換余裕を要求

2025-09-29改正データの代表境界:

| 目的 | 栄発 | 金山着 | 名港線発 | 乗換 |
| --- | --- | --- | --- | --- |
| E01 金山 | 00:10 | 00:18 | - | 0 |
| E02〜E07 | 00:02 | 00:10 | 00:18 | 1 |

栄00:10発の新瑞橋行は金山00:18着で、名古屋港行最終00:18と同時刻になるため接続可能とは扱わない。

## 桜通線の徒歩hub方式

桜通線 S01〜S21 は、現在地から丸の内 S04または久屋大通 S05へ直接歩く方式を採用する。

理由:

- 深夜に短区間の地下鉄を前段に使うより直接WALKが自然なケースがある
- 乗換接続を推測しなくてよい
- 「徒歩→hub→終電境界JSON」の共通構成を維持できる

代表境界:

| 目的範囲 | 丸の内 | 久屋大通 | 最終列車 |
| --- | --- | --- | --- |
| S01〜S03 | 00:25 | 00:23 | 太閤通行 |
| S06〜S08 | 00:22 | 00:24 | 今池行 |
| S09〜S17 | 00:06 | 00:08 | 野並行 |
| S18〜S21 | 23:55 | 23:56 | 徳重行 |

## 上飯田線 K01

K01上飯田は、栄 M05 → 平安通 M11 → 上飯田線 K02の1回乗換境界を保持する。

公式データ上の遅い接続候補には、栄00:14 → 平安通00:26 → 00:28という2分接続がある。

しかし平安通で2分接続を安全に保証できる一次情報は確認できないため、プロダクト安全側として `minimumTransferLeadMinutes=3` を採用する。

その結果、平日・土休日とも:

- 栄 00:04発
- 平安通 00:16着
- 上飯田線 00:28発
- 上飯田 00:29着
- transfer margin 12分
- transfers=1

---

## 名鉄瀬戸線 ST01〜ST12

現在地から名鉄栄町 ST01へ直接WALKする。

公式の路線別時刻表PDFをCIで解析し、ランタイムには境界だけを保持する。

2026-03-14改正の代表境界:

| 目的 | 栄町発 | 最終列車 |
| --- | --- | --- |
| ST01 栄町 | 徒歩帰宅 | - |
| ST02〜ST11 | 00:00 | 喜多山行 |
| ST12 大森・金城学院前 | 23:45 | 尾張瀬戸行 |

00:00発は喜多山止まりなのでST12には到達しない。

PDFの表構造、終着、深夜時刻を一意に取得できない場合はCIをfail-closedする。

## 名鉄名古屋本線・常滑線・犬山線

これらは `nagoya` 徒歩hubから名鉄名古屋駅を利用する。

### 対象

- 名古屋本線 NH24〜NH38
- 常滑線 TA01〜TA05
- 犬山線 IY02〜IY03

名鉄は種別・分岐・行先が複雑なので、アプリ側で「この急行は目的駅に停車するはず」と推測しない。

名鉄公式 `DepArrTimeList` のdestination-specificな直通結果を使用し、目的駅ごとに:

- 発時刻
- 到着時刻
- 種別
- 行先
- 直通可否

を検証して境界を生成する。

名古屋本線・犬山線の詳細は次も参照する。

- `docs/meitetsu-main.md`
- `docs/meitetsu-inuyama.md`

## 名鉄築港線 CH01 東名古屋港

CH01は名鉄名古屋から大江 TA03で築港線へ1回乗り換える。

直通系とは分離して乗換metadataを保持する。

### 平日

- 名鉄名古屋 19:25発
- 大江 19:36着
- 大江 19:44発
- 東名古屋港 19:47着
- transfer margin 8分

### 土休日

- 名鉄名古屋 16:55発
- 大江 17:06着
- 大江 17:20発
- 東名古屋港 17:23着
- transfer margin 14分

共通:

- `transferAt=大江`
- `transferStationCodes=[TA03]`
- `minimumTransferLeadMinutes=3`
- `transfers=1`

名鉄公式の各legをdestination-specific結果で確認し、公式境界とproduction JSONをverification CIで突合する。

## 名鉄小牧線 KM12 味鋺

KM12は `sakae` hubから:

```text
栄 → 名城線 → 平安通 → 上飯田線・名鉄小牧線直通 → 味鋺
```

とする。

平安通で1回乗り換えるが、上飯田では同一列車の直通運転なので追加の乗換として数えない。

平日・土休日とも:

- 栄 23:42発
- 平安通 23:54着
- 平安通 00:06発
- 味鋺 00:10着
- 最終列車: 小牧行
- `transferAt=平安通`
- `transferStationCodes=[M11,K02]`
- `minimumTransferLeadMinutes=3`
- `transferMarginMinutes=12`
- `transfers=1`

### 同一列車マッチングの安全策

PoC初期版では「同じ行先 + 近い時刻」だけで栄と平安通の時刻表を結合したため、別列車を誤って結び、栄23:52→平安通23:54という物理的に不正な2分経路を生成できた。

この問題を受け、栄→平安通では**公式時刻表上の所要12分一致**を同一列車条件として必須化した。

一般化すると、複数駅の時刻表を結合する場合は行先文字列だけでなく、所要時間・停車順・列車識別など、その路線で検証可能な追加条件を持つ。

---

## あおなみ線 AN01〜AN11

`nagoya` 徒歩hubを利用する。

2026-03-14改正の代表境界:

| 目的 | 名古屋発 | 最終列車 |
| --- | --- | --- |
| AN01 名古屋 | 徒歩帰宅 | - |
| AN02〜AN09 | 23:58 | 稲永行 |
| AN10〜AN11 | 23:36 | 金城ふ頭行 |

PDFと名古屋駅公式HTMLを突合し、帳票構造や改正情報を確認できない場合はfail-closedする。

## 近鉄名古屋線 KT-E01〜KT-E07

近鉄公式駅番号 E01〜E07 は名古屋市営地下鉄名港線 E01〜E07と衝突するため、内部codeに `KT-` prefixを付ける。

| 内部code | 公式code | 駅 |
| --- | --- | --- |
| KT-E01 | E01 | 近鉄名古屋 |
| KT-E02 | E02 | 米野 |
| KT-E03 | E03 | 黄金 |
| KT-E04 | E04 | 烏森 |
| KT-E05 | E05 | 近鉄八田 |
| KT-E06 | E06 | 伏屋 |
| KT-E07 | E07 | 戸田 |

`nagoya` hubを利用する。

2026-03-14時点でKT-E02〜KT-E07は近鉄名古屋00:04発 普通 富吉行が最終到達列車。

公式列車詳細ページの停車順・時刻・種別・行先までCIで確認する。

---

## JR東海3線

JRは `nagoya` 徒歩hubを利用する。

内部codeは他事業者との衝突を避け、路線prefixを含める。

### 関西本線

- JR-CJ00 名古屋
- JR-CJ01 八田
- JR-CJ02 春田

詳細: `docs/jr-kansai.md`

### 中央本線

- JR-CF01 名古屋〜JR-CF06 新守山

詳細: `docs/jr-chuo.md`

### 東海道本線

- JR-CA68 名古屋〜JR-CA62 南大高

詳細: `docs/jr-tokaido.md`

### JR共通方針

- 公式時刻表PDF/ページから名古屋発の最後に目的駅へ到達する列車を検証
- `nagoya`以外のhubを推測追加しない
- 正確な目的駅到着時刻を公式ソースから今回の方式で確認できない場合は `lastArrival=null`
- `null` を補うために所要時間から推測しない
- generator結果とproduction JSONをCIで突合

---

## 名前空間

公式駅番号は事業者間で衝突する可能性がある。

衝突しない場合は公式codeをそのまま利用できる。

例:

- NH24
- TA01
- IY02
- CH01
- KM12

衝突する場合は内部prefixを付ける。

例:

- 近鉄 E01 → `KT-E01`
- JR CJ00 → `JR-CJ00`
- JR CF01 → `JR-CF01`
- JR CA68 → `JR-CA68`

UIでは可能な限り利用者に馴染みのある公式駅番号・駅名を表示し、内部codeはJSON/API/localStorageの一意性確保に使う。

## 公式ソースと更新

ダイヤ改正や公式ページ変更時は、production JSONを直接推測更新しない。

基本フロー:

```text
公式ソース
  ↓
parser / generator / PoC
  ↓
generated boundary
  ↓
production JSONと比較
  ↓
unit test / verification CI
  ↓
PR
  ↓
main
  ↓
Cloudflare deploy
  ↓
production smoke
```

事業者ごとに公式ソース形式は異なる。

- 名古屋市交通局: 公式オープンデータXLSX/ZIPを優先
- 名鉄: 公式時刻表PDFまたはdestination-specific検索結果
- あおなみ線: 公式PDF/HTML
- 近鉄: 公式駅時刻表/列車詳細
- JR東海: 公式時刻表PDF/ページ

## fail-closed

次の場合は、既存production JSONを自動で「もっともらしい値」に更新しない。

- 駅番号・駅名が変わった
- 公式ページのHTML/PDF/XLSX構造が変わった
- 最終列車を一意に決められない
- 種別・行先・停車駅を確認できない
- 平日/土休日を判定できない
- 乗換前後の列車を安全に対応付けられない
- 必要な最低乗換余裕を満たすか判断できない
- generator結果とproduction JSONが一致しない

この場合はverification CIを失敗させ、人間が公式ソースと設計を確認する。

## APIへの返却

`POST /api/last-train-boundary` は、直通経路だけでなく乗換経路のmetadataも返す。

代表:

- `routeSummary`
- `transfers`
- `transferAt`
- `transferStationCodes`
- `transferReadyTime`
- `connectionDeparture`
- `connectionTerminal`
- `minimumTransferLeadMinutes`
- `transferMarginMinutes`

これによりフロントエンドは、単に「帰れる/帰れない」だけでなく、どこで何時に乗り換える境界かを説明できる。

## MVP完了状態

Issue #42「栄・伏見→名古屋市内の終電JSON基盤を作る」は2026-09-05に完了。

以後の市外拡張、新しい交通事業者、精密な次列車ETAなどは、MVP後の別Issueとして管理する。
