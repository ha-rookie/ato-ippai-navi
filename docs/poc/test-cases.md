# API PoC テストケース

## T01 通常時

- origin: 錦三丁目付近
- destination: 藤が丘駅
- time: 22:30 JST
- 期待: TRANSIT routeFound = true

## T02 深夜境界

- origin: 錦三丁目付近
- destination: 藤が丘駅
- times:
  - 23:20
  - 23:35
  - 23:50
  - 00:05
  - 00:20
- 期待: どこかでその夜に帰れる/帰れないの境界が現れる

## T03 近距離比較

- destination: 金山駅
- 期待: 藤が丘とは境界が異なる

## T04 DRIVE

- destination: 藤が丘駅
- 期待:
  - distanceMeters > 0
  - durationSeconds > 0

## T05 運賃

- transitFareが返るか記録
- 返らなくてもPoC失敗にはしない

## T06 最寄り駅モード

- destinationに駅だけを指定
- 自宅住所・自宅座標は使わない
- TRANSIT / DRIVE両方が成立すること

## T07 実GPS

- スマホのGeolocation APIで取得した緯度経度をoriginに使用
- 期待: 現在地に応じた乗車駅・徒歩区間が返る
