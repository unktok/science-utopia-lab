# Research campaign workflow

Software development and scientific evidence use related but different
lifecycles. A passing feature test does not make a research result, and an
interesting run does not retroactively define a valid protocol.

Closed-study reports also retain compact author-step diagnostics from the
original-source audit: terminal reason, each status, distinct step/transition
error channels, virtual filenames and exact record hashes. A rejected compiled
action may be null or malformed JSON; it is not a validated tool object. These
diagnostics are evidence locators, not inferred causal labels, independent
failed trials or scientific-merit criteria. An applied source write is not proof
of executed behavior; a generic generation failure is not a sufficient diagnosis.
Full raw wire messages and source replay remain in the input audit. Do not feed
post-study diagnostics into a still-active campaign or manufacture a closed
audit from a partial live snapshot.

For closed V2 selected-policy evaluation figures, use
`python -m scripts.figures.native_design_evaluation --report <closed-report.json> --output <fresh-directory>`
with the approved project interpreter. It emits all reference comparisons and
separate horizons, not a retrospectively chosen favorable reference. Plotted
points rejoin the report's physical scores and job identities. Null pairs remain
outside the numerical axis; diamonds are means of available pairs, not full
expected losses or confidence intervals. Squares denote the same physical job,
not independent replication. The complete input report keeps cross-objective
scores and all missing pairs. SCRIPTED previews are not scientific evidence.

## Before execution

For model-authored searches, first pass the [finite real-backend interface
preflight](designer-preflight.md) at the current runtime/model/backend binding.
Supply its operator-owned certificate to server and worker/campaign entrypoints.
This is technical readiness, not a scientific-merit constraint. Missing,
incomplete, failed, stale or mismatched evidence must block expensive dispatch.

1. Define the mutable `SystemSpec` subspace.
2. Freeze a versioned `LossSpec` for optimization seeds.
3. Define technical `ValiditySpec` checks.
4. Reserve disjoint optimization, selection, and held-out evaluation seeds.
5. Declare budget, fidelity, stopping conditions, and optimizer state format.
6. Declare held-out evaluation metrics and any optional decision policy.
7. Merge the protocol and create an annotated protocol tag.

## During execution

1. Run from a clean commit-pinned experiment worktree.
2. Persist every optimizer suggestion before dispatch.
3. Keep run registries, output roots, and mutable caches isolated.
4. Preserve technically valid poor outcomes.
5. Quarantine incomplete or corrupt observations without inventing penalty
   losses unless the `LossSpec` explicitly defines that behavior.
6. Do not alter loss, seeds, simulator, evaluator, or stopping rule after
   seeing results.

For the opt-in automatic designer, use the [v14 runtime contract](../research/components/native-autonomous-search-runtime-v14.md)
and [literal stable-ID authoring IR](../research/components/native-stable-id-authoring-ir.md).
Validate the exact request, then grant fresh request-bound compute consent;
preparation, evidence viewing and local editing are not inference authorization.
The UI/API process never runs the designer or researcher. Start its separate
single worker with the same source, provider config and queue directory.
Verify the actual launch environment (including `/usr/local/bin/docker` on
this host) before dispatch. Follow the approved Python/TLS instructions;
do not use Apple Python. Record started/ended receipts and preserve failed
launches. An interrupted generation intent consumes its declared attempt;
resume the same queue rather than resubmitting or resetting its budget.

## After optimization

1. Freeze the selected candidate.
2. Evaluate it on untouched seeds and declared stress scenarios.
3. Report effect sizes, uncertainty, resource cost, slices, and failure modes.
4. Apply a decision policy only if one was explicitly versioned.
5. Commit compact results, hashes, manifests, and interpretation.
6. Create an annotated result tag after verification.

If all authoring attempts fail, there is no selected institution to freeze or
evaluate on held-out seeds. Publish the nulls, original drafts, diagnostics,
unknown replies and separate designer/scientist costs. A terminal scheduler
does not imply a compiled design or completed world. An interface correction
requires a separately prospective source/budget and separate results, never
repair of historical drafts or hidden replacement trials. See the
[closed v14 a1 failure](../research/results/native-autonomous-search-v14-a1.md).

## Parallel development

Long runs and development use separate worktrees. The game UI, graph runtime,
and analysis tooling may progress while a campaign runs, but no code change may
enter the frozen experiment worktree. A changed simulator or producer
configuration creates a new campaign revision.

The authoritative research taxonomy and historical mapping are in
[`research/INDEX.md`](../research/INDEX.md).

## Reproduction tiers for the submission package

These are different tasks, not interchangeable evidence of reproducibility.
None of the commands below authorizes downloads, external spend or disclosure.

| Tier | What is reproduced | Inputs / boundary |
| --- | --- | --- |
| Software QA | Compiler, records, statistics and artifact guards | Scripted fixtures, installed dependencies; no real LLM result |
| Figure/table rebuild | Recorded scientific summaries and the working PDF | Tracked compact JSON, source, figures and cached TeX resources; not a raw re-audit |
| Read-only raw audit | Original source, every trial, physical replies/code receipts and checkpoints | Full local raw archive and matching frozen checkout; no new inference/code execution |
| Independent rerun | Fresh proposed institutions and researcher trajectories | Approved exact model artifacts, corpus, image, backend/context and finite compute; not a failed-slot refill |

### Rebuild a recorded strong-control figure without private caches

From the integration repository root, with the existing approved environment:

```sh
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv/bin/python -m scripts.reports.native_control_summary \
  --summary research/results/native-benchmark-controls-v2-a1.json \
  --output tmp/reproduction/controls-r1.json \
  --figures tmp/reproduction/controls-r1 --print-layout
```

Both output paths must be fresh. The input summary's source/hash, nulls and ties
are preserved. New rendering provenance is recorded separately. This does not
claim the original raw audit was rerun or that independently rendered SVG/PDF
metadata is byte-identical. It starts no model, downloads no data, and does not
overwrite manuscript inputs. See the [paper build guide](../paper/README.md)
and its dependency/visual-QA receipt for the cached PDF build.

### Audit before reporting the V2 study

The current V2 experiment is pinned at
`b6654adefc42223f9ecc7b4e53c043c879230f68`.
After its writer is terminal, use that detached source's
`scripts/analyze_native_design_benchmark.py` with the full raw archive,
`--expected-source` and a fresh output outside the raw root. Repeat to a second
fresh audit output and compare them. Do not run its exact-source audit from a
later integration source or call an in-progress archive complete.

The separately implemented integration modules then project that audit:

```text
python -m scripts.reports.native_design_benchmark --plan <raw/plan.json> \
  --audit <closed-full-audit.json> --expected-source <40-hex-commit> --output <fresh-report.json>
python -m scripts.figures.native_design_benchmark --report <report.json> --output <fresh-figures>
python -m scripts.reports.native_selection_relaxation --run <raw-root> \
  --audit <closed-full-audit.json> --expected-source <40-hex-commit> --output <fresh-analysis.json>
```

Here `python` is a notation for the approved uv-managed project interpreter,
not Apple Python. The last module fixes realized decisions/reviews and relaxes
only decision flags. Its minima are not feasible dynamic-policy counterfactuals.
These reporting tools preserve missing scores and physical-sharing labels;
they do not rerun worlds, renew calibration or update the proposer.

Raw checkpoints contain original absolute locators. A relocated copy needs an
explicit verified relocation procedure; do not edit old journals or silently
rewrite paths to make an audit pass. The compact Git results are not a substitute
for the full raw archive. No public raw archive has been released by this task.

### Exact resources versus replaceable implementations

The pinned V2 plan binds scientist Qwen3-8B, the separately approved local35B
designer, image identity and corpus. These are not interchangeable model names.
The corpus is `Ahren09/SciEvo`, configuration `arxiv`, revision
`f80fb38a034b2f763dfcbdd2cd187f5b42ddcce6`, CS categories from the plan,
2016--2019,103107 ordered documents. Ordered corpus SHA256:
`ee4ca9325e5a61a61edc052346f24e94071b631c622193562308ebd054b28fb2`.
The completed S1 checkpoint records retrieval model `thenlper/gte-small`, revision
`17e1f347d17fe144873b1201da91788898c639cd`; do not substitute the unused
`all-MiniLM-L6-v2` entry elsewhere in configuration. The pinned native factory
uses CPU retrieval and source-owned normalization/cache binding.

The scientist digest is
`500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`;
the local designer alias `qwen3.6:35b-mlx-64k` has digest
`f3ddc74319e42fad1cce455555e9f6864372665bcf9f0578b600f554787cbcc8`.
An alias/digest alone is not a public download or model-conversion recipe.
That recipe and separate model-server environment remain a reproducibility
gap to resolve before claiming fresh-machine inference reproduction. A different
model/backend is a declared new study, not a silent replacement.

The later [selected backend artifact observation](../research/results/submission-backend-artifacts-observed-v2.json)
records the existing native Ollama daemon executable and ten app-bundled
Ollama/llama/MLX/Metal file hashes at10:23UTC. Both MLX variants are installed;
this is not proof of which variant was loaded for an inference, a complete
server lock or a startup observation. The restricted-shell version command
reports client0.33.3 but cannot connect; current backend version is not inferred
from that command. Do not assume that this native app's MLX dependency must be
a pip package in the researcher interpreter. No server, weights or settings
were modified. The model's upstream revision/conversion recipe remains unknown.

The [local/public manifest comparison](../research/results/designer-local-public-provenance-v2.json)
finds the existing64k alias and its local base share995 nonparameter descriptors
after removing `from` annotations; the added parameter is `num_ctx=65536`, while
the manifest config also differs. These are descriptor/metadata comparisons,
not reconstructed historical creation commands or a fresh tensor hash audit.
The current [public same-name tag](https://ollama.com/library/qwen3.6:35b-mlx)
has a different manifest and tensor set. Do not silently pull that tag as an exact
experimental replacement. The local base digest's specific registry query
returned404; neither an immutable public retrieval path nor its HF origin has
been established. The user likewise did not have a confirmed origin record.

The existing sandbox reports image
`sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833`,
linux/arm64, under `python:3.11-slim`; the current Docker metadata also reports
that ID under `RepoDigests`. Remote registry availability has not been verified.
The executor uses `--pull=never`, no network/host mounts, a read-only filesystem,
unprivileged user and bounded resources. There is no host-execution fallback.

The [observed environment](../research/results/submission-environment-observed-v2.json)
records selected package versions at09:45UTC on2026-11-07. It is deliberately
**not a startup attestation, complete lockfile, or separate inference-server
environment record**. Its observation command installs/fetches nothing and
cannot write inside the frozen source or raw root. Current Docker server
metadata reports29.8.2, likewise an observation rather than a startup claim.

### Scientist response-token accounting

After a full original-source S1/V2 audit is CLOSED, use the approved project
interpreter with `-m scripts.reports.native_token_costs --run <raw-root> --plan <plan.json> --audit <full-audit.json> --expected-source <experiment-commit> --output <fresh-output.json>`.
It verifies the exact audited raw inventory before/after, opens SQLite read-only,
joins committed replies to ordered wire inputs, and reports prompt/completion/
reported-total/cached-prompt usage separately. Partial-world journals and wires
without committed replies remain visible. Missing or invalid usage is not0;
reported totals are not silently repaired to match components. Distinct physical
journals are counted separately even when content hashes coincide. This is a
separately source-hashed projection, not a new original-source audit.

Provider token counts do not measure fresh GPU operations, FLOPs, energy,
wall time or money. Warm-cache differences can depend on operation order rather
than policy alone. Designer/calibration/load/host/retrieval/container costs remain
separate; unknown/omitted costs are not zero. Preserve recorded campaign wall
time without adding overlapping role/runtime/checkpoint durations. This module
does not alter losses, validate scientific merit or contact a model.

### Release and attribution boundary

Keep the repository's Apache2.0 LICENSE and upstream attribution. The current
[SciEvo dataset card](https://huggingface.co/datasets/Ahren09/SciEvo) declares
Apache2.0 and requests citation of
[Jin et al., SciEvo](https://arxiv.org/abs/2410.09510).
These live primary pages were checked2026-11-07; the pinned-revision README
could not be retrieved through that check. This records the card's declaration,
not a verified blanket permission for every underlying paper or model artifact.

Before a reviewer/public bundle, check source/data/model provenance and terms,
anonymous filenames/metadata, operator paths, secrets and generated content.
Do not include raw caches, model weights, `.env`, operator configs or an entire
home/Git history by default. Sharing, remote pushing, authorship and actual
submission still require the user's approval. Local preparation is not release.
