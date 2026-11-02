# Read-only open-design expected-loss audit v11

`scripts/analyze_native_open_estimators_v11.py` independently reconstructs the
eight-world native pilot without generating designs, calling a model, importing
institution source, or launching a container. Original researcher worlds and
raw evidence remain unchanged. The analysis must run after the pilot writer
has stopped; concurrent raw changes fail the immutable-inventory guard.

```sh
.venv/bin/python scripts/analyze_native_open_estimators_v11.py \
  --run /absolute/raw/output \
  --expected-source EXACT_ACTUAL_40_CHARACTER_SOURCE_COMMIT \
  --output /absolute/report/outside/raw.json
```

`--allow-incomplete` supports a truthful interrupted/partial audit, not a
completed-world score for an unfinished physical run. Its default requires all
eight native draws complete, with no generation, world or estimator failure.
Technical stops retain null failed losses and do not become numeric penalties.

## What is checked

- The exact declared utility LossSpec, source/model/corpus/seed/native horizon,
  per-arm method bindings, two generations of two draws, and original population.
- Every generation's exact own-arm past history, request-bound external inbox,
  original manifest, and saved source/factors/coordinates. Initial definitions
  must match across methods except the declared top-level vocabulary and
  factor-choice `provenance` metadata fields; code, IDs, edits, bounds, weights,
  metadata, wiring and semantic parameters/state named `provenance` are not erased.
- Exact replay of the existing durable campaign: conditional likelihoods,
  sampled raw latents/assignments, compatibility signature, prior-only frozen
  fit, both categorical and Gaussian expectation corrections, all comparator
  gradients, and subsequent recorded weights. Replay uses numeric tensor math,
  not generated institution or researcher execution. Replay-critical optimizer,
  checkpoint audit helper and kernel modules must match their actual source-pin blobs exactly;
  the new audit script itself is allowed to be newer than the actual source.
- Independent extraction of measurements and native loss from original portable
  checkpoints, annual event prefixes and initialized state. Physical validation
  reuses `audit_native_run` with explicit v11 experiment/loss arguments; old v7
  default bindings and validators are unchanged.
- Exact SystemSpec and generated-source/context/result/image receipts, durable
  institution state, open-domain effect lineage and completed model-input
  messages, SQLite response hashes, and ordered actual HTTP payloads. Ambiguous
  code-attempt attribution stays explicitly ambiguous rather than being guessed.
- Each physical native run belongs to exactly one declared draw. Complete reply
  journals reconcile with logical final checkpoint counts. This pilot declares
  no physical sharing/replayed historical replies; an incomplete pilot reports
  completed logical reply counts separately from all physical replies.
- Every observed institution and every exact best-loss tie is retained, along
  with the incumbent path. An unevaluated initial institution is not scored.
- Before/after raw file inventories and hashes are identical. The output path
  must be outside the raw directory. Repeated audit on unchanged source/raw
  should produce byte-identical JSON; source hashes are included in the receipt.

## Evidence limits

The audit establishes recorded execution/provenance and estimator replay, not
institutional superiority, science quality, useful autonomous invention,
recursive designer improvement, full-world pathwise derivatives, or variance
reduction. Two prior points can yield an unstable ridge control variate. A
nonzero raw LR estimate under equal costs is possible Monte Carlo noise, not
comparative evidence. The external author's identity remains self-reported.

`tests/reports/test_native_open_estimators_v11_audit.py` verifies read-only
repeatability, explicit incomplete and technically stopped classifications,
null failed costs, external request binding, canonical update/summary tamper
rejection, strict initial-definition matching, all ties, symlink rejection and
concurrent-write detection. These are scripted software guards, not Qwen results.
