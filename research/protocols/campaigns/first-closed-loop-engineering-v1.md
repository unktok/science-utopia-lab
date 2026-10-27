# First closed-loop engineering campaign v1

Status: prospective engineering protocol; simulator execution pending

## Purpose and claim boundary

This campaign tests whether Science Utopia can complete a persistent,
result-dependent black-box optimization loop over executable whole-system
designs. It is an engineering demonstration, not evidence that its selected
system is good science policy.

The mutable object is a nested `SystemSpec`. Its current adapter is deliberately
restricted to the legacy fixed topology and eight parameters. Peer review is
one mechanism in that graph, not the optimization target by itself.

## Frozen machine-readable inputs

| Role | Artifact |
|---|---|
| campaign | `research/specs/first-closed-loop-engineering-v1.json` |
| campaign schema | `research/specs/closed-loop-campaign-v1.schema.json` |
| loss | `research/objectives/losses/engineering-continuity-demo-v1.json` |
| loss schema | `research/specs/loss-spec-v1.schema.json` |
| execution template | `research/specs/study-v2-smoke.json` |
| design space | `research/specs/design-space-v1.json` |

The protocol must be merged and tagged before model-backed execution. A changed
input or source commit produces a different campaign revision and output root.
Initialization refuses a dirty worktree and records the exact commit in the
immutable snapshot.

## Search and budget

- optimizer: deterministic `AdaptiveRandomSearch`;
- optimizer seed: `20261027`;
- initial batch: two independent candidates;
- adaptive batch: one mutation around the lower-loss completed candidate;
- total budget: three suggestions;
- optimization seeds per suggestion: `503, 509, 521`;
- reserved held-out seeds: `523, 541, 547`;
- fidelity: one-year `smoke`;
- local workers: one, because the measured single-Ollama workers 1/2/4 benchmark
  showed no material throughput gain at four workers.

The stopping rule is budget exhaustion after the third suggestion is observed.
The controller does not run the held-out seeds.

## Engineering loss

For each technically usable run:

```text
run_loss = 1
           - active_researcher_fraction
           + 0.05 × review_burden_per_active_researcher
```

Across the three optimization seeds:

```text
loss = mean(run_loss) + 0.25 × population_sd(run_loss)
```

Lower is better. All three runs are required. A missing metric or exhausted
failed run makes the suggestion invalid; it does not receive a fabricated large
loss. This formula is only an engineering signal. It is not a validated
scientific-value, social-welfare, truth, novelty, or public-benefit objective.

## Technical validity

The existing harness checks native completion manifests, integrity reports,
funding application conservation, retries, and isolated run outputs before a
run becomes `complete`. Only completed runs with measured loss inputs enter the
loss aggregation. Historical capability or protected-slice promotion vetoes are
not optimizer constraints in this campaign.

## Persistent state flow

```text
ask initial SystemSpecs
  → persist campaign-state.json
  → register 2 designs × 3 seeds in runs.sqlite3
  → execute and validate
  → evaluate LossSpec
  → tell both observations
  → ask one mutation based on the lower-loss observation ID
  → persist/register/execute/observe/tell
  → stop at budget 3
```

Raw outputs stay under ignored `outputs/optimization/closed-loop/`. Compact
result summaries, hashes, source commit, tag, revision, and interpretation will
be tracked after completion.

## Operator commands

Run only from a clean worktree pinned to the protocol tag:

```bash
.venv/bin/python -m utopia.optimization.closed_loop \
  --campaign research/specs/first-closed-loop-engineering-v1.json init
.venv/bin/python -m utopia.optimization.closed_loop \
  --campaign research/specs/first-closed-loop-engineering-v1.json suggest
.venv/bin/python -m utopia.optimization.closed_loop \
  --campaign research/specs/first-closed-loop-engineering-v1.json run
.venv/bin/python -m utopia.optimization.closed_loop \
  --campaign research/specs/first-closed-loop-engineering-v1.json observe
.venv/bin/python -m utopia.optimization.closed_loop \
  --campaign research/specs/first-closed-loop-engineering-v1.json suggest
```

The final `run` and `observe` complete the third candidate. `status` is safe at
any point. Re-running `init` is idempotent, job registration is idempotent, and
the optimizer state is reconstructed from disk.

## Acceptance criteria

1. Two initial suggestions each reach a complete or explicit invalid terminal
   observation across the frozen seed set.
2. The third suggestion records `phase=adaptive` and
   `based_on_observation_id` equal to the lowest-loss valid initial observation.
3. Controller restart does not alter candidate identity or optimizer history.
4. No held-out evaluation seed appears in the optimization run registry.
5. The result report preserves the engineering-only claim boundary.
