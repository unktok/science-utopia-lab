# Metric-Conditioned Optimization v1.1: provenance-safe trajectory reuse

Status: implementation contract; no change to v1 LossSpecs, seed firewall, or
winner rule.

V1.1 allows the two non-canonical arms to reuse the canonical arm's first
three byte-identical proposals. It shares a realized simulator trajectory, not
a loss value or aggregate. Every arm independently evaluates that trajectory
under its own frozen `LossSpec`.

## Identity and admission

An execution identity contains the producer source commit, normalized producer
command, design JSON and id, fidelity, seed role, seed, model identity, backend,
and declared model/dataset revisions. Normalization removes only logical
`run_id` and output-root values. Campaign id, LossSpec, and optimizer identity
do not enter the producer identity.

Adoption is allowed only when:

- source and target execution-identity hashes match;
- the source is terminal `complete`, has at least one real attempt, and has a
  completed scheduler-attempt record;
- the source is itself executed rather than adopted;
- its native manifest is complete and agrees on run id, source commit, seed,
  model, backend, and any declared revisions;
- native integrity and funding-trace admission passes;
- the target is still `planned` with `attempt=0`.

The target transition and `artifact_links` insertion are one SQLite
transaction. Repeating the exact adoption is idempotent. A different source or
an attempted target is rejected.

## Immutable physical bundle

The source receipt enumerates every regular raw file below its `docs`,
`checkpoints`, simulator `logs`, and harness `registry-logs` run directories
with size and SHA-256. Symlinks are rejected. The receipt and arm-specific
`objective_evaluation.json` are derived metadata and excluded from the sealed
raw set.

Resolution verifies the receipt hash, internal identity and attempt-provenance
hashes, and the exact current raw-file set. Changed, removed, or additional raw
files make the logical run unusable. Evaluators read the physical source path
but write derived evaluation only below the logical target path.

## Controller workflow

After `init` and `suggest-initial`, execute all nine initial design-seed jobs in
one canonical arm. Then run:

```bash
python -m utopia.optimization.metric_conditioned_study \
  --study research/specs/metric-conditioned-optimization-study-v1-1.json \
  adopt-initial \
  --canonical-arm metric-conditioned-participation-review-v1-1
```

The command seals the nine physical artifacts and creates 18 logical adoption
links. Each arm then runs `observe`; adaptive proposals can diverge from the
arm-specific loss observations and execute normally.

Reports retain logical run ids and expose physical lineage, bundle hashes, and
separate `executed`/`adopted` counts. An adopted trajectory is never counted as
an independent simulator execution.

## Version boundary

This controller changes source commit and campaign revision. It must be used
from a newly initialized clean worktree. It cannot be installed into or used to
rewrite the frozen v1 campaign at commit `9f9868d`.
