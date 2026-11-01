# Objective-visible redesign in a persistent native society

## Scope

`utopia.optimization.native_society_design.NativeSocietyDesignSession` connects
actual native scientific intervals to arbitrary externally authored design
patches, explicit consent, durable installation and subsequent feedback. It
does not choose a policy, invent a loss or interpret before/after observations
as causal superiority. Researcher LLM weights are unchanged; responses to new
inputs are not frozen.

The original actors, projects, corpus, paper production, review, funding and
random state remain the forward world. Typed activity contracts are opt-in
extensions, not replacement toy dynamics. The proposer can change parameters,
source, protocols, nodes and wiring within the native runtime contract. Technical
validity, operator authorization and scientific merit are distinct.

## Executable lifecycle

1. `observe(simulation)` accepts an actual synchronously saved annual boundary.
   Review/decision/message metrics cover the new interval; resources and active
   author counts are boundary stocks. It archives the complete inspected society.
2. `author(proposer, ...)` exposes the current graph, declared LossSpec, previous
   measurements and adoptions. The proposer supplies the actual complete patch;
   the controller fills in no missing algorithm or semantic connection.
3. `stage(...)` binds the candidate, source provenance, parent observation,
   complete checkpoint and kernel, actual native domain and explicit memory/
   pending-message reconciliation to one request hash. No source is run here.
4. `confirm(request_id, confirmed_request_sha256)` records consent for exactly
   those bytes. Consent alone does not execute a researcher or install a system.
5. `adopt(simulation, ...)` rechecks the saved boundary and performs the existing
   atomic `commit_native_design` transaction. An origin field binds the installed
   migration receipt to the exact session/request. The same actors continue.
6. A later `observe` measures actual subsequent activity; the next proposer sees
   that feedback. `cancel` records a reason without erasing evidence or assigning
   a failed candidate an artificial loss.

## Persistence and recovery

Persistence and adoption share `Simulation.capture_checkpoint_state`, the complete
canonical state serializer. This closes a review-discovered gap in which extra
actor fields, RAG state or native overlays could change without invalidating a
partial stale-state check. Session identity binds actual model, corpus, native
configuration and physical response cache, not just a caller's label. Observed
event prefixes and acknowledged receipts must remain in the current society;
foreign or rewound histories cannot inherit a completed adoption.

The session uses a private hash-chained journal, one-writer locking and atomic
fsynced writes. If the checkpoint commits before its journal acknowledgement,
reopening reconciles the actual receipt without repeating installation. Adoption
status is complete only after restoring the operator-selected saved checkpoint,
verifying the original-rooted migration chain and matching the exact request.
An absent checkpoint remains pending even if a journal claims acknowledgement.

New observations additionally pin the binding-specific ordered response prefix.
If a later year stops after committing responses but before its checkpoint,
only idempotent observation of an already observed and adopted boundary may
accept an intact prefix with a verified extra tail. Only the physical response
count is normalized for that comparison; every scientific field still matches.
New observation, adoption and direct migration remain strict. Old observations
without the proof cannot use this prospective recovery path. Scripted native
stop-after-code/cold-resume tests compare complete scientific state to continuous
execution and retain ambiguous physical attempts separately from committed effects.

## Loopback UI boundary

`scripts/serve_native_lab.py --society-config ...` accepts an operator-owned JSON
configuration containing `directory`, `founding_system`, `loss_spec`,
`world_binding` and `checkpoint_directory`. Existing token/same-origin/loopback
restrictions apply. Browser calls cannot choose an arbitrary filesystem path or
submit executable source to this endpoint.

- `GET /native-api/society`: actual session projection.
- `POST /native-api/society/confirm`: exact request consent only, HTTP202 pending.
- `GET /native-api/society/requests/{id}`: saved-receipt verification.

The existing English cyberpunk lifecycle UI distinguishes old reset-world search
from this continuity view. A labelled fixture sends no consent POST. Pending is
not displayed as adoption or scientific completion; a retained completed request
is re-verified after the pending field becomes null.

## Evidence boundary

Original native QA with scripted corpus/replies covers multiple adoptions,
changed future researcher inputs, cold restart, cancellation, wrong consent,
foreign/rewound lineage, unsaved mutations and commit-before-ack recovery.
The actual Qwen pilot, its preserved first failure and independent audit are
separate evidence. See the campaign protocol and result records in the index.

This implements continuing institutional redesign, not automatic merit-based
promotion, causal benefit, pathwise differentiation through the native world,
new scientific actor ontologies or a designer improving its own algorithm.
