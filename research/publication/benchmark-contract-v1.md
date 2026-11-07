# Objective-conditioned institution benchmark：比較contract v1

Status: **design contract / not an executed campaign protocol**。2026-11-07。
次の実行前に、実source、コード、条件、seed、有限予算を別のprospective protocolへ固定する。
この文書はモデル呼出・world起動・有料サービスを開始しない。

## 問題と境界

入力は目的LossSpec、初期SystemSpec、利用可能な初期観測、探索予算。
設計対象は制度の数値、実装コード、node/edge、state、protocol、活動過程。
研究者の重み・corpus・世界の基本adapterは比較内で固定する。
提案器→技術検査→元世界実行→測定→canonical loss→ask/tellを再利用する。
新しいtoy simulatorやoptimizer frameworkを増やさない。

## 比較の軸

| 軸 | 比較対象 |
| --- | --- |
| 目的 | 既存の明示的なLossSpec。全測定を保存し、全候補を同じ目的集合で相互採点 |
| 自由度 | 固定制度／parameter-only／自由code・固定graph／自由code・graph・process |
| 提案 | random/evolutionary、LLM no-loss-feedback、LLM loss-feedback |
| 任意の推定器 | 宣言した座標・分布のLR等。対応しない任意コードまでbackpropしたとしない |

目標は目的を変えたときの制度・経路・帰結であり、特定の方式を勝たせることではない。
同じ制度・同点でも正しい結果。作者名や目的ラベルで候補を不採用にしない。

## 最初の最小pilot案

- 原世界の5研究者・2年・開発seed42・4年corpus。研究者Qwen3-8B固定。
- 比較する二目的は既存throughputとnet-reviewed-utilityを候補とする。
  この選択は過去開発結果を見たfeasibility設計であり、新しい事前仮説の実証ではない。
  将来の確認では重み感度と未使用条件を別途固定する。科学的価値の代理にすぎない。
- 一つの共通初期SystemSpecをfresh同一sourceで評価する。目的がforwardに入らない
  ことを確認できた場合だけ、同じ測定ベクトルを複数目的で採点する。
- 二目的×二方式(feedback/no-feedback)×二候補＝8候補枠。
  共通baselineを別に1物理worldとすれば、最大9物理worldの計画案。
- 失敗は枠を消費しnull。別候補で補充しない。成功分だけの勝率にしない。
- 自由度比較はその後の別計画。最初の8枠だけで、parameter-onlyを上回ると主張しない。

上記は案であり、まだdispatch予算として確定していない。P1の対照を実装・検証し、
source/model/backend/profileを固定したfresh校正後に実行protocolを作る。

## No-feedback対照の重要点

科学的lossを隠しても、lossで選んだ親、候補順、best印、strategy重み、自然言語の
成功説明から情報が漏れる。no-feedback群はlossに依存しない固定初期親または
事前固定の親選択を使い、これら全てをテストで検査する。
最終bestの選択は両群とも宣言したlossだけで行う。提案器への情報遮断と、
評価・採用基準を混同しない。技術的な形式・実行エラーは両群へ同じ条件で返せる。

## 費用・初期観測

- oracle予算は論理候補枠と実physical worldを両方数える。
- 初期観測、cache/checkpoint採用、failed/partial呼出を明示する。共有履歴を新規実験としない。
- 設計者POST/token/秒、研究者POST/token/秒、実行・container・監査費用を分ける。
- LLM方式の呼出上限・出力・connect/read timeout・校正枠をdispatch前に固定する。
- 同じoracle回数と同じ総計算費用は異なる比較。両方の曲線を表示し、同一とは言わない。

## 必須保存と図

1. 全候補、生成source、親、graph差分、条件付き更新、失敗原因、source/model/data bindings。
2. 目的ごとのbest-so-farと全試行。技術失敗を数値lossで埋めない。
3. 全候補×全目的のcross-score行列。同点と欠測を含め、異なる尺度を平均しない。
4. 予算／wall timeとbest loss。過去観測を含む線と新規だけの線を分ける。
5. 機構が実際に変えた情報、研究計画、査読割当、資源等を原文・領収書へつなぐ。

## 選択後の評価

開発の目的・候補選択を固定してから未使用seed/条件で評価する。
既に見たseedをheld-outに戻さない。独立単位はworld/seedであり、年や研究者を
独立反復としない。同じprefix・cache・同一checkpointの相互採点は独立標本でない。
単一seedのpilotには有意差・期待改善・モデル一般性の主張を付けない。
技術的失敗も評価結果として報告し、後から隠れた科学的vetoを追加しない。
