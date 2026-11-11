# 固定内容採点器の実入力準備

閉鎖済み62388a7の元source readerで44完了checkpointのhash、world、年、採択数を照合した。
5途中失敗は除外し、欠測の完成結果を作っていない。
263採択decisionは76種類のtitle／abstract／topicsに対応し、すべて短縮なしで要求上限に収まる。
要求全体は1449〜3232 UTF8 bytes。これはtoken容量や実モデルの互換性の検証ではない。

- `staging.json` は内容hash、critic別の要求hash／bytes、全countを保持する。
- `contract.json` は準備時のsource af294b7、期待する既存8Bモデルとbackend、固定rubric等を保持する。

同じdata／contract／summaryを二回生成し、全fileのbytesが一致した。
rawの全文／paper ID付き対応表`contents.json`はignored outputsへ保持し、ここには含めない。
新しいモデル呼出、採点値、新world、新しい最適化結果はない。

76内容×3criticなら最大228 POSTである。保存契約の一般上限789は263 decision×3という保守的な
準備値であり、このデータに対する228回の実行許可や新実験の凍結protocolではない。
実際に呼ぶ前に、目的、対象、有限予算、既存モデルの実互換性と未使用評価の扱いを固定する。

元のfull auditはcontent85d4698f。checkpoint読出しと件数のjoinを行ったのであり、1859 raw
全体のfull auditを今回また実行したという意味ではない。
[component契約](../../components/common-content-observer-v1.md)と
[検証記録](../../results/common-content-observer-verification-v1.json)を参照する。

再生成はaf294b7のclean checkout、承認済みinterpreterで
`scripts.reports.stage_common_content_observer_v1`へ`--run`、`--audit`、元62388a7の
`--frozen-source`、新しい`--output`を明示する。元rawとfull auditはGitに含まれない。
現在の別commitで作る契約のsource IDが変わる場合は、同一artifactのprompt／seedと
運用provenanceの変更を分けて比較する。運用識別子だけではpromptは変えない。
