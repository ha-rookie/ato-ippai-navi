# 終電JSON運用設計

## 目的

MVPとして完成した `src/data/last-trains-nagoya.json` を、ダイヤ改正・公式ソース更新・対象路線拡張に対して安全に保守するための運用方針を定義する。

本書はデータ構造そのものではなく、**正本・監視・確認・更新・公開の運用責務**を扱う。

データ構造は `docs/last-train-json.md` を参照する。

---

## 1. Source of Truth

本番終電データの唯一の正本は次のJSONとする。

```text
src/data/last-trains-nagoya.json
```

Google Sheets、Notion、GitHub Issue、ローカルファイルは正本にしない。

本番WorkerはGitHub管理下のJSONを利用する。

### 原則

- JSON変更はGitHub上でレビュー可能な差分として管理する
- 変更は原則 branch → PR → CI → merge → production deploy → production smoke の順で反映する
- `status=verified` の経路だけを本番判定に利用する
- 公式ソースと矛盾した状態を自動的に本番へ反映しない

---

## 2. Google Sheetsの責務

Google Sheets「あと一杯ナビ 終電データ運用台帳」は、人間が保守状態を確認するための**可視化・監視ビュー**とする。

### 用途

- どの事業者・路線を最後にいつ確認したかを見る
- 公式ダイヤのrevisionとJSONの状態を一覧する
- 要確認の路線を見つける
- JSONの終電境界を人間が読みやすい表で確認する
- 更新履歴をGitHub Issue / PRと関連付けて残す

### 禁止事項

- Sheetを正本にしない
- Sheetのセル編集からproduction JSONを自動更新しない
- JSONとSheetの双方向同期を行わない
- Sheet上の値だけを根拠に本番データを変更しない

### 同期方向

```text
GitHub JSON
    ↓
Google Sheets
```

一方向のみとする。

将来Apps Script等で同期する場合も、GitHub公開JSONを読み取り専用で取得し、Sheetへ展開する。

---

## 3. 運用台帳の構成

### 3.1 `終電データ監視`

路線単位の保守状態を確認するメイン画面。

推奨列:

- 事業者
- 路線
- 対象駅コード範囲
- 主なsourceId
- 公式revision / checkedAt
- JSON metadata.checkedAt
- 最終定期検証日時
- 定期検証結果
- 次回確認目安
- 要確認フラグ
- GitHub Issue / PR
- 備考

このタブでは全駅の終電時刻を編集しない。

### 3.2 `終電境界一覧`

`last-trains-nagoya.json` を人間向けに平坦化した読み取り専用ビュー。

推奨列:

- 目的駅コード
- 駅名
- 事業者
- 路線
- hub
- 曜日区分
- 最終出発
- 最終到着
- 経路概要
- 列車行先
- 乗換回数
- 乗換駅
- 接続列車発車時刻
- 乗換余裕
- status
- sourceIds

### 3.3 `更新履歴`

運用変更を時系列で記録する。

推奨列:

- 日付
- 事業者 / 路線
- 変更種別
- 概要
- 公式revision
- Issue
- PR
- merge commit
- production smoke
- 備考

---

## 4. `checkedAt` の意味

JSONの `metadata.checkedAt` やsource単位の `checkedAt` は、**productionデータを正式に確認・投入した時点**を表す。

定期検証を実行しただけでは更新しない。

理由:

- 週次検証のたびに意味のないcommitを作らない
- 「データを正式に確認した日」と「ジョブを最後に回した日」を混同しない

定期検証の最終実行日時は、GitHub Actions実行履歴またはGoogle Sheets運用台帳側で管理する。

---

## 5. ダイヤ改正監視

ダイヤ改正監視は、JSON管理とは別の運用責務として扱う。

### レベル1: 定期自動検証

原則週1回、既存のgenerator / parser / verification workflowを再実行する。

対象:

- 名古屋市交通局
- 名古屋鉄道
- JR東海
- 近畿日本鉄道
- 名古屋臨海高速鉄道（あおなみ線）

公式ソースから再生成可能な範囲は、production JSONと比較する。

変更がなければproduction JSONを変更しない。

### レベル2: 差分検知

公式ソースから再生成した境界がproduction JSONと一致しない場合は、検証をfailureにする。

差分検知時は次を行う。

1. どの事業者・路線・駅・曜日区分が変わったかを特定
2. 自動でproduction JSONを書き換えない
3. GitHub Issueまたは既存Issueへ記録
4. 公式情報を人間が確認
5. 必要なPoC / generator修正を行う

### レベル3: 人間確認

公式ダイヤ改正の発表を確認した場合、週次ジョブ結果に関係なく対象路線を再検証する。

特に、公式ソースのURL・PDF・HTML構造・検索結果仕様が変更された場合は、時刻差分がなくてもparser / verifierの再確認対象とする。

---

## 6. 更新フロー

```text
公式ソース変更 / 定期検証差分
        ↓
GitHub Issue
        ↓
公式一次情報確認
        ↓
PoC / generator / parser確認
        ↓
branch
        ↓
production JSON更新
        ↓
PR
        ↓
CI / verification
        ↓
merge
        ↓
Cloudflare deploy
        ↓
production smoke
        ↓
Google Sheets運用台帳更新
```

### fail-closed

以下の場合はproduction JSONを自動更新しない。

- 公式ソースを取得できない
- HTML / PDF / XLSX構造が想定と異なる
- 駅・列車・行先を一意に結び付けられない
- 乗換列車の同一性を保証できない
- 公式時刻とproduction JSONが矛盾する
- 到着時刻を一次情報から確認できない

確認できない値は推測で埋めない。既存方針どおり、必要に応じて `null` または未検証として扱う。

---

## 7. 定期運用サイクル

### 週次

- verification workflow実行
- failure / source取得失敗の確認
- 差分があればIssue化

### 月次

- Google Sheets `終電データ監視` を確認
- 最終検証が古い路線、source revision不明の路線、要確認フラグを棚卸し
- 公式サイトのダイヤ改正告知有無を確認

### イベント駆動

鉄道事業者からダイヤ改正が発表された場合は、定期サイクルを待たずに対象路線を再検証する。

---

## 8. データ拡張時

市外駅・新規路線・新規hubを追加する場合も、既存JSONへ直接手入力だけで追加しない。

最低限:

1. 対象範囲をIssueで定義
2. 公式ソースを確認
3. 境界生成・検証方式を設計
4. `status=verified` をCIで保証
5. production smokeを追加
6. Google Sheets運用台帳へ対象を追加

---

## 9. 将来実装

運用方針確定後、以下を段階的に実装する。

### Phase A

- Google Sheets「あと一杯ナビ 終電データ運用台帳」を作成
- 現行JSONを `終電境界一覧` へ展開
- 路線単位の `終電データ監視` を初期登録

### Phase B

- GitHub JSON → Google Sheets 一方向同期
- 週次verification workflowの統合またはschedule化

### Phase C

- 差分検知時のIssue自動作成または通知
- 運用台帳への最終検証日時・結果反映

---

## 10. 運用原則

> 本番データの正本はGitHub。
> Google Sheetsは終電データの可視化・監視・保守判断のための運用台帳とする。

この原則を変更する場合は、データ更新経路・レビュー・CI・production deployへの影響を再設計する。