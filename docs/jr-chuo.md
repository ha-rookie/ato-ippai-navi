# JR中央本線（名古屋市内）終電境界

## 対象

既存 `nagoya` 徒歩hubからJR東海・中央本線へ直接乗車するPhase 1方式。

- JR-CF01 / CF01 名古屋（walk-home）
- JR-CF02 / CF02 金山
- JR-CF03 / CF03 鶴舞
- JR-CF04 / CF04 千種
- JR-CF05 / CF05 大曽根
- JR-CF06 / CF06 新守山

CF07勝川以降は名古屋市外のため対象外。

## 公式ソース

JR東海 名古屋駅 中央線 多治見・中津川方面 2026-03ダイヤ。

- 平日: `chuo_Nagoya_A_w_d.pdf`
- 土曜・休日: `chuo_Nagoya_A_h_d.pdf`
- 駅番号: JR東海公式 station-numbering railway map

CIで公式PDFを取得して `pdftotext -layout` し、0時台最終ブロックと停車駅順を検証する。

## verified boundary

| 目的 | 名古屋発 | 列車 | lastArrival |
| --- | --- | --- | --- |
| CF01 名古屋 | 徒歩帰宅 | - | - |
| CF02〜CF06 | 00:05 | 普通 高蔵寺行 | null |

平日・土曜休日とも同じ。

各駅の正確な最終到着時刻はこのソースから取得していないため、`lastArrival` は推測せず `null` とする。

## fail-closed

以下が変わった場合はofficial-source CIを失敗させる。

- 0:05ブロックの存在
- 高蔵寺行 / 普通という列車属性
- 0時台に追加列車が出現
- 名古屋→金山→鶴舞→千種→大曽根→新守山→勝川の停車駅順
- 公式PDF構造または必須トークン

ランタイムには全時刻表を持たず、目的駅ごとの終電境界のみをproduction JSONへ保持する。
