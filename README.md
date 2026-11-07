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
| What is the publication strategy and next research task? | [Research plan](research/publication/plan.md), [comparison contract](research/publication/benchmark-contract-v1.md) |
| Where is the scientific record? | [Research index](research/INDEX.md) |
| How is the repository organized? | [Repository map](docs/repository.md) |
| How do I develop or contribute? | [Setup](docs/development.md), [contributing](CONTRIBUTING.md), [tests](docs/testing.md) |
| What code boundaries must remain separate? | [Architecture](docs/architecture.md) |
| How do I run a campaign safely? | [Research workflow](docs/research-workflow.md), [designer preflight](docs/designer-preflight.md) |
| Where are the manuscript and interface? | [Manuscript](paper/README.md), [English game UI](game-ui-v2/README.md) |

## Current evidence

The latest local-author pilot is **closed**, not running. Two submitted
institutions were dispatched: one native evaluation completed and one failed
a producer/consumer tensor contract. Retrospective pooled scores are not
objective-specific, held-out or causal improvements. See the
[audited result](research/results/native-warmstart-v45-a1.json) and
[interpretation](research/logbook/2026-11-07-native-warmstart-v45.md).
Earlier studies, including external-author improvements, remain part of the
record with their original source and author provenance.

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
