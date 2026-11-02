# 研究ロードマップ

日付はコミットメントではなく、検証ゲートを次段階の開始条件とする。Phaseは能力層を示し、必ずしも直列に大規模化しない。Decision 0021により、次は各能力を小規模に一度つなぐbreadth-first integrationを優先する。

## 現在の主マイルストーン — 目的条件付きの自由な制度改訂 v12

実装済みの生成・実行基盤を使い、2目的×3世代×1候補で制度のコード・
機構・protocol・配線・活動processを改訂し、全経路と両目的でのcross-scoreを
比較する。別枠でv11最後の補正付き更新後を2候補で前向き評価する。
総予算最大8試行、人数・年数・科学seedは据え置き。改善が出るまで追加しない。
独立監査・図と英語UIも並列に進める。[有限ゴール](milestones/2026-11-02-objective-open-redesign-v12.md)
と[事前protocol](protocols/campaigns/native-objective-redesign-v12.md)を現行基準とする。

## 完了した有限マイルストーン — 自由な制度設計と勾配推定 v11

ユーザーの確認により、全世界の微分可能化は目的でも必須完成条件でもない。
目的関数に対して、制度のコード・ルール・配線・構造を最適化する。
ブラックボックス評価、尤度比による期待損失の勾配推定、微分可能な表現は
それぞれ手段として選択・併用する。Decision0028、STATUSと
[有限v11ゴール](milestones/2026-11-02-open-native-estimators-v11.md)を現行の基準とする。

元の研究者世界を保ち、自由な制度生成の共通境界、過去データだけで作る
補正付きcontrol variate、実測経路を見せる英語UIを並列で実装した。
人数・年数・seedを増やさず8世界・742応答を完走し、独立監査した。
両手法とも最初の最良値は更新していない。G0のLR更新後はnativeで再評価し、
最後のG1 control-variate更新は保存までで再評価していない。
最適化の実装が動くことと、有用な制度を発見したことは別々に報告する。
残る小規模の研究課題は、最終更新後の評価、推定量の性質、自由な制度・設計者の
有効な改訂、より意味のある目的と活動であり、全世界ADや大規模化は必須条件でない。

以下のv6以降の記述は各時点の計画・履歴であり、現在の完了条件ではない。

## 前段階 — 非スケール統合 v6（履歴）

[完了条件と非主張](milestones/2026-11-01-non-scale-completion-v6.md)、
[全体目標との対応表](program-map.md)、[実行STATUS](STATUS.md)を参照。
人数・seed数の追加より、元世界を保ったまま以下の経路を閉じることを優先する。

1. 研究計画・投稿対象・実論文bundleをtyped input/outputにし、任意制度から
   実際の研究活動を変更する。元世界6年分の同値性を退行テストで保持する。
2. code/protocol/wiringを組み合わせる提案分布の正確なlog probabilityから、
   元世界の実損失でscore-function backwardを行う。世界全体のpathwise微分とは別。
3. 同一社会の実観測→loss付き提案→正確な同意→永続導入→次年度feedbackを
   小規模に実行する。実RAG、途中停止・再開、保存前後の整合性も確認する。
4. 英語ゲームUIで履歴と導入を確認し、HTTP成功ではなく保存済みreceiptの独立検証を
   導入完了条件にする。失敗、raw hash、原稿と図も更新する。

これらの実装と小規模統合が終わっても、自由なactor/活動意味論、忠実な
入力応答微分、意味のある制度発見、設計者自身の改善は研究課題として残る。
非スケールの未達を「seedを増やせば済む」と扱わず、別々の次課題として記録する。

## 前段階 — 目的条件付きの生成・実行・改訂 v5（履歴）

[全体目標との対応表](milestones/2026-11-01-objective-conditioned-design-v5.md)と
[最新STATUS](STATUS.md)を参照。元の研究者世界を包含したまま、lossから自由な
コード・protocol・配線を設計し、実測損失を次の設計へ戻す。人数・seed・期間の
拡大はこの能力を代替しない。暗黙の品質・参加率・公平性gateも追加しない。

ローカルQwenの広い同時生成はv5の3試行でも技術的に失敗したため、元の失敗を
残したまま、Codex制度設計者／固定Qwen研究者という別pilotを小予算で完了した。
5世界・285応答、実損失`[-1,-3,-3]`と`[.70,.45,.45]`、2機構/protocolへの同点改訂まで
独立監査した。[結果と限界](results/native-external-objectives-v5-a1.md)を参照。
生成済みコードとグラフは、採用されなかった候補も結果と一緒に保存する。
新しい実作用として、任意制度が選んだ資源移転を本物の研究者・台帳へ渡す
native capabilityも追加した。これは既存資源の保存的な移転であり、自由な
資金創造・新actor・任意の研究過程の完成ではない。

次の非スケール優先順位は次のとおり。

1. 研究・投稿・資金の`_frame`内に隠れた依存を、元世界との同値性を保ちながら
   一つずつtyped input/outputにする。構文上の新nodeではなく、新制度が実際の
   科学活動を変更できる意味上の接続を広げる。
2. 外側の実測loss→再設計を、既存の同一社会migrationへ接続する。候補の評価、
   明示的な採用、履歴保存、将来の研究者行動の変化を別々に検証する。
3. 微分は、有限の既存制度を選ぶlogitsだけでなく、制度内の演算や明示的な
   code/edge選択へ対象を広げる。score-function法とpathwise法を混同せず、
   frozen LLMでも入力応答は変わることを含めて局所的な忠実性を検証する。
4. 英語ゲームUIで、同じ実データのloss別探索経路・コード・graph差分を見せる。
   明示的な採用操作と過去証拠の不変性を両立する。フルゲーム体験の完成と、
   有用なゲーム風UIの成立は別の到達点とする。
5. 長期的な再帰的自己改善では、制度が変わることだけでなく、設計者の戦略自体が
   変わって次の設計成果を改善することを検証する。現時点で達成済みとは扱わない。

## 前段階 — 元の研究者世界での非スケール統合 v4（履歴）

[能力・実証・未達の現在地](milestones/2026-11-01-non-scale-integration-v4.md)を参照。
制度コード・protocol・配線の生成API、元世界の実損失を使う分布勾配、視覚的編集、
同じ社会の年境界での制度変更と永続化・cold restartを実装した。
ゲームUIは明示LossSpec/目標/試行上限のcontractと実測結果だけの履歴を持つ。
一方、Qwenの制度/配線同時生成は2試行とも技術的失敗であり、有効な新制度の
自動発明は未達。元世界データ由来の近似勾配はnative secantと一致せず、
有限4制度の確率最適化をその解決や世界全体の逆伝播とは扱わない。
次は自由な制度・typed boundary記述、忠実な世界応答表現、目的に基づく継続的採用、
UIからの明示的migrationを詰める。seed/人数/期間拡大は引き続き後回しにする。

## 以前の設計段階 — Whole-System Design Lab v0〜v1（履歴）

Decision 0026で、制度の実装だけでなく配線・protocol・順序を同時編集するpatchと、
元の研究者世界で実行する永続的な外側ループを追加した。同じnative lossで連続な
設計変数の提案分布を更新するscore-function勾配推定も、小規模に実行できる入口を
持つ。ただし世界全体のautogradではない。研究者世界内からの制度改訂提案をjournalへ
記録し、別のnative世界で評価する最初のbridgeもQAした。同じ社会の連続運営と実行中
state migrationは当時未実装だったがv4で明示的な永続APIを追加した。
改善プロセス自体の再帰的改善は現在も未達である。

Decision 0025により、ここでいう小規模化は人数・期間を小さくすることであり、
研究活動を数値属性の別世界に置き換えることではない。元の研究者世界も単純すぎる
ため、それを包含した上で拡張する。NativeScienceKernelは元の実行過程をグラフの
一構成として実行し、新コード/新protocolから実際の研究者入力と出版状態へ接続する。
元の6年実行との互換性、接続/遅延の効果、査読の除去と実装置換、再開をQAした。
研究者世界全体の微分可能化、任意actorの行動、自由なイベント進行は未完であり、
数値miniatureの成功とは区別する。

少数agent、1〜2年、1〜2 development seeds、少数候補で、次を同じend-to-end workflowに接続する。

1. `ObjectiveSpec`から`LossSpec`とheld-out diagnosticsを生成する。
2. evaluationに加えてpublication、funding、government、communicationのうち少なくとも2機構を含む小さな構造grammarを凍結する。
3. nodeの有無・実装置換と、edgeまたはschedule/latencyをブラックボックス探索する。
4. 同じ設計対象に対する微分可能relaxationから候補を射影する。
5. 両方の候補を同じ離散`SystemSpec` validatorとmodel-backed simulatorで外側評価する。
6. objective、proposal lineage、graph差分、world events、observed lossを同じcanonical artifactsからゲームで表示する。

この段階ではoptimizer superiorityや統計的安定性を主張しない。統合sliceの完了後にseed、optimizer、候補予算、population、期間を一軸ずつ増やす。

Decision 0022により、項目3と4は別々の研究対象ではなく二軸で扱う。何を動かすかは
parameter ⊂ mechanism implementation ⊂ node/edge structure と段階化し、どう探すかは
black-box / differentiable surrogate / hybrid とする。三つの自由度と三手法を同じ
projection・外側評価へ通すsynthetic common boundaryは実装済み。schedule/latencyの
relaxationとmodel-backed outer executionは未完である。

続くDecision 0023で、生成可能な機構DSLと新しい数値world backendを実装した。
ここでは新規AST/custom node生成、graph/latency/order変更、world全体の連続緩和に
対するbackpropagation、離散評価、canonical viewを2目的・2development worldsで
実行・再現した。Qwenは機構規則と初期特徴を生成する。この数値sliceの完了と、
元のlongitudinal Qwen-agent simulatorへの任意機構接続・微分可能化は区別する。
後者とObjectiveSpecの統合は次の課題であり、scale-upより先に進める。

Decision 0024では固定ASTだけにとどめず、LLMがPython実装コード・JSON内部状態・
新しい成果物の出力schemaを生成し、隔離実行してproduction PaperTrackerへ接続する
経路を追加した。任意コードが実行できることと、意味のある新制度が動くこと、
研究者の反応まで組み込めること、全体を微分できることは別の検証対象である。
[スケール以外の制限一覧](audits/non-scale-limitations-v1.md)を次の実装優先順位の
基準とし、producer/consumerの同時生成と新protocolの因果的作用を次に確認する。

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

