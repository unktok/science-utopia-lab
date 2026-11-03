# Opt-in bounded local autonomous search v14

`native_search_v14.py` controls existing campaigns. Black-box requests run a
fresh free authored definition for each of 1–8 scheduled slots, using unchanged
`NativeAdaptiveDesignCampaign(mode='blackbox', count=1)`. Nested LR requests
must allocate exactly four slots and use unchanged v13 `2→1→1`: two initial
IID draws and one LOO update, one fresh draw under its saved weights, then one
free redesign. Other nested budgets are rejected. There is no new optimizer,
quality gate, source catalogue, identity fallback, replacement draw or native
retry. The exact supplied LossSpec is the target. Technical validity, held-out
metrics and promotion policy remain separate concepts.

The request schema is `scienceutopia.native-search-request.v14` with exactly
`schema, initial_system, loss_spec, seed, years, method, native_budget, designer`.
Years are 1–4; seeds must be development seeds matching the initial system.
`designer` contains exactly fixed local `model: qwen3:8b`, `max_attempts: 1..3`
and `max_tokens: 512..8192`. The UI cannot select commands, host paths, modules
or provider URLs. Arbitrary generated source remains data for the existing
isolated native executor. All eight native measurement adapters are allowed,
including raw accepted reviewer scores and unreviewed acceptances; existing
one-candidate jobs retain their original six-metric validation default.

The operator supplies a JSON file with exactly `provider_binding`, containing
`model, model_digest, corpus_sha256, dataset_identity, corpus_years, image_id`.
The horizon is exactly four corpus years and the execution image is an explicit
SHA256 digest. Validation and enqueue use this binding and the clean server
source commit. The worker compares its actual native factory model, corpus,
dataset and horizon against those immutable values before authoring or native
execution. The local generator also validates its provider binding. Neither
provider is constructed by API validation or enqueue.

`NativeSearchQueue` persists `native-search-jobs-v14.sqlite` and at most two
queued/running searches. It shares `worker.lock` with the existing job queue
when both use the same operator queue directory. SQLite immediate transactions
serialize submission/claim. Exact plan hashes provide permanent idempotency,
including completed and failed requests. Changed source or provider bindings
produce different plans; a stale consent hash cannot authorize a changed
request. A single explicit worker resumes a running search before queued work.

Artifacts under `search-<32 hex>/` are:

- `plan.json`: exact request/hash, source, provider/corpus/image binding, stage
  counts, maximum generator/provider attempts, and failure/objective policies.
- `campaign/native-adaptive-state.json` or `campaign/native-nested-state.json`:
  the original validated campaign format, exact requests, definitions, literal
  graph/source operations, draws, observations, null failures and updates.
- `authoring/`: bounded local designer journal, owned by the v14 generator.
- `worlds/<run-id>/`: original native factory checkpoints, response cache,
  actual wire requests and generated-code contexts.

Every read validates the immutable plan and original campaign replay contract.
Missing state is rejected, never recreated. BaseException interruption leaves
the same running search resumable. Saved generation definitions are reused;
the original factory owns exact completed-response/year checkpoint replay.
If the final campaign commit precedes a process interruption, restart only
marks the queue terminal and does not even construct a generator/native factory.
Unexpected generator exceptions become malformed `generation_failure` JSON,
preserved by the campaign as null compile failures consuming their scheduled
slots. Native failure observations also retain null loss. A terminal
infrastructure failure preserves partial evidence and its error.

The additive loopback API uses the existing origin/host/session-token checks:

- `POST /native-api/search-validate` accepts the exact request and returns its
  SHA256, source commit, plan hash and maximum provider attempts, without compute.
- `POST /native-api/searches` accepts exactly
  `{request, confirmed_request_sha256}` after explicit compute consent.
- `GET /native-api/searches/<id>` and `.../<id>/evidence` return
  `scienceutopia.native-search-progress.v14`, including partial/failed evidence.

Progress exposes exact records/pending state, flattened suggestion/observation
pairs, all equal-loss best ties, earliest tie as display incumbent, and current
latest-stage observation separately. A generation failure has null current;
it cannot visually reuse an older successful outcome. Budget consumed means
committed scheduled stage slots, including null generations. Native observations
count is separate. Exact definitions and candidate SystemSpecs preserve source,
code and graph changes; neither new hashes nor new names imply useful invention.

Launch the existing server with `--search-config <operator JSON>` to opt in.
Launch a separate worker with `--search-worker-once --search-config <same JSON>
--data-cache <operator cache>`, sharing `--queue <directory>` with the server.
Launch native Python with fixed `PYTHONHASHSEED`; no actual worker was executed
during implementation QA. Existing jobs/society routes remain available.

Software verification uses SCRIPTED generation and HTTP/native fixtures only.
It covers strict request budgets, v13 efficiency loss, exact consent and completed
idempotency, source/provider mismatch, bounded queue, null generations/worlds,
cross-queue single-writer locking, source/plan/state tampering, missing-state
rejection, separate-process restart, original native scripted world/ties/current,
HTTP origin/token/source checks and unchanged legacy job API regressions.
These tests are software evidence, not Qwen invention or scientific outcomes.
