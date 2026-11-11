# 順序説明による制度設計の小規模診断

2026年11月11日。閉鎖済みのT/E探索の初回と第2回requestを再提示し、
現在の制度設計者が何を提出できるかを8セッションで調べる。
新しい閉ループ探索、候補のloss比較、スケール拡大ではない。

## 固定する比較

Tは`-A`、Eは`-Q+0.5R`。元のLossSpec、親制度、history、observations、
generation、rng_seedをそのまま保持する。各目的のcode-and-graph armの
G0/G1 requestを使う。旧実験sourceは`62388a74d071a3a4fdc8cc309c2807422f96223f`。
旧結果の原source監査は[閉鎖記録](../../results/pre-scale-search-closed-verification-v1.json)を参照。
planには各stateファイルSHA256とrecord内request digestを固定する。
未使用seedの評価結果はrequestへ追加しない。

両群とも新しい明示的review-routing domainを使う。変更する説明条件は
`causal_design_context`だけで、説明あり群は現在graphから導出したread-only fileを読める。
既知の解コードや追加world呼出は与えず、同じモデル・権限・時間枠を使う。
元world_bindingは旧sourceのまま残し、現在authoring sourceとは分ける。
feedback_policyに両sourceと「履歴測定は新候補の測定ではない」を表示する。
初回requestのgeneration0と履歴なしは維持する。

順番はhistory0から1、各historyでTからE。T/h0とE/h1はoff→on、
E/h0とT/h1はon→off。既存のモデルseedはrequest-binding依存のため、
説明条件が変わればseedも変わりうる。共通乱数実験や効果量の確証とは呼ばない。

## 実行枠と停止

承認済みlocal designer `qwen3.6:35b-mlx-64k`、実context40960、thinking off。
8 authoring session、各16 action、各応答8192 output token、1200秒。
HTTPは接続10秒・読取900秒。生UTF-8 requestを送信前に保存する。
元のQwen3-8B研究者への新しい呼出はなく、native worldは0。

新source/model/backendに対して説明条件別にfresh execution-readiness-v39を実行する。
各条件は長いE/h1 requestを使い、最大40 POST、1200秒。
2 calibrationを含む最大POST数は208（80 calibration、128 authoring）。
calibration失敗は候補dispatchを止める。完了不明は全ての後続推論を止める。
既知の候補失敗は当該枠を消費し、次の事前固定枠へ進む。失敗補充、
自動修復、回答salvage、条件変更、再dispatchは行わない。
再度runを要求しても拒否し、既存出力はcold auditのみ許す。

## 分析

8枠全てについて未送信／提出失敗／静的有効を残す。
literal code、connection、scheduleの変更、説明fileの読取、実際の呼出数、
backend prompt/output tokenと終了理由、時間を記録する。
不明costは0としない。両群とも同じ新domainを使うため、旧探索との直接比較を
説明の効果とは解釈しない。

cold replayと実interpreterで提出を復元し、生成コードはhost上で実行しない。
新候補をnative worldで実行するのは次の別protocolとする。
したがって静的有効な提出でも、作用・loss改善・科学の改善は本診断では未測定。
新しいgraphを出すことを合格条件にしない。
