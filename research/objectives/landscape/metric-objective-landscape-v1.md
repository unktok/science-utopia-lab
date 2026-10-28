# Metric / Objective Landscape v1

Status: prospective, report-only, for a future campaign.

This landscape asks a different question from the running three-arm study. The
running study intentionally holds everything fixed except a narrow `LossSpec`
and observes which system each metric selects. This document does not repair,
replace, or reinterpret those arms while they run. It audits what each proxy
can mean and defines a broader space for a separately preregistered campaign.

The machine-readable source of record is
[`metric-objective-landscape-v1.json`](metric-objective-landscape-v1.json).
It contains the full metric cards, citations, and graph. The schema and
semantic validator fail closed if the three source hashes change, if the
topic-entropy arm loses its contrastive label, if graph references break, or
if a future optimization candidate lacks a new-campaign boundary.

## What the current three arms measure

| LossSpec | Defensible reading | It does not measure | Characteristic gaming path |
|---|---|---|---|
| participation + review | nominal continuity traded against visible review actions at an experimental exchange rate | meaningful access, authority, welfare, scientific progress | retain agents nominally or suppress/shift evaluation work |
| topic entropy | variety and balance over a fixed topic ontology | disparity, lineage independence, coherence, truth, usefulness | relabel/split topics or produce shallow work in rare labels |
| review burden | logged review-action intensity per active researcher-step | total labor, service quality, rigor, wellbeing, lifecycle cost | suppress reviews/submissions or move labor off-ledger |

All three remain useful as contrastive interventions. None is a recommended
national science-policy objective. The point of the current experiment is
precisely to reveal their different institutional consequences.

## Measurement model

Every metric card separates five layers:

```text
public/scientific value
  -> construct (what we mean)
  -> observable model (what events or states could indicate it)
  -> aggregation (who, where, and when is combined)
  -> objective or diagnostic role (what decisions may use it)
```

Skipping a layer silently turns a convenient simulator column into a claim
about good science. The audit therefore records proxy assumptions, Goodhart
paths, distribution, time horizon, state-policy relevance, missing fields, and
the validation needed before optimizer exposure.

## Prospective landscape

The nine cards are deliberately not one score:

1. verification-weighted epistemic progress;
2. independent replication and correction capacity;
3. a scientific possibility portfolio;
4. disparity-aware epistemic diversity;
5. typed participation, routing, and authority;
6. distributed process burden and service quality;
7. verified marginal resource efficiency;
8. long-horizon capability, resilience, and option value;
9. mission and public value with distribution and externalities.

Some are possible future optimization arms; some are vector components or
constitutional audits. A metric's importance does not imply that it should be
optimized. In particular, public value and standing require explicit authority
and amendment processes, while replication/correction remains report-only
until its measurement and gaming behavior are validated.

## Objective graph

The graph in JSON makes the non-equivalences executable as lint:

```text
fixed proxy -> partial proxy for -> construct -> operationalizes -> value
       |                                |
       +---- gaming path ---------------+

national science policy -> contextualizes capability and public mission
national science policy -/-> epistemic value as a universal identity
```

Important examples are explicit graph edges: entropy is only a partial proxy
for diversity; active fraction is only a partial proxy for typed participation;
review-action count is only a partial proxy for distributed burden. National
science policy legitimately introduces public mission, capability,
distribution, authority, and externality questions, but national advantage is
not identical to epistemic progress or universal scientific value.

## How this can become an experiment

Promotion requires a new preregistration, new evidence split, construct-validity
evidence, adversarial fixtures, and an explicit choice among separate arms,
Pareto comparison, target ranges, or temporary scalarization. There is no
default composite. The current campaign's source files, execution records, and
evaluation split are outside this artifact's authority and data boundary.

Run the local validation without opening any campaign runtime state:

```bash
.venv/bin/python -m utopia.optimization.metric_objective_landscape \
  research/objectives/landscape/metric-objective-landscape-v1.json \
  --root .
```

