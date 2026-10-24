# Seed-replicated experiment harness

## Purpose

目的関数の内容から独立して、制度候補を複数の独立worldで実行し、計画、失敗、checkpoint再開、完了を追跡する。adaptive optimizerを導入する前に、random/Sobol baselineを同じregistry上で動かす。

## Study specification

最初の仕様は [`specs/study-v0-smoke.json`](specs/study-v0-smoke.json)。以下を明示する。

- design-spaceとbaseline design
- sampler種別、候補数、sampler seed
- exploration / selection / confirmationの互いに素なseed集合
- model、backend、endpoint、batch size
- output root、cache、最大attempt数

study specificationとdesign-space全体のhashがstudy revisionになる。出力は次へ分離される。

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
- attemptごとのcombined stdout/stderrを別ファイルへ保存する。
- final run状態とは別にattempt tableを保持し、復旧後も一時的失敗、attempt単位の失敗率、消費時間を失わない。
- v0 harnessは一台のOllama endpointと共有cacheを使うため逐次実行する。並列化時はcache writerとmodel capacityの分離が別途必要。

## Report boundary

registry reportはwall-clock、failure rate、paper/review/active researcher/resourceの分布だけを出す。これらは運用・活動診断であり、最適化目的ではない。Science of Science調査を反映したobjective evaluatorは別moduleとして接続する。

