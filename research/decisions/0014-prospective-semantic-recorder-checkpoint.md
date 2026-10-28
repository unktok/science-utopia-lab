# Decision 0014: Record semantic events prospectively at the producer boundary

- Status: accepted prospective vertical slice
- Date: 2026-10-28
- Scope: future simulator campaigns; report-only semantic instrumentation

## Context

Decision 0013 validates typed semantic event bundles after they exist. That is
not sufficient evidence that a future simulator recorded claims, evidence,
verification, replication, and correction when those events occurred. A
post-hoc extractor could silently infer meaning from paper or review text,
discard negative attempts, fill unknown lineage, or combine records produced
under different system/model configurations.

Long simulator campaigns also need a restart boundary. A partial file,
truncated stream, replaced configuration, or modified historical event must not
be accepted as a valid continuation.

## Decision

Add a default-disabled prospective recorder with an explicit producer API:

- `append_claim`
- `append_evidence`
- `append_verification`
- `append_replication`
- `append_correction`

The producer supplies the event type, identity, simulation step, actor,
institution, source event IDs, and exact typed payload. The recorder supplies
only the contiguous sequence, configured run/producer identity, family schema,
and integrity envelope. It has no API that accepts a paper, review, prompt, or
other document and does not infer semantic values from text.

Every proposed event is validated together with the complete prior prefix
before it is appended. Existing semantic-instrumentation v1 checks therefore
apply at event occurrence: forward references, missing causal sources, claim
version gaps, orphan evidence, unresolved replication lifecycle, implicit
missingness, and invalid correction propagation fail before a durable write.

## Identity and integrity

An enabled recorder requires immutable identifiers for the run, producer,
bundle, recorder, system fingerprint, and model fingerprint. Fingerprints are
lowercase SHA-256 values over campaign-defined canonical system/model
manifests. Their manifest construction is outside this recorder, but their
exact values are fixed in the stream header and every event envelope.

The JSONL stream is single-writer and append-only:

1. the header hashes its canonical body;
2. the first event entry points to the header hash;
3. every later entry points to the preceding entry hash; and
4. each entry hashes its immutable envelope and typed event.

After each append, the recorder atomically replaces a separate checkpoint. It
binds the header hash, event count, tail hash, last event/sequence, stream byte
length, and whole-file SHA-256. The checkpoint itself is canonically hashed.

Resume rereads and validates the full stream, semantic lifecycle, all identity
fields, the hash chain, and the checkpoint. A missing/torn record, stale
checkpoint, changed fingerprint, truncation, out-of-band append, or historical
edit is an error. V1 intentionally provides no automatic repair or
uncheckpointed-tail recovery; an operator must preserve the artifacts and
resolve the incident outside the recorder rather than silently redefining
history.

## Missingness and ground truth

The recorder preserves the instrumentation v1 observed/missing wrappers.
Unknown lineage or probability requires an explicit missing reason and detail;
the recorder never fills a value. Synthetic classifications require observed
synthetic ground truth. An experimental shadow stream requires ground truth to
be explicitly missing and cannot embed a synthetic oracle.

## Authorization boundary

The only accepted use is `instrumentation_use: report_only`. Headers and
append receipts state `optimization_input: false`. There is no LossSpec,
ranking, candidate-selection, veto, or optimizer adapter. The recorder is not
wired into the current simulator, runner, v1.1 study manifest, or held-out
suite. Enabling it in a future campaign requires an explicit versioned config
and caller-selected output path.

The current metric-conditioned v1.1 LossSpecs, design space, seeds, manifests,
held-out data, and running outputs remain unchanged and unconsumed.

## Consequences

- A future mechanism can emit auditable semantic primitives without choosing a
  scalar epistemic objective.
- Restart preserves exact run/system/model identity and refuses ambiguous
  history.
- Negative, missing, correction, and lineage records are explicit producer
  obligations rather than post-hoc guesses.
- The synthetic integration fixture proves API, checkpoint, resume, and
  tamper-detection behavior only. It is not an experimental result.

V1 is deliberately single-writer. A future multi-process producer would need a
separate coordination protocol and cannot share this stream by convention.
