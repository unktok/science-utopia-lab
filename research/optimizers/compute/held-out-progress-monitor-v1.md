# Held-out progress monitor v1

## Purpose

Provide a read-only operational view of a running held-out evaluation without
turning incomplete evidence into a result. The monitor reports run states,
technical failures, completed-run durations, a median-rate ETA, and whether the
registry is ready for the separately defined report command.

It does not read model outputs, measurements, losses, metric profiles,
optimizer observations, or promotion decisions. It never writes to the run
registry. SQLite is opened in read-only mode and copied into memory before the
projection is queried.

## Command

```bash
.venv/bin/python scripts/monitor_metric_conditioned_evaluation.py \
  --registry <study-root>/held-out-evaluation/runs.sqlite3 \
  --expected-runs 15
```

The JSON output uses schema `scienceutopia.held-out-progress.v1` and includes a
content hash. Exit status `2` means the orchestration appears stalled: either a
running row exceeded the configured stale threshold or retryable/planned work
exists without an active row. Technical failures remain distinct from a poor
simulated outcome.

## Completion gate

`gate.ready_for_report` becomes true only when no row is planned or running and
no retryable technical failure remains. `gate.next_action` then names
`report-evaluation`; the monitor does not execute that command itself. This
keeps monitoring, scientific evaluation, and report generation as separate
auditable operations.
