# Seed-replicated experiment harness

## Purpose

目的関数の内容から独立して、制度候補を複数の独立worldで実行し、計画、失敗、checkpoint再開、完了を追跡する。adaptive optimizerを導入する前に、random/Sobol baselineを同じregistry上で動かす。

## Study specification

最初の仕様は [`specs/study-v0-smoke.json`](specs/study-v0-smoke.json)。以下を明示する。

- design-spaceとbaseline design
- Metric Constitutionとその内容hash
- sampler種別、候補数、sampler seed
- exploration / selection / confirmationの互いに素なseed集合
- model、backend、endpoint、batch size
- output root、cache、最大attempt数

study specification、design-space、Metric Constitution内容hashがstudy revisionになる。`study-snapshot.json`にはconstitution本体も固定する。出力は次へ分離される。

```text
outputs/optimization/<study-id>/<study-revision>/
  study-snapshot.json
  registry.sqlite3
  registry-report.json
  registry-logs/<run-id>/attempt-<n>.log
  docs/<run-id>/...
  checkpoints/<run-id>/...
  logs/<run-id>/...
```

## Commands

計画だけを作り、LLM runは開始しない。

```bash
.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v0-smoke.json \
  plan --fidelity smoke --seed-role exploration
```

デフォルトではbaseline 1候補 + Sobol 4候補をexploration seed 2個で組み合わせ、10 runを計画する。同じplanを再実行しても重複しない。

計画の状態を見る。

```bash
.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v0-smoke.json status
```

一件だけ実行する。

```bash
.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v0-smoke.json run --limit 1
```

特定のbaselineまたは候補を選ぶ場合は `run --run-id <planned-run-id>` を使う。

集計を更新する。

```bash
.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v0-smoke.json report
```

固定した二つの5-seed campaignをprovenance監査付きでpaired比較する。

```bash
.venv/bin/python -m utopia.optimization.paired_comparison \
  --baseline-root outputs/optimization/longitudinal-comparison-baseline-v1/fb38800d92 \
  --candidate-root outputs/optimization/first-candidate-funding-slots-v2/5e2b4d9e2f \
  --json-output research/results/first-paired-system-comparison-v1.json \
  --markdown-output research/runs/2026-10-26-first-paired-system-comparison.generated.md
```

確認段階では、別registryへ未使用confirmation seedsだけを計画する。

```bash
.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v6-confirmation-baseline.json \
  plan --fidelity longitudinal --seed-role confirmation

.venv/bin/python -m utopia.optimization.harness \
  --study research/specs/study-v6-confirmation-candidate.json \
  plan --fidelity longitudinal --seed-role confirmation
```

両方が完走した後、`paired_comparison --seed-role confirmation`で比較する。
confirmation policy v1ではcapability failureをrun除外理由にせず、pass/failの
制度outcome distributionとpaired transitionとして保持する。技術的admissibility
failureだけがformal comparisonを未完了にする。

この比較器はseedをexact joinし、design差分が許可された一変数だけであること、
source/model/dataset/evaluator/embedding/configが一致すること、全runのintegrity、
funding reliability、測定完全性を検査する。過去のexploration v1 reportでは、
capability infeasibleなrunを除外せずformal statusを`incomplete`としてpaired
diagnosticを保持する。confirmation policyを持つv2 reportでは上記の事前登録どおり、
capability failureをformal completenessではなく制度outcome gateで扱う。

## Failure and resume semantics

- run IDはstudy revision、fidelity、seed role、design hash、seedから決定的に作る。
- harness開始時に`running`のまま残った行を検査する。親だけが異常終了して子processが
  run leaseを保持している場合はregistryを変更せず起動を拒否する。子も終了済みなら
  その行を`failed`へ戻す。
- attempt上限内のfailed runは同じrun IDと出力先で再実行する。
- `--always_rerun`は付けないため、ScienceUtopiaは利用可能な年次checkpointから再開する。
- process exit 0だけで成功にせず、run manifestの`status=complete`も要求する。
- integrity reportとfunding application conservation traceの全checkがpassであることも要求する。
- worker 1ではattemptごとのcombined stdout/stderrを保存し、並列時はrunごとの
  stdout/stderrへ分離する。
- final run状態とは別にattempt tableを保持し、復旧後も一時的失敗、attempt単位の失敗率、消費時間を失わない。
- `run --workers N`は一台のOllama endpointへ最大N個の独立runを投入する。
  `N>1`ではwarm RAG cacheをrunごとのprivate cacheへseedし、mutable cacheと出力を
  分離する。model capacity上の実効速度は保証しないため1/2/4 workersで実測する。
  詳細は [`parallel-harness-v1.md`](parallel-harness-v1.md) を参照する。

## Report boundary

registry reportはwall-clock、failure rate、paper/review/active researcher/resourceに加え、資金申請のtarget、semantic retry、request error、drop、decision、allocationの分布を出す。これらは運用・活動診断であり、最適化目的ではない。Science of Science調査を反映したobjective evaluatorは別moduleとして接続する。

objective evaluatorは、固定されたMetric Constitutionからhard constraint、capability state、commitment-specific objective vectorをrunごとに生成する。v1で実装するmetricは`integrity-checks-pass`、`active-researcher-fraction`、`topic-entropy`、`review-burden-per-active-researcher`である。結果は各runの`objective_evaluation.json`とaggregate reportの`design_objective_readiness`へ保存する。

現在の成果物はaggregate metricを計算できるが、protected sliceであるlow-resource researchersのmembershipとreview actionを結果から独立に結合できない。end-of-run funding quantileからsliceを作るとoutcome-conditioned selectionになるため採用しない。sliceは`unknown`とし、aggregateの参加率がfloorを超えてもcapability stateをpassにしない。また、各objective metric cardが要求するminimum 5 runsをdesign単位で満たすまで`authorized_for_ranking=false`とする。

measurement-complete v1では、`balanced_two_band` population profileが開始時に固定したresource bandを`agent_year`へ、個々の査読行為を`review_action`へ記録する。evaluator 1.1は両tableをagent IDで結合し、slice supportとaction総数のreconciliationを検査する。新しいcampaignは`research/specs/study-v1-smoke.json`で定義し、v0 artifactを異なるevaluator versionで再評価しない。

v1 revision `1cc1b68161` のbaseline seed 101でend-to-end validationを完了した。6 review actionsは6 unique event IDsとしてcheckpoint aggregateと一致し、measurement gapは0になった。aggregate burden 0.6に対してlow-resource slice burdenは1.2で、平均では隠れる負担集中を検出した。runはfeasibleだが1/5 seedsのためranking authorizationはfalseである。

同revisionのbaseline exploration seeds 101, 103, 107, 109, 113はすべて
first attemptで完走した。全runがfeasibleかつmeasurement gap 0で、最低5反復を
満たしたためbaselineのranking authorization gateはopenになった。aggregate
review burdenはmean 0.78、median 0.60、range 0.30–1.50、low-resource sliceは
mean 0.76、median 1.00、range 0.00–1.20だった。slice−aggregate差は
−0.50から+0.60まで符号反転し、pooled meanだけでは負担集中を判断できない。
参加率はaggregate/sliceとも全run 1.0であり、1年smokeのceiling effectとして
扱う。

funding生成は260 attempts中134 semantic-invalid（51.5%）、6 terminal drops、
request error 0だった。trace conservationは全runでpassしたが、この不正率は
cross-design comparisonのengineering reliability gateを通さない。詳細は
[`runs/2026-10-25-v1-baseline-five-seed.md`](runs/2026-10-25-v1-baseline-five-seed.md)
を参照する。`authorized_for_ranking=true`は反復・測定・制約上の比較参加資格で
あり、他design未実行の現時点では順位や最適性を意味しない。

## Engineering reliability gate

`study-v2-smoke.json`から、funding proposal pipelineを目的ベクトルと分離した
versioned gateで検査する。per-runのsemantic-invalid、sanitized reference、
request error、terminal dropを分母付きrateとして計算し、policy ID/version/hash
とともにreportへ保存する。最低target数に届かないrunは
`insufficient_evidence`、閾値違反は`fail`となり、どちらも`quarantine`される。
run自体はdiagnostic artifactとしてcompleteになり得るが、design-levelの
`authorized_for_ranking`はfalseになる。

このgateは良い制度を選ぶ指標ではない。シミュレータの故障やLLM出力不良を
制度効果として最適化しないためのadmissibility conditionである。v1 artifactへ
遡及適用せず、trace schema v2と新しいstudy revisionだけで使用する。設計根拠と
閾値は[`funding-reliability.md`](funding-reliability.md)に記録する。

## Longitudinal measurement gate

`study-v3-longitudinal-pilot.json`は制度候補を生成しないbaseline-only calibration
を表現する。`sampler.count=0`は`include_baseline=true`の場合だけ許可され、未実行の
候補designをregistryへ混ぜない。fidelity名はdesign-spaceで拡張でき、各fidelityが
`experiment_stage`を明示するため、`longitudinal`のような研究目的に即した名前を
使える。

4年・10人のlongitudinal fidelityにはversioned participation measurement gateを
適用する。`agent_year`から年別active数、最終aggregate参加率、開始時に固定した
low-resource slice参加率を再構成し、期間・support・時系列変化・floor/ceilingを
検査する。pass以外は`recalibrate_fidelity`となり、objective値が良くても
`authorized_for_ranking`を閉じる。これは制度性能ではなく、主要目的を測れる実験
条件かどうかの検査である。事前基準と選択根拠は
[`longitudinal-fidelity.md`](longitudinal-fidelity.md)に固定する。

## First end-to-end validation

2026-10-24にbaseline design / exploration seed 101を実モデルで完走した。registry上の1 attempt、native manifest、checkpoint、integrity report、attempt log、aggregate reportが同じ決定的run IDへ結びつくことを確認した。実行時間は約23分44秒で、report生成時点では1 complete / 9 plannedである。

詳細とevidence hashは [`runs/2026-10-24-harness-baseline-seed101.md`](runs/2026-10-24-harness-baseline-seed101.md) に固定した。これはharnessの実行可能性を示すだけで、複数seed推定や制度の優劣を示さない。

## Constitution-bound revision

Metric Constitution v1をstudyの必須入力にし、schema、format、ID重複、全cross-referenceをplan前に検証する。constitutionのcanonical SHA-256をrevisionへ含めるため、目的・評価器・decision policyの変更は既存campaignへ混入しない。

最初のconstitution-bound planはrevision `6fcbf8bae1`で、baseline + Sobol 4 designs × exploration 2 seedsの10 runである。全件plannedであり、LLM runはまだ開始していない。旧revision `eadef0bb5a`の1 complete / 9 plannedとは別campaignとして保持する。

各runでは資金申請をtrace IDで追跡し、generation request error、semantic invalid、`submit=false`、terminal drop、evaluation、decision、allocationを区別する。説明不能なattritionはintegrity failureとなり、exit code 0でもregistry上のcompleteにはしない。

