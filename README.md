# Science Utopia Lab

Optimize the **system that organizes science**, not the researcher-model weights.
This research fork extends [ScienceUtopia](https://github.com/Ahren09/ScienceUtopia)
with executable institutions, editable mechanisms and wiring, objective-conditioned
search, optional gradient estimators, and an English pixel/cyberpunk evidence UI.

The original researcher world is a contained instance, not the limit of the
design space. Small experiments retain that world; numerical test fixtures are
not substitutes for scientific evidence.

## Start here

| Question | Canonical document |
| --- | --- |
| What are we trying to achieve? | [Research purpose](RESEARCH.md) |
| What works, and what remains unproven? | [Current status](research/STATUS.md) |
| What is the publication strategy and next research task? | [Active publication goal](research/publication/publication-ready-v3.md), [original comparison contract](research/publication/benchmark-contract-v1.md) |
| Where is the scientific record? | [Research index](research/INDEX.md) |
| How is the repository organized? | [Repository map](docs/repository.md) |
| How do I develop or contribute? | [Setup](docs/development.md), [contributing](CONTRIBUTING.md), [tests](docs/testing.md) |
| What code boundaries must remain separate? | [Architecture](docs/architecture.md) |
| How do I run a campaign safely? | [Research workflow](docs/research-workflow.md), [designer preflight](docs/designer-preflight.md) |
| Where are the manuscript and interface? | [Manuscript](paper/README.md), [English game UI](game-ui-v2/README.md) |

## Current evidence

The [latest reviewed integrated manuscript](paper/README.md) is73 pages,
with38 figures and30 tables. Its62-file minimal source rebuild matches the
text and all73 reviewed page images. It preserves the research program and prior
drafts without an artificial page cap; paper length is not publication readiness.

The [parent-presentation comparison](research/components/native-parent-presentation-loop-v1.md)
is stopped with its exact partial records and unknown completion preserved.
The separate [numeric comparator](research/data/native-parameter-comparator-v1/README.md)
closes all six actual worlds with matching cold audits, costs and reports;
no own policy improves the known reference incumbent. The new
[workflow-v2 experiment](research/results/native-workflow-v2-first-dispatch-v1.json)
starts23:52:27UTC on November13 from a clean frozen source/unused plan.
Initial real-backend readiness passes and the first fresh R7 reference begins;
two references/six own slots are the finite upper bound, not completed results.
See [current status](research/STATUS.md) for liveness, not software-test scores.

The [closed T/U development](research/data/native-objective-instrument-loop-v1/README.md)
retains all eight own submissions: six native completions and two technical
nulls. Its [selection-fixed evaluation](research/results/native-objective-fixed-evaluation-v1.md)
closes18 actual worlds/21 logical cells on three unused seeds. Publication-count
selections tie strong connected accept-all rules; content-score differences
against reviewer-free accept-all are mixed. Evaluation seeds are not independent
optimizer histories. The [three closed advice-timing controls](research/results/native-instruction-timing-v1.md)
establish delivery to model inputs but no topic/duration or T/U gain here;
full inputs, replies and some resource trajectories differ. These controls and
a direct executable-governance precedent now enter the reviewed PDF.

A separate [finite T/P pilot](research/results/native-capacity-objective-loop-v1.md)
normally closes five developer references and four own submissions: three
complete/one technical null. All complete own programs tie strong allocation
rules atT=−12/P=−15, without changing wiring. Its full data, failures, costs
and two actual figures enter the latest PDF. P measures initial-founder
active annual boundaries, not a hidden constraint on T. The prepared fixed
evaluation is not dispatched to enlarge this flat comparison. The subsequent
[three planning controls](research/results/native-catalog-actuation-v1.md)
close with18 accepted decisions for concrete advice and legal catalog assignment,
versus12 for the cut control on one reused seed. Their actual choices, effects,
costs and two figures enter the preserved66-page draft. These are developer policies,
not automatic invention. A separate [free planning T/U study](research/results/native-planning-objective-loop-v1.md)
now closes all eight references and six own proposals, with matching double
audits/costs and five double exports. Every own assigned loss ties its best
reference; all edits are selection source only. This later closure now enters
the preserved69-page PDF and latest73-page version with a complete14-condition
table and three print-sized figures.
The [fixed-policy evaluation path](research/components/native-planning-fixed-evaluation-v1.md)
is software-verified; no new evaluation seed list or actual inference is yet
dispatched by that preparation.
[Current status](research/STATUS.md) is the authority for live progress and
closure-gated readouts. New invention, stable strong-rule advantage and
publication readiness remain unestablished.

Earlier completed evidence remains available:

The earlier finite [design-freedom comparison](research/protocols/campaigns/native-design-freedom-v2.md)
is complete: two objectives, five proposal arms, three controller histories and
all120 candidate slots, followed by fixed selection and90 physical unused-
condition evaluations. Both full audits agree using an explicit order adapter.
The historical12-page empirical study draft, figures,
supplemental analyses and numerical/paper rebuilding are also preserved.
[V2 requirement audit and submission judgment](research/publication/submission-decision-v2.md)
closes the finite decision package, not the broader research program.
Immediate main-conference submission is not recommended; top-conference
readiness, useful structural invention and method superiority are not established.
There is no remaining writer from this study. See [current status](research/STATUS.md).

The earlier [pre-scale completion](research/pre-scale-completion.md) is closed:
all12 information-intervention worlds close with matching full audits,
[complete descriptive analysis](research/results/pre-scale-information-v1.md)
and reproducible numerical figures. Fresh numerical/staged author readiness
passes at its source; the finite T/E search, selected-policy evaluation and
final integration checks are closed. These historical studies are not the
separately closed planning T/U pilot.

Completed evidence includes the [eight-candidate feedback pilot](research/results/native-feedback-comparison-v1-a1.md)
and [eight strong-rule controls](research/results/native-benchmark-controls-v2-a1.md),
with original-source audits. Simple all-accept controls recover the earlier
proxy minimum; weak-seed improvement alone is not effective invention or better
science. Earlier studies, including the [V45 pilot](research/results/native-warmstart-v45-a1.json)
and external-author improvements, retain their original source and provenance.
The completed study does not establish feedback/method superiority or conference readiness.

## Local development

Use Python 3.11 through the approved project environment or `uv`. On this
computer, never execute Apple-provided Python/pip. Before fetching packages,
verify the resolved pip is at least26.2.2; do not install or download models
merely to read the repository.

```bash
# Existing environment: documentation checks need no model, GPU or network.
.venv/bin/python scripts/check_repository_docs.py

# Focused software tests; this does not run a scientific campaign.
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv/bin/python -m pytest tests/reports/test_repository_docs.py -q
```

Installation variants live in the [development guide](docs/development.md).
The [previous README](README.history-through-v45.md) preserves the mixed
upstream/Lab instructions exactly as of5ae3c5c, including historical examples;
it is not the current experiment prescription.

## Reproducibility and collaboration

- Develop on feature branches; execute long campaigns only from clean,
  commit-pinned worktrees. Never edit an active or historical experiment tree.
- Keep loss, technical validity, evaluation metrics and optional adoption policy
  separate. No hidden fairness, novelty or improvement veto.
- Track compact results, manifests and source identities; ignore raw
  `outputs/`, caches, weights and environments.
- Keep old protocols, outcomes, failures and source-bound certificates unchanged.
  No certificate from an older source authorizes a new experiment.
- Entry documents describe current state. Versioned records preserve history.

Upstream attribution and the [Apache2.0 license](LICENSE) remain unchanged.
The [upstream website](https://ahren09.github.io/ScienceUtopia/) describes the
base simulator, not all claims of this fork.
