# Decision 0015: Compare frozen winners before opening held-out evaluation

- Status: accepted implementation boundary
- Date: 2026-10-28
- Applies to: Metric-Conditioned Optimization Study v1.1

## Context

Decision 0012 produces the authoritative optimization-completion report after
all 45 logical development runs and simultaneous winner freeze. It recomputes
every observed candidate under all three LossSpecs and proves that held-out
planning has not started. The project also needs a compact, paper-ready answer
to the core optimization question: which system did each objective select,
and how do those three frozen systems trade off under the other two objectives?

The compact comparison must not become a second optimizer, refreeze winners,
open held-out artifacts, or imply that development-seed behavior generalizes.

## Decision

Add `scienceutopia.metric-conditioned-post-optimization-comparison.v1` as a
focused read-only projection of the sealed Decision 0012 report. Its only
inputs are:

1. one complete `metric-conditioned-optimization-completion.v1` JSON document;
2. exactly three explicit `arm=winner-system-fingerprint` assignments.

The fingerprints must be lowercase SHA-256 values and match both the frozen
winner record and the winner candidate in the completion report. The source
report must retain its development-only, held-out-unconsumed boundary. No
campaign registry, simulator output, held-out registry, held-out snapshot, or
held-out cross-evaluation path is an input to this command.

The Decision 0012 builder remains responsible for re-evaluating candidates
under all three LossSpecs from native development evaluations. This slice
independently checks that the frozen 3-by-3 matrix equals the winner candidate
evidence, that every cell has the same three development seeds, and that seed
means and population dispersion recompute. It never launches another
simulation or evaluation run.

## Analysis outputs

The report retains:

- the three frozen fingerprints and selection objectives;
- all nine aggregate loss cells with seed values, population SD, and exact
  three-seed bootstrap intervals;
- within-objective ranks and top-system rank reversal;
- conditional Pareto front and pairwise dominance;
- objective-by-objective signed deltas for all three winner pairs;
- executed versus provenance-safe adopted logical runs;
- all physical attempt status counts, including non-complete attempts;
- physical attempt wall time; and
- source commit, winner-freeze hash, manifest hash, controlled-contract hashes,
  and campaign artifact hashes.

Pareto dominance compares losses only within the same LossSpec. Raw units from
different LossSpecs are never added into a composite. The visualization colors
the matrix by within-objective rank and uses per-objective normalized regret
only for its parallel-coordinate profile.

## Authorization and held-out firewall

Every output records:

- `source_split: development_only`;
- `held_out_artifacts_read: false`;
- `held_out_runs_created: false`;
- `held_out_seeds_consumed: false`;
- `candidate_selection: false`;
- `optimization_update: false`; and
- `universal_winner_selection: false`.

The CLI deliberately has no held-out path, seed, evaluator, or simulation
option. It reads only the completion JSON and writes a new atomic output
directory. Protected seed identifiers are not propagated into the focused
report. A synthetic source is visibly watermarked and is refused under the
paper result directory.

## Interpretation boundary

The Pareto front is conditional on three specific frozen systems and three
declared LossSpecs. It is not a global Pareto front over the design space. A
rank reversal demonstrates metric-conditioned selection on development worlds,
not held-out generalization or real-world science-policy superiority. Topic
entropy and review burden remain contrastive probes, not normative targets.

## Consequences

- The objective-conditioned result becomes reviewable immediately after
  optimization completion without spending the protected split.
- Winner identity is an explicit input rather than inferred from file order.
- Seed uncertainty, runtime failures, and adopted provenance remain visible in
  the paper-ready view.
- Final generalization, gaming, and common evaluation metrics still require the
  separate post-held-out Decision 0010 pipeline.
