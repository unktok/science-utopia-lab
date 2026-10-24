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

## Failure and resume semantics

- run IDはstudy revision、fidelity、seed role、design hash、seedから決定的に作る。
- harness開始時に`running`のまま残った行を`failed`へ戻す。
- attempt上限内のfailed runは同じrun IDと出力先で再実行する。
- `--always_rerun`は付けないため、ScienceUtopiaは利用可能な年次checkpointから再開する。
- process exit 0だけで成功にせず、run manifestの`status=complete`も要求する。
- integrity reportとfunding application conservation traceの全checkがpassであることも要求する。
- attemptごとのcombined stdout/stderrを別ファイルへ保存する。
- final run状態とは別にattempt tableを保持し、復旧後も一時的失敗、attempt単位の失敗率、消費時間を失わない。
- v0 harnessは一台のOllama endpointと共有cacheを使うため逐次実行する。並列化時はcache writerとmodel capacityの分離が別途必要。

## Report boundary

registry reportはwall-clock、failure rate、paper/review/active researcher/resourceに加え、資金申請のtarget、semantic retry、request error、drop、decision、allocationの分布を出す。これらは運用・活動診断であり、最適化目的ではない。Science of Science調査を反映したobjective evaluatorは別moduleとして接続する。

objective evaluatorは、固定されたMetric Constitutionからhard constraint、capability state、commitment-specific objective vectorをrunごとに生成する。v1で実装するmetricは`integrity-checks-pass`、`active-researcher-fraction`、`topic-entropy`、`review-burden-per-active-researcher`である。結果は各runの`objective_evaluation.json`とaggregate reportの`design_objective_readiness`へ保存する。

現在の成果物はaggregate metricを計算できるが、protected sliceであるlow-resource researchersのmembershipとreview actionを結果から独立に結合できない。end-of-run funding quantileからsliceを作るとoutcome-conditioned selectionになるため採用しない。sliceは`unknown`とし、aggregateの参加率がfloorを超えてもcapability stateをpassにしない。また、各objective metric cardが要求するminimum 5 runsをdesign単位で満たすまで`authorized_for_ranking=false`とする。

measurement-complete v1では、`balanced_two_band` population profileが開始時に固定したresource bandを`agent_year`へ、個々の査読行為を`review_action`へ記録する。evaluator 1.1は両tableをagent IDで結合し、slice supportとaction総数のreconciliationを検査する。新しいcampaignは`research/specs/study-v1-smoke.json`で定義し、v0 artifactを異なるevaluator versionで再評価しない。

## First end-to-end validation

2026-10-24にbaseline design / exploration seed 101を実モデルで完走した。registry上の1 attempt、native manifest、checkpoint、integrity report、attempt log、aggregate reportが同じ決定的run IDへ結びつくことを確認した。実行時間は約23分44秒で、report生成時点では1 complete / 9 plannedである。

詳細とevidence hashは [`runs/2026-10-24-harness-baseline-seed101.md`](runs/2026-10-24-harness-baseline-seed101.md) に固定した。これはharnessの実行可能性を示すだけで、複数seed推定や制度の優劣を示さない。

## Constitution-bound revision

Metric Constitution v1をstudyの必須入力にし、schema、format、ID重複、全cross-referenceをplan前に検証する。constitutionのcanonical SHA-256をrevisionへ含めるため、目的・評価器・decision policyの変更は既存campaignへ混入しない。

最初のconstitution-bound planはrevision `6fcbf8bae1`で、baseline + Sobol 4 designs × exploration 2 seedsの10 runである。全件plannedであり、LLM runはまだ開始していない。旧revision `eadef0bb5a`の1 complete / 9 plannedとは別campaignとして保持する。

各runでは資金申請をtrace IDで追跡し、generation request error、semantic invalid、`submit=false`、terminal drop、evaluation、decision、allocationを区別する。説明不能なattritionはintegrity failureとなり、exit code 0でもregistry上のcompleteにはしない。

