# Testing

Latest v5 evidence:the full Python suite passes1311 tests with6 explicit skips
from clean`ecd1ae6`. It includes the new native resource capability, accounting,
restart, authoring and external-inbox audits. Later analysis-only observed-system
export and node-count graphics receive separate focused checks. See the source/JUnit-bound
[verification receipt](../research/results/objective-conditioned-design-v5-verification.json).
These are software checks, not fresh scientific experiments. The v4 full-suite
result of1197 passed/6 skipped is historical; the new full result above supersedes it.

Use the repository environment and explicit deterministic CPU settings:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
  .venv/bin/python -m pytest tests/optimization tests/runtime \
  tests/replay tests/mechanisms/evaluation tests/system -q
```

The 2026-10-31 native-kernel integration regression passed **611 tests, with three
skips**, in 53.40 seconds using this broader focused command:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
  .venv/bin/python -m pytest tests/models tests/system tests/runtime \
  tests/funding tests/optimization tests/communication tests/government \
  tests/replay tests/data/test_fulltext.py -xq --tb=short
```

This is not a full-repository suite or empirical model validation. Native tests
preserve actual domain phases and script only corpus/retrieval/HTTP for exact
QA. They compare baseline/original state, RNG and wire requests, edge/delay
effects, isolated-code selection with review removed, open LLM institution
memory, generic non-paper artifact identity/history, portable replay, plain
original funding in empty publication years and empty citation histories.
Live Qwen evidence belongs in the separately pinned research probe result.
The skips are the two environment-opt-in real-ledger/tokenizer tests and the
optional rapidgzip test; local Docker source-execution tests did run.

Game UI changes also run:

```bash
node --test game-ui/test/model.test.mjs
node --check game-ui/src/app.js
node --check game-ui/src/model.js
```

## Test levels

| Level | When | Expected dependencies |
|---|---|---|
| focused unit | every edit | CPU only |
| shared regression | before integration | CPU only, explicit deterministic environment |
| full suite | before a release or broad refactor | may include upstream/integration assumptions |
| model smoke | model/backend changes | running endpoint, bounded minutes |
| longitudinal campaign | research protocol only | frozen commit, hours or days |

## Current known baseline

The six failures reported on2026-10-27 in
`tests/experiments/test_prospective_logging.py`, whose mocks patched a removed
`funding_feedback.subprocess` attribute, were repaired during v4 integration.
The [v4 verification](../research/results/non-scale-integration-v4-verification.json)
records the full1197-pass/6-skip result. Do not reuse the old failure list to
excuse a current regression, or describe a historical full suite as a new run.

## Reproducibility expectations

- Set required environment variables rather than allowing fixtures to infer
  them.
- Test deterministic serialization and state restoration.
- Never require an LLM for a unit-level contract test.
- Record model-dependent smoke results separately from deterministic tests.
- Compare generated artifacts byte-for-byte when they are intended to be
  reproducible.
