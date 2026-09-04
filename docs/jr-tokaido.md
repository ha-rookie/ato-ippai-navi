# JR東海道本線（名古屋市内）終電境界

## 対象

既存 `nagoya` 徒歩hubからJR東海・東海道本線へ直接乗車するPhase 1方式。

- JR-CA68 / CA68 名古屋（walk-home）
- JR-CA67 / CA67 尾頭橋
- JR-CA66 / CA66 金山
- JR-CA65 / CA65 熱田
- JR-CA64 / CA64 笠寺
- JR-CA63 / CA63 大高
- JR-CA62 / CA62 南大高

CA61共和・CA69枇杷島は名古屋市外のため対象外。

## 公式ソース

JR東海 名古屋駅 東海道線 豊橋・武豊方面 2026-03ダイヤ。

- 平日: `tokaido_Nagoya_A_w_u.pdf`
- 土曜・休日: `tokaido_Nagoya_A_h_u.pdf`
- 駅番号: JR東海公式 station-numbering railway map

CIで公式PDFを取得して `pdftotext -layout` し、23時台最終ブロックと0時台空欄、右側停車駅案内を検証する。

## verified boundary

| 目的 | 名古屋発 | 列車 | lastArrival |
| --- | --- | --- | --- |
| CA68 名古屋 | 徒歩帰宅 | - | - |
| CA62〜CA67 | 23:59 | 普通 岡崎行 | null |

平日・土曜休日とも同じ。

各駅の正確な最終到着時刻はこのソースから取得していないため、`lastArrival` は推測せず `null` とする。

## fail-closed

以下が変わった場合はofficial-source CIを失敗させる。

- 23:59岡崎行・普通という列車属性
- 0時台に列車が追加
- 名古屋→尾頭橋→金山→熱田→笠寺→大高→南大高→共和の停車駅案内
- 公式PDF構造または必須トークン

ランタイムには全時刻表を持たず、目的駅ごとの終電境界のみをproduction JSONへ保持する。
