# 制度の作用経路に関する設計と最初の接続検証

2026年11月11日。[研究計画](../publication/institution-causal-design-plan.md)の第一段階を実装・検証した。
本会議に必要な重要な研究結果や、LLMによる新制度の発明を達成した段階ではない。

## 研究上の区別

同じ情報・記憶・操作権限・時点を持つ任意のコードがgraphの処理を代替できる場合、
graphだけの原理的な必要性は主張できない。固定パラメータ族の範囲、情報／操作の利用可能性、
同じ権限を持つ表現の探索しやすさを区別して比較する。
目的関数はT/Eを維持し、新nodeや新配線を作るための報酬・vetoを加えない。

## 実装したもの

- `native_causal_design.describe`：実際のschedule・port・wireから年内順序を説明する。
  現在の費用80→査読90→採否130を示し、既定例の105/110を誤って使わないようにする。
  任意コードの因果効果や全worldのcausal DAGを推論するものではない。
- `causal_design_context`：strategyの不変provenanceからcampaign requestへ渡すopt-in設定。
  editorの`reference/causal-design.json`をread-onlyとし、実際のbounded読取・提出・cold replayまで確認した。
- 新しい明示domain：既存のtyped review-routingを研究生産と区別して許可する。
  旧fixed-production-v1の拒否条件は保持し、新scopeにのみ適用する。
  生産・会計・project権限・元plan・runtime imageの保護は維持する。
- 元の研究者worldに、明示した85/87のsnapshot／sourceを置く接続検証。
  受け付けた割当と実査読taskのID・件数・原投稿batch hashを照合する。

前回の提案はこのtyped割当機構を使っていないため、旧domainの制限が前回の不成功の原因だったとは言わない。

## 実行で確認した範囲

研究者HTTPとcorpusはscripted、元のSimulation年次処理とnetworkless Dockerは実物。
fixtureの4研究者・2年・同一seedで、次の3条件をそれぞれ2つのhost clockで確認した。
2つの時計は独立な科学的seedではなく、時計への依存を調べるQAである。

| 開発者が与えた条件 | 初年の実査読件数 | 翌年の実投稿数 | 2年のA | 2年のQ | 2年のR |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1査読者／全不採択 | 4 | 8 | 0 | 0 | 12 |
| 2査読者／全不採択 | 8 | 8 | 0 | 0 | 24 |
| 2査読者／全採択 | 8 | 4 | 8 | 32 | 16 |

各時計の中で初回査読前の全モデル入力と実投稿batchは一致する。
査読前の割当が実件数4→8を変える一方、後続の採否を変えても初年8は変わらない。
しかし翌年は不採択の再投稿を含む8件と、全採択後の4件に分かれ、2年の査読総数も変わる。
つまり「年内の済んだ仕事は変えられない」と「将来の仕事も変わらない」は違う。
これは手作業の対照による接続・時間的作用の確認であり、探索やモデル発明の優位性ではない。

## 検証と保持

clean446cd29で9module・173件が55.52秒でpass。実行前後のsource/HEADは不変。
前のclean28d5991は169pass/1failであり、そのJUnitと失敗worldを保持する。
不一致は投稿の`submission_time`だけだったため、raw値を削らず、対照内の時計を合わせて別時計でも再検証した。
その中間のcleanbf2d202は171件pass。失敗を成功へ書き換えたり、実行期限を延ばしたりしていない。
[source・hash・scopeの記録](institution-causal-design-verification-v1.json)。
[実行順序のretained data](../data/native-causal-design-v1/README.md)も独立再生成できる。

新しい実LLM比較は未開始。次はsourceと二履歴を固定し、fresh readiness後に最大8 authoring sessionで
順序説明あり／なしを比較する。その結果と新しい有限protocolを経て、元世界での目的別閉ループ比較へ進む。
この第一段階の完了を研究全体の完成や投稿可能性に置き換えない。
