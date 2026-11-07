# Research index

This is a navigation page, not a chronological experiment transcript.
Read [purpose](../RESEARCH.md), then [current status](STATUS.md).
Historical documents retain their paths and source identities.

## Active orientation

- [Autonomous submission goal](publication/submission-goal.md): milestones and evidence-based completion criteria.
- [Fixed objective/design-freedom study](protocols/campaigns/native-design-freedom-v2.md):
  search finished, selected-policy evaluation underway; see current STATUS.
  [Source-specific software QA](results/native-design-freedom-v2-verification.json)
  and the later [audit-order component diagnostic](results/native-design-freedom-v2-audit-order-diagnostic-v1.json)
  have different scopes. The [order-only correction verification](results/native-design-freedom-v2-audit-order-verification-v1.json)
  records74 tests/two exact component replays; full closed-study audits remain pending.
- [Program map](program-map.md): original goals, capabilities and evidence gaps.
- [Roadmap](roadmap.md): what to do next and why.
- [Submission research plan](publication/plan.md), [comparison contract](publication/benchmark-contract-v1.md),
  [initial related work](publication/related-work.md).
- [Reproducible four-study evidence inventory](results/publication-evidence-inventory-v1.json).
- [Feedback control implementation](components/native-feedback-control-v1.md) and
  [prospective finite comparison](protocols/campaigns/native-feedback-comparison-v1-a1.md).
- [Research charter](charter.md): original motivation and explicit principles.
- [System abstraction](system-model.md), [optimization](optimization.md).
- [Software/research workflow](../docs/research-workflow.md).
- [Explicit paper-rebuild subset](../docs/paper-rebuild-bundle.md):12 paths,
  tested local offline build; not final-result, anonymous or numerical reproduction.

## Latest completed evidence

- [S1 strong rule baselines](results/native-benchmark-controls-v2-a1.md): all eight
  complete, original-source audited twice; developer controls, not automatic invention.
- [S1 fixed-record relaxation](results/native-controls-selection-relaxation-v1.json):
  read-only loss algebra, not a dynamic-policy optimum or new search outcome.
- [S1 observed scientist tokens](results/native-controls-token-costs-v1.json):
  source-bound response usage, not total project compute or fresh GPU operations.
- [V1 same-source feedback comparison](results/native-feedback-comparison-v1-a1.md):
  all eight slots, four runtime failures, initial all-accept improvement, no measured G1 gain.
- [V1 compact audit](results/native-feedback-comparison-v1-a1.json) and
  [short working manuscript](../paper/submission.tex).
- [V45 compact audit](results/native-warmstart-v45-a1.json).
- [V45 actual outcomes, error diagnosis and separate fixes](logbook/2026-11-07-native-warmstart-v45.md).
- [V45 prospective two-slot protocol](protocols/campaigns/native-warmstart-v45-a1.md).
- [Search-design review](search-design-review.md) and
  [decision0029](decisions/0029-search-review-before-more-autonomous-authoring.md).
- [V13 nested free-institution results](results/native-nested-search-v13-a1.md):
  external-author provenance, not local-Qwen invention.
- [Earlier parameter/held-out study](../paper/figures/metric-conditioned/README.md):
  distinct design freedom and experiment binding.

## Stable technical entry points

| Capability | Entry |
| --- | --- |
| Whole scientific system | [SystemSpec](components/system-spec-graph-v1.md), [native kernel](components/native-science-kernel-v1.md) |
| Actors, artifacts and processes | [Open native domain](components/native-open-domain-v7.md), [process execution](components/native-process-execution-v7.md) |
| Free source and structure | [Scoped authoring](components/native-scoped-region-authoring-v5.md), [adaptive search](components/native-adaptive-open-search-v7.md) |
| Search methods | [Black-box ask/tell](optimizers/blackbox-ask-tell-v1.md), [operational hybrid gradients](components/native-operational-hybrid-gradients-v7.md) |
| Loss and evaluation | [Objective index](objectives/README.md), [metrics](metrics/README.md) |
| Replay and UI | [Canonical replay](canonical-event-replay-v1.md), [English game](../game-ui-v2/README.md) |

## Record organization

- `protocols/campaigns/`: prospective experiment definitions.
- `results/`: compact data and interpreted results; failures remain visible.
- `logbook/`: chronological observations and work notes.
- `decisions/`: durable decisions and supersession.
- `literature/`: source-linked literature notes.
- `components/`: implementation contracts and their limits.

## Historical navigation

The [complete pre-reset index](index-history-through-v45.md) preserves all507
lines of links as of5ae3c5c. The
[pre-reset status ledger](status-history-through-v45.md) preserves all2619
lines of recorded snapshots. The later348-line status is preserved byte-for-byte
in the [V2 through70 snapshot](status-history-2026-11-07-v2-through70.md);
current STATUS records its SHA256. Older statements saying a process is running are
historical observations, not live heartbeats.

Do not move/delete old records or frozen worktrees to shorten this index.
