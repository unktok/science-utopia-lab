# 研究ロードマップ

日付はコミットメントではなく、前段階の検証を通過したことを次段階の開始条件とする。

## Phase 0 — 再現可能なローカル基盤（進行中）

成果物:

- Qwen3-8B / Ollama による macOS 実行経路
- ベースライン run、manifest、数値レポート
- 研究憲章、ログ、実験テンプレート
- upstream と研究 fork の分離

完了ゲート:

- 同一設定の再実行と checkpoint が動く
- 設定・出力・コード revision がrun単位で追跡できる
- 既知の環境差と未解決テストが記録される

## Phase 1 — 測定と最適化 harness

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

## Phase 2 — Evaluation System API

成果物:

- `LegacyPeerReviewEvaluation`
- 型付き機構 interface と contract tests
- 少なくとも一つの代替評価機構
- 現行挙動との regression comparison

完了ゲート:

- simulator 本体を分岐せず評価機構を交換できる
- decision provenance と resource effect を追跡できる

## Phase 3 — 多目的ブラックボックス制度探索

成果物:

- Bayesian / evolutionary / multi-fidelity baseline
- Pareto front と robustness report
- Goodhart / adversarial stress suite
- 最初の研究報告または論文草稿

完了ゲート:

- random search と同予算で比較できる
- 選ばれた制度が未使用 seed と環境 shift で検証される
- 改善だけでなく代償と失敗範囲を説明できる

## Phase 4 — 微分可能な評価機構

成果物:

- 連続緩和された評価・配分機構
- differentiable surrogate
- gradient / ES / black-box の比較
- gradient fidelity 診断

完了ゲート:

- surrogate 上だけでなく真の simulator 上で改善を確認する
- 勾配近似が壊れる条件を特定する

## Phase 5 — 科学システム構造探索

成果物:

- mechanism graph schema
- publication / funding / governance の分離
- 構造とパラメータの共同探索
- 複雑さと性能の trade-off

## Parallel Track — Game vertical slice

Phase 1 の canonical event schema を利用し、read-only replay viewer を作る。その後、checkpoint から制度を変更して branch できる interactive prototype へ進む。研究 core とUIの二重実装は禁止する。

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

## Repository relocation backlog

現在のrepositoryは`/Users/shiro/ScienceUtopia`にある。active experimentがない区切りで
移動先を決めて移す。tracked sourceにはこの絶対pathの固定参照はないが、historical
manifestの絶対pathはprovenanceとして書き換えない。移動後はvirtual environmentと
cacheを再接続し、testsとsmoke runを通してから長時間campaignを開始する。

## Optimization v1 — 次の主マイルストーン

1. optimizerが直接参照する`LossSpec`を一つversion固定する。
2. lossに使うoptimization seedsと、候補凍結後のevaluation seedsを分離する。
3. evaluation metricsはaccuracyに相当するheld-out評価として定義し、同じcampaignの
   candidate更新には使わない。
4. bounded parallel schedulerを安全性監査後に統合し、workers 1/2/4を実測する。
5. random/Sobol初期点から`observe`し、少なくとも一回は結果依存の次候補を
   `suggest`する閉ループを完成させる。

technical validity以外のfloorやvetoは既定では置かない。必要な場合だけ、lossとは
別の明示的constraintまたはcampaign終了後のdecision policyとしてversion化する。

