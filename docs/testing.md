# Testing

Use the repository environment and explicit deterministic CPU settings:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 \
  .venv/bin/python -m pytest tests/optimization tests/runtime \
  tests/replay tests/mechanisms/evaluation tests/system -q
```

The integrated foundation currently passes 131 tests in this group.

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

As of 2026-10-27, the full suite has six pre-existing failures in
`tests/experiments/test_prospective_logging.py`. Those tests patch a removed
`funding_feedback.subprocess` attribute and fail unchanged on `main`. Do not hide
new failures behind this baseline; report focused and full-suite outcomes
separately until the compatibility tests are repaired.

## Reproducibility expectations

- Set required environment variables rather than allowing fixtures to infer
  them.
- Test deterministic serialization and state restoration.
- Never require an LLM for a unit-level contract test.
- Record model-dependent smoke results separately from deterministic tests.
- Compare generated artifacts byte-for-byte when they are intended to be
  reproducible.
