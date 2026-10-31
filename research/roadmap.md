# 研究ロードマップ

日付はコミットメントではなく、検証ゲートを次段階の開始条件とする。Phaseは能力層を示し、必ずしも直列に大規模化しない。Decision 0021により、次は各能力を小規模に一度つなぐbreadth-first integrationを優先する。

## 現在の主マイルストーン — Miniature Whole-System Design Lab v0

少数agent、1〜2年、1〜2 development seeds、少数候補で、次を同じend-to-end workflowに接続する。

1. `ObjectiveSpec`から`LossSpec`とheld-out diagnosticsを生成する。
2. evaluationに加えてpublication、funding、government、communicationのうち少なくとも2機構を含む小さな構造grammarを凍結する。
3. nodeの有無・実装置換と、edgeまたはschedule/latencyをブラックボックス探索する。
4. 同じ設計対象に対する微分可能relaxationから候補を射影する。
5. 両方の候補を同じ離散`SystemSpec` validatorとmodel-backed simulatorで外側評価する。
6. objective、proposal lineage、graph差分、world events、observed lossを同じcanonical artifactsからゲームで表示する。

この段階ではoptimizer superiorityや統計的安定性を主張しない。統合sliceの完了後にseed、optimizer、候補予算、population、期間を一軸ずつ増やす。

## Phase 0 — 再現可能なローカル基盤（完了・維持）

成果物:

- Qwen3-8B / Ollama による macOS 実行経路
- ベースライン run、manifest、数値レポート
- 研究憲章、ログ、実験テンプレート
- upstream と研究 fork の分離

完了ゲート:

- 同一設定の再実行と checkpoint が動く
- 設定・出力・コード revision がrun単位で追跡できる
- 既知の環境差と未解決テストが記録される

## Phase 1 — 測定と最適化 harness（parameter-level v1.1完了）

成果物:

- 設計変数 registry
- objective / constraint の metric cards
- seed を束ねる run registry
- random と Sobol の探索 baseline
- runtime、分散、failure rate の測定

完了ゲート:

- 一つのコマンドで design -> replicate runs -> report が生成される
- 5〜8変数の小規模探索を再現できる
- 未使用 seed で候補を再評価できる

## Phase 2 — SystemSpecと機構グラフ基盤（部分実装・v0統合対象）

成果物:

- whole-system `SystemSpec` schemaとvalidator
- 現行システムを再現する`LegacySystemSpec` compiler
- 型付き機構interface、接続規則、contract tests
- canonical event/replayによるグラフ実行の観測
- Evaluation System APIを最初のvertical sliceとして接続

完了ゲート:

- legacy構成を`SystemSpec`から再現できる
- 少なくとも一機構をsimulator本体の分岐なしで交換または除去できる
- 機構間のdecision provenanceとresource effectを追跡できる

## Phase 3 — 多目的ブラックボックス制度探索（統合後にscale-up）

成果物:

- Bayesian / evolutionary / multi-fidelity baseline
- Pareto front と robustness report
- Goodhart / adversarial stress suite
- 最初の研究報告または論文草稿

完了ゲート:

- random search と同予算で比較できる
- 選ばれた制度が未使用 seed と環境 shift で検証される
- 改善だけでなく代償と失敗範囲を説明できる

## Phase 4 — 科学システム構造探索（miniature sliceを次に実行）

成果物:

- mechanism graphの構造変異operator
- publication / funding / governanceの分離
- 構造とパラメータの共同探索
- 複雑さと性能のtrade-off

完了ゲート:

- 異なるtopologyを同じ実験contractで実行・比較できる
- 未使用seedと環境shiftで構造候補を再評価できる

## Phase 5 — 微分可能な科学システム（synthetic proofをminiature outer loopへ接続）

成果物:

- 連続緩和された機構・接続・配分
- differentiable surrogate
- gradient / ES / black-boxの比較
- gradient fidelity診断

完了ゲート:

- surrogate上だけでなく真のsimulator上で改善を確認する
- 勾配近似が壊れる機構・構造・条件を特定する

## Integrated Track — Game vertical slice

read-only canonical replay、system sandbox、branch comparison、optimization observatoryの各sliceは存在する。次はこれらを別デモとして増やすのではなく、Miniature Whole-System Design Lab v0のobjective、proposal、graph、outer evaluationへ接続する。研究coreとUIの二重実装は禁止する。

長時間run中の並行開発は、凍結した実験worktreeとtrack別の開発worktreeを分離して
行う。GPU貸出機の要件、実測runtime換算、event/replay・UI・Evaluation API・
mechanism graphの並行境界は
[`compute-and-parallelization-plan.md`](compute-and-parallelization-plan.md) に固定する。

## 直近の次の3項目

1. **完了:** v1で最大のstress caseだったbaseline seed 113をv2で1本だけfull実行し、funding conservation・objective・reliability gateをend-to-end検証した。
2. **完了:** 4年・10人のlongitudinal baseline seed 113は、参加人数10→10→10→8、最終aggregate 0.8、lower slice 0.6で、事前登録した測定可能性gateを通過した。
3. **完了:** repaired source commit上でbaseline/candidate各5 seedsを完走した。候補は参加率をaggregate +0.08、lower slice +0.16改善したがgrant input +160を要した。baseline seed 107が固定capability floorを下回ったためformal comparisonはincomplete、5-pair vectorはdiagnostic evidenceとして保持した。

## Confirmation campaign の完了

capability violationを技術的失敗と分離し、制度のoutcome distributionとして
全件保持する規約を[`confirmation-comparison-v1.md`](confirmation-comparison-v1.md)
に事前登録した。未使用confirmation seeds 401, 409, 419, 421, 431でbaselineと
固定済みcandidateを各5件完走した。

候補は5/5でcapability floorを満たし、平均参加率をaggregate +0.06、低資源層
+0.12改善した。一方seed 431で低資源層が0.8→0.6となり、負のprotected-slice
pairを許さない固定gateに違反したため、判断は`not_confirmed`である。次はこの
candidateを閉じ、新しいdesign集合・seed分割・判断規則を事前登録したmulti-design
campaignへ進む。

## Repository relocation

repositoryは`/Users/shiro/unktok/dev/science-utopia-lab`へ移動済みである。
historical manifestの絶対pathはprovenanceとして維持し、旧pathのcompatibility
symlinkとartifact manifestの`current_locator`で接続している。統合testsは移動後の
実体pathで通過済みであり、次の長時間campaign前にsmoke runを行う。

## Optimization v1 — 完了した基礎マイルストーン

1. **完了:** optimizerが直接参照する`LossSpec`をversion固定した。
2. **完了:** lossに使うoptimization seedsと、候補凍結後のevaluation seedsを分離した。
3. **完了:** evaluation metricsはaccuracyに相当するheld-out評価として定義し、同じcampaignの
   candidate更新には使わない。
4. **完了:** bounded parallel schedulerを安全性監査後に統合し、workers 1/2/4を実測した。
5. **完了:** 初期点から`observe`し、少なくとも一回は結果依存の次候補を
   `suggest`する閉ループを完成させた。

最初の実行では現行固定topologyのparameter vectorを制限版`SystemSpec`として用いて
よい。ただしoptimizer APIとcampaign recordの設計単位はsystem全体とし、
Evaluation Systemだけを恒久的な最適化対象にはしない。

technical validity以外のfloorやvetoは既定では置かない。必要な場合だけ、lossとは
別の明示的constraintまたはcampaign終了後のdecision policyとしてversion化する。

