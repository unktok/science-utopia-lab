# Infrastructure amendment: derived RAG index on native cold resume

Preregistered before any repaired live retry. The a1 source pin and its raw
evidence remain immutable; this preparation invokes no native Qwen inference.

## Preserved a1 failure, not a failed institution/loss

The first live society pilot at source `f7e3ae4` completes year1 with24 researcher
responses. Its externally authored annual-sprint/open-publication institution is
staged, explicitly confirmed through the actual UI and durably adopted. Year2
executes its code/research-plan effects and receives5 intention responses, but
submission retrieval then raises `TypeError` because `document_embeddings` is
`None`. Its last valid saved society is the adopted year1 checkpoint. The29
responses remain in its original independent response journal. **Year2 loss is
unavailable/null**, not a penalty, zero or evidence of institutional failure.
Root preserves detailed raw logs/checkpoint/manifest/UI receipts separately.

This is not external authoring draft exhaustion. The host's cold-resume index
readiness check is defective. No institution source, scientific world law,
researcher/model/corpus identity or a1 evidence is repaired/relabeled here.

## Concrete mechanism and minimal repair

`LocalQwenNativeFactory` loads actual corpus documents before `Simulation.run` to
bind their identity. Portable checkpoint loading correctly retains that host's
configured corpus/providers and restores document statuses, but does not serialize
derived embedding tensors. `_prepare_paper_index(year>1)` previously rebuilt
the index **only when documents were empty**. A fresh process therefore has
nonempty verified documents plus no embedding tensor and skips reconstruction.
The older fixed-retrieval fixture never indexed that tensor and concealed this.

The change is confined to `Simulation._prepare_paper_index`: rebuild when either
documents are absent **or the derived embedding tensor is absent**. Missing
documents still load using the configured fixed corpus horizon, preserving exact
saved status rows/order/dtypes. `RAG.build_knowledge_index` remains unchanged:
its existing cache identity binds ordered document metadata/text, corpus, immutable
encoder model/revision, normalization and dtype. Neither retrieval ranking nor
scientific project/decision behavior is changed. Cold load/build captures/restores
scientific RNG, including when encoder construction consumes random numbers.
Warm in-process year1/index-ready behavior is unchanged.

## Forward-only a2 retry, no source-binding bypass

Use a **new clean source pin, output directory, plan, society session and response
journal**, rerunning year1 under that actual source. This is an infrastructure
retry of the declared5-researcher/seed1301/three-year/four-year-corpus pilot, not
statistical scale-up or another independent success replicate to pool with a1.
Keep all original strict model/corpus/source/seed/portable contracts intact.

Do not replace a1's `source_commit` metadata, normalize away a source mismatch,
rewrite its saved portable contract/cache binding or run changed source from its
frozen worktree. Do not silently transplant its journal/checkpoint into a2.
The extra initial baseline cost is explicit; a1 remains a negative infrastructure
execution and a2 receives its own actual observations/provenance.

The external designer may explicitly revalidate and reuse the **identical**
institution source against a2's new hash-bound authoring request. Its new response
must record prior source origin/hash and reuse, not claim a second invention.
The host does not mutate old response hashes or substitute old manifests as if
authored for the new request. UI consent and worker adoption again bind the new
exact staged request, with same-society continuity applying **within a2** only.
Any other runtime/UI infrastructure fix is separately disclosed in the new pin;
no causal attribution to this single fix follows from a combined retry.

## Verification before root authorizes retry

`tests/runtime/test_real_rag_cold_resume_v6.py` uses original native scientific
phases and **real** RAG corpus loading, embedding-cache construction/loading,
PyTorch similarity retrieval and top-k. Only a small in-memory dataset payload,
deterministic tiny encoder and HTTP replies are scripted; no model download or
new scientific inference is performed.

Checks cover both cache hit and missing-cache rebuilding, preloaded and empty
document providers, byte-identical tensor values and derived cache identities,
unchanged native document statuses, exact RNG preservation, zero HTTP/zero
response-cache entries for reconstruction, and actual year1→cold→year2/3 resume.
The continuous and resumed native worlds have identical full scientific
checkpoint state (including complete portable agent/RNG state and events), every
HTTP request payload and exact per-year response counts. Year1's scripted native
reference requires29 responses; no already completed year is requested again.

These are infrastructure QA, not live-Qwen success or proxy benefit. Root must
record the repaired live pin, new attempt, observed counts/losses, exact external
reuse and UI/adoption evidence separately before declaring the pilot complete.

## Accounting-double compatibility follow-up

The full corrected-source regression initially reports3 accounting compatibility
failures (`TestSubmissionRefactorCompatibility`) because its old `RAGFixture`
did not declare `document_embeddings` at all and its build method was a no-op.
Actual `RAG.__init__` has always declared the absent derived tensor as `None`.
The new production readiness check correctly uses that real contract; weakening
it with attribute-existence fallbacks would hide an incomplete test double.

The follow-up changes **only the accounting fixture/tests and this note**: the
double now declares an initial missing index and installs a deterministic NumPy
placeholder when built. Its retrieval remains deliberately scripted, not proof
of real embedding semantics. Its serializer omits that derived index exactly as
before. Existing accounting golden references are not updated or normalized;
they must pass unchanged. A focused lifecycle test checks missing→built→serialized
→cold-restored readiness. The production RAG/cache repair and running a2 source,
raw evidence, scientific world and binding checks are untouched.
