# Decision 0012: Seal a development-only completion report before held-out planning

- Status: accepted implementation boundary
- Date: 2026-10-28
- Applies to: metric-conditioned optimization v1.1

## Context

The final paper slice in Decision 0010 intentionally requires completed
held-out evaluation. A distinct evidence boundary is needed immediately after
the 45 development runs finish and all three winners are frozen. At that point
we need to answer which system each LossSpec selected, audit physical execution
versus provenance-safe artifact adoption, and inspect development-seed
dispersion without opening or planning the protected split.

This is not an early substitute for the held-out result. Cross-scoring a
development candidate under all three LossSpecs is post-search diagnostic
analysis on optimization evidence. It cannot estimate generalization.

## Decision

Adopt `scienceutopia.metric-conditioned-optimization-completion.v1` as the
machine-readable pre-held-out report. One fail-closed command reads the study
manifest, three frozen campaign states/snapshots/read-only registries, registry
reports, and simultaneous winner freeze. It refuses to run unless:

1. the contract is exactly three arms, five observed candidates per arm, and
   three distinct development seeds per candidate;
2. all 45 logical runs are complete and have exactly one verified execution
   mode: physical execution with a complete attempt, or artifact adoption with
   no execution attempt and complete link provenance;
3. all snapshots share one clean pinned source commit and the LossSpec hashes
   match the freeze;
4. every winner equals the recomputed minimum under its arm LossSpec;
5. development and held-out seeds are disjoint, no held-out seed occurs in an
   arm registry, the freeze records every held-out seed as unconsumed, and the
   held-out registry, snapshot, and cross-evaluation report do not exist; and
6. all 15 candidate systems can be scored under all three frozen LossSpecs.

The report contains arm trajectories, per-seed values, population dispersion,
exact $3^3$ development-seed bootstrap intervals, executed/adopted provenance,
the frozen-winner 3-by-3 cross-objective matrix, all-candidate rankings,
Kendall tau-b association, and observed top-rank changes. The schema is
versioned at
`research/specs/metric-conditioned-optimization-completion-v1.schema.json`.

## Interpretation boundary

Every artifact says **development split only; held-out unused**. Figure titles
are conditional: rank reversal or distinct-system selection is claimed only
when present in the report. Topic entropy and review burden remain contrastive
proxies, not normative recommendations. No universal winner is produced.

The command performs no simulation, optimizer update, winner refreeze,
held-out planning, or policy selection. Registries are opened with SQLite
`mode=ro`, hashed before and after reading, and the output package is published
through one atomic rename. Synthetic fixtures are visibly watermarked.

## Relationship to the final paper slice

This report is the optimization-stage handoff and progress graphic. Decision
0010 remains the publication gate after common held-out evaluation. Its
generalization, paired effects, gaming diagnostics, and final manuscript
fragments must not be inferred from this development-only report.

## Consequences

- Completion of the expensive search becomes reviewable before any held-out
  seed is registered.
- Adopted logical observations are visible without double-counting them as
  physical simulations.
- The same 15 observed systems can be compared under every objective while
  retaining the distinction between objective-specific frozen winners and a
  post-hoc union-of-candidates ranking.
- A partial campaign, stale freeze, missing objective evaluation, ambiguous
  provenance, or any sign of held-out planning fails closed.
