# ADR-0011: Version future objective candidates before implementing LossSpecs

- Status: accepted
- Date: 2026-10-28

## Context

Metric-conditioned optimization v1.1 deliberately tests three narrow proxy
LossSpecs. The next campaign needs a larger objective research space informed
by science-of-science and the local `ai-scientist-survey`, without retroactively
changing the frozen experiment or presenting available simulator columns as
validated measures of scientific value.

Construct proposals had been described in literature notes, but not in a
machine-checkable object that tied each construct to its observable,
aggregation, direction, Goodhart risk, required simulator fields, held-out
boundary, feasibility, and sources.

## Decision

Adopt `scienceutopia.objective-catalog.v1` as a future-campaign planning object.
It is separate from executable `LossSpec`, `EvaluationMetricSpec`, technical
validity, and promotion policy.

The catalog must:

1. include epistemic progress, novelty, robustness, diversity, participation,
   efficiency, and public value;
2. pin local research sources by repository commit, path, and locator;
3. label native, derivable, and missing simulator fields;
4. fail closed on unresolved citations, held-out leakage, frozen LossSpec ID
   reuse, and any composition strategy marked as a universal default;
5. keep all candidate loss families future-only until separately
   preregistered.

No single composite is endorsed. Separate-arm studies, Pareto comparison,
temporary scalarization, and explicit constraints remain alternative designs
whose normative assumptions must be reported.

## Consequences

- The active v1.1 LossSpecs and seeds do not change.
- A native output being measurable is no longer enough to call it an objective
  candidate; construct validity and the missing semantic fields are explicit.
- Proxies exposed to search require a new evidence split. Current held-out
  diagnostics cannot silently become optimizer inputs.
- Several scientifically important constructs remain intentionally
  unimplementable until claim, verification, branch, mission, and stakeholder
  models exist.
- Future objective proposals become reviewable in diffs and testable in CI.

## Evidence

- [`../literature/science-of-science-objectives.md`](../literature/science-of-science-objectives.md)
- [`../literature/ai-scientist-survey-objectives.md`](../literature/ai-scientist-survey-objectives.md)
- [`../objectives/catalog/objective-catalog-v1.md`](../objectives/catalog/objective-catalog-v1.md)
- `t46/ai-scientist-survey` commit
  `02b437b854e73f1bd8a274399e56167ee05a4400`, with source paths and locators
  embedded in the catalog.
