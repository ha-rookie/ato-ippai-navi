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
Workerの読み取り専用CSV
    ↓
Google Sheets IMPORTDATA
```

一方向のみとする。

`GET /ops/last-train-boundaries.csv` は `last-trains-nagoya.json` をリクエスト時に平坦化した派生ビューであり、別のデータ正本ではない。

このendpointはGoogle Routes APIを呼ばず、APIキーやGoogle Sheets認証情報も使用しない。公開repo内の終電境界を人間向けに変換して返すだけとする。

Google Sheets側からGitHub・Workerへ書き戻す経路は作らない。

---

## 3. 運用台帳の構成

### 3.1 `終電データ監視`

路線単位の保守状態を確認するメイン画面。

列:

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

現時点では最終定期検証日時・結果の正本はGitHub Actions実行履歴とし、Sheetへの自動反映は後続Phaseとする。

### 3.2 `終電境界一覧`

`last-trains-nagoya.json` を人間向けに平坦化した読み取り専用ビュー。

列:

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

Google Sheetsでは `IMPORTDATA` で次を読み込む。

```text
https://ato-ippai-api-poc.edward-se-pg.workers.dev/ops/last-train-boundaries.csv
```

Sheet側の値を編集元にはしない。

### 3.3 `更新履歴`

運用変更を時系列で記録する。

列:

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

production更新時の履歴はIssue / PR / merge commitを根拠に記録する。

---

## 4. `checkedAt` の意味

JSONの `metadata.checkedAt` やsource単位の `checkedAt` は、**productionデータを正式に確認・投入した時点**を表す。

定期検証を実行しただけでは更新しない。

理由:

- 週次検証のたびに意味のないcommitを作らない
- 「データを正式に確認した日」と「ジョブを最後に回した日」を混同しない

定期検証の最終実行日時はGitHub Actions実行履歴で管理し、必要に応じてGoogle Sheets運用台帳へ表示する。

---

## 5. ダイヤ改正監視

ダイヤ改正監視は、JSON管理とは別の運用責務として扱う。

### 5.1 週次オーケストレーター

実装:

```text
.github/workflows/weekly-last-train-verification.yml
ops/weekly-verifiers.json
scripts/dispatch-workflow-and-wait.py
```

毎週水曜日 11:17（Asia/Tokyo）に実行する。

時刻を毎時00分からずらし、GitHub Actionsの混雑時間帯を避ける。

`ops/weekly-verifiers.json` に現在のMVPを検証する17 workflowを列挙する。

親workflowは最大3並列で既存の `workflow_dispatch` verifierを起動する。GitHub APIの `return_run_details=true` で子run IDを取得し、各runが完了するまで監視する。

1件でもfailure / cancelled / timeoutになれば親workflowもfailureとする。

### 5.2 対象

- 名古屋市交通局
  - 東山線
  - 鶴舞線
  - 名城線・名港線
  - 名港線 金山乗換
  - 桜通線
  - 上飯田線
- 名古屋鉄道
  - 瀬戸線
  - 名古屋本線
  - 常滑線
  - 犬山線
  - 築港線 CH01
  - 小牧線 KM12
- JR東海
  - 関西本線
  - 中央本線
  - 東海道本線
- 近畿日本鉄道 名古屋線
- 名古屋臨海高速鉄道 あおなみ線

公式ソースから再生成可能な範囲はproduction JSONと比較する。

変更がなければproduction JSONを変更しない。

### 5.3 差分・障害検知

公式ソースから再生成した境界がproduction JSONと一致しない場合、または公式ソース取得・parser・検証が失敗した場合はverificationをfailureにする。

親workflow failure時はGitHub Issueを自動作成し、親run URL・commitを記録する。

調査時はmatrix jobから対象事業者・路線を特定し、子workflowログから駅・曜日区分・公式ソース取得状況を確認する。

**failureが発生してもproduction JSONは自動変更しない。**

### 5.4 人間確認

公式ダイヤ改正の発表を確認した場合、週次ジョブ結果に関係なく対象路線を再検証する。

特に、公式ソースのURL・PDF・HTML構造・検索結果仕様が変更された場合は、時刻差分がなくてもparser / verifierの再確認対象とする。

---

## 6. 更新フロー

```text
公式ソース変更 / 定期検証差分
        ↓
週次verification failure / GitHub Issue
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
Worker CSVも同じJSONから自動反映
        ↓
Google Sheets IMPORTDATAへ反映
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

- 水曜日11:17 JSTに親verification workflowを自動実行
- 17 verifierを最大3並列で再実行
- failure / source取得失敗 / production差分をfail-closed
- 親workflow失敗時は調査Issueを自動作成

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
6. `ops/weekly-verifiers.json` の週次検証対象を必要に応じて更新
7. Google Sheets運用台帳へ対象を追加

---

## 9. 実装ステータス

### Phase A: 完了

- Google Sheets「あと一杯ナビ 終電データ運用台帳」を作成
- 路線単位の `終電データ監視` を初期登録
- `更新履歴` を作成

### Phase B: 実装済み

- GitHub JSON → 読み取り専用CSV → Google Sheetsの一方向同期
- `終電境界一覧` の全件自動展開
- 17 verifierを束ねる週次schedule
- 週次failureのGitHub Issue自動作成

### Phase C: 後続

- `終電データ監視` への最終verification日時・結果の自動反映
- 必要に応じたダイヤ改正告知の別系統監視

---

## 10. セキュリティ・障害分離

`/ops/last-train-boundaries.csv` は読み取り専用で、Google Routes APIを呼ばない。

Google Sheets同期のためにGoogle APIキー・サービスアカウント・GitHubへの書込み権限を追加しない。

Google SheetsまたはIMPORTDATAが失敗しても、`/api/tonight-decision` とproduction終電判定には影響しない。

週次verificationが失敗しても、自動でJSON・Cloudflare productionを変更しない。

---

## 11. 運用原則

> 本番データの正本はGitHub。
> Google Sheetsは終電データの可視化・監視・保守判断のための運用台帳とする。

この原則を変更する場合は、データ更新経路・レビュー・CI・production deployへの影響を再設計する。
