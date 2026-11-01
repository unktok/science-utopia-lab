# Optional external institution designer, unchanged native researchers

This optional adapter is software, not an authorization to run a new campaign.
No live external authoring, provider API calls or native experiment were run to
implement it. A user may keep all designers local; this route can remain unused.
An external/Codex designer must never be reported as Qwen-generated invention.

## Request and response contract

`ManifestInbox(directory).generate(**kwargs)` implements the existing designer
model interface without calling a model. It preserves every supplied prompt,
system prompt, seed context, response schema and setting in a canonical JSON
request document:

```json
{"schema":"scienceutopia.external-manifest-request.v5","request":{}}
```

The real `request` contains the actual nonempty generation arguments. The SHA256
of the entire canonical document names `requests/<request_sha256>.json`. If
`responses/<same_sha256>.json` is absent, it raises `ExternalAuthoringPending`
with exact request and response paths. This is a waiting state, not an invalid
candidate, numerical penalty or failed native observation.

An authorized external author reads the saved request and supplies exactly:

```json
{
  "request_sha256":"the exact request hash",
  "manifest":{},
  "authoring":{"kind":"codex-agent","identity":"recorded author or tool"}
}
```

The real `manifest` must be the complete requested scoped IR: rationale, freely
chosen nodes with exact Python bodies/ports/schemas/parameters/state schemas,
and all explicit exports/wires—not a catalog choice or a host-supplied policy.
`authoring.kind` may also be `external`. Additional authoring metadata is
retained, but it is self-reported provenance, not authenticated provider identity.
No extra top-level response fields are allowed. Nonmatching request hashes,
symlink responses, invalid envelope fields and changed consumed responses fail
closed. Structural/code validity is judged by the existing bounded proposer,
so invalid drafts remain exact technical receipts with null loss.

`consumed/<sha256>.json` binds the request, entire response, exact manifest and
author metadata. The adapter never imports, executes, patches or repairs Python
source. Existing source compilation and isolated no-network Docker execution
remain mandatory. `audit_manifest_inbox` independently reopens exact hashes
without model calls or file changes; it audits inbox provenance only, not the
whole native candidate. A whole-campaign external request -> IR -> compiled
patch -> checkpoint/native-loss audit is still required before reporting a
live result. Existing Qwen-designer SQL-cache audits must not be reused to claim
replay of this different authoring provider.

## Optional native driver

`scripts/run_external_native_objectives_v5.py` uses a separately bound
`scienceutopia.external-native-objectives.v5` / `kind=externalnative-v5` protocol.
Two explicit losses have separate `NativeDesignCampaign`s and external inboxes.
One actual native baseline is shared through the existing independently checked
adoption mechanism; it is not counted as independent replication. Researchers
remain fixed local Qwen3:8b with the existing five-author native factory,
two-year default horizon, seed1301, portable checkpoints, code/HTTP recording,
the supplied corpus cache and mandatory shared inference flock.

The route intentionally uses complete-IR `NativeBoundaryRegionProposer`, not
extra staged graph/code requests. Current a2 prompt projections have a known
deep-container diagnostic representation; the driver explicitly warns external
authors that these diagnostics are NOT the native ABI and gives the correct
flat port -> envelope-list -> payload -> conferences/list/papers/list/reviews
paths. Code must obey real domain interfaces and the full chronological probe,
not program against omission-marker dictionaries.

A CLI invocation can prepare pending requests for **both** arms. One missing
response never blocks preparation for the other arm. On rerun, existing
baseline/controllers/prompts/consumed responses are reused, exact candidates
are executed in the original researcher world, and the next external request
uses the actual resulting objective feedback. Native execution only occurs
after a full valid manifest and isolated probe; no source is executed directly
from an unvalidated inbox. Three technical drafts per proposal are the default,
not an unbounded interactive repair loop. The output directory has a one-writer
process lock. A pending external request creates `progress.json` with status
`waiting-for-external-authoring` and **no terminal completion receipt**.

Run only after explicit authorization/preregistration from a clean pinned
experiment checkout, with startup `PYTHONHASHSEED=42` and the repository's
uv-managed `.venv/bin/python`. The CLI requires output, corpus cache, two loss
paths and inference-lock path. Reuse exactly the same arguments on resume;
changed source/protocol/world bindings fail closed. This driver has not been
used for a live experiment by this implementation task.
