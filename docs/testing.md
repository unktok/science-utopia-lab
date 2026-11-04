# Testing

## Designer interface recurrence prevention — V16

Run `tests/optimization/test_native_designer_contract_v16.py` alongside staged
author/compiler/transport/audit tests. It covers exact JSON types (including
Unicode, null, booleans and integers above2^53), per-tool sender/receiver
agreement, alternating/alias reads, bounded/stale memory, and fail-closed
certificate replay/tampering/expiry/source/backend/model checks.

These are SCRIPTED tests, not actual Qwen evidence. Before an expensive
model-authored campaign, also follow the [real-backend preflight](designer-preflight.md).
A unit pass, one completed JSON reply or a static compilation does not establish
multi-turn authoring reliability. Keep literal controls, unforced planning and
scientific-world effects as separate evidence levels. Retain unsuccessful
preflights and exact wire bytes; never call interrupted suites full passes.

## Active v8 verification — 2026-11-02

Clean live source425ec10 full Python suite:1509 passed/6skipped,602.55s.
The second full suite at clean integration eda6537 passes1587/6skipped in968.70s,
including the response-boundary implementation and production review-context
capability. Later exact-observation report/UI selection fixes have their own
focused scopes, not falsely attributed to that earlier full suite. Exact-file authoring,
independent audit and figure scope passes31 checks at1601019 (4.52s); response
attribution/concurrency scope passes40 at4ea5e74 (1.27s); plotting scope passes5
at434685e (0.70s). These scopes overlap, not additive test totals. All model-based
actual outcomes belong to immutable425ec10 campaign output, not these scripted
software checks. Frozen bfe83c0 response QA and separately pinned e8c0677
read-only refit keep their original source identities after integration.

Later clean3ff2968 report/validator/response suite passes82 with1 duplicate heavy
seven-world check deselected (5.04s). Subsequent physical-width/schema plot
checks pass18 (2.67s); these are separately scoped, not attributed to3ff2968.
UI implementation184checks/typecheck/build and ACTUAL byte-exact export plus
desktop/graph/crossscore/mobile browser QA pass. Every capture haszeroerrors,
overflow andnonGET dispatch. These are not new simulator or model calls.

Final clean publication68727c4 passes83 focused checks with1 duplicate heavy
check deselected (4.06s); committed paper text3c2ae4b passes3 typography checks.
All37 PDF pages are rendered and visually reviewed; the final one-line error/
null-loss clarification changes onlypage23 pixels, individually rechecked.
Full source/JUnit/raw/UI/PDF hashes:
[v8 verification receipt](../research/results/objective-structure-v8-verification.json).

## Historical v7 verification — 2026-11-02

Full clean live source c09e069:1480 passed/6 skipped (847.51s).
Full clean integration ceb8248:1496 passed/6 skipped (816.48s).
Later conditional-unused/diagnostic changes:47 targeted checks at1da13de
(104.99s). Final audit/figure changes:17 checks at31306e2 (5.13s).
These suites overlap; do not add their counts or claim that one full run used
all later changes. UI feature6b72d52 (integrated as37c51b4) passes174 tests,
typecheck and production build. Actual browser inspection has no errors or
mobile/desktop overflow and starts no native experiment. See
[source/JUnit/artifact receipt](../research/results/non-scale-closure-v7-verification.json).
Two full regressions plus risk-scoped later checks are software verification,
not independent experiments or evidence of institutional benefit.

## Historical v5 verification

V5 evidence:the full Python suite passes1311 tests with6 explicit skips
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
