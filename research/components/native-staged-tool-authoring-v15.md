# Durable staged tool authoring v15

This is an opt-in engineering extension of the original-world institution
designer, not a new numerical research world or a finite menu of institutions.
The v14 one-shot adapter, factory default, request API and historical journals
are unchanged. Implemented functionality and SCRIPTED tests are not evidence
that the fixed local Qwen model has yet completed an actual authored native loop.

## Author interface and freedom

`utopia.optimization.native_staged_author_v15.StagedVocabularyGenerator` is a
generator callback for the existing `GeneratedMixedDesign`/native campaign
boundary. It takes an explicitly bound model, runtime image, directory,
`max_steps` (1–64) and `max_tokens` (512–8192). The default tool session is
12 calls of at most2048 output tokens; a protocol may explicitly choose other
bounded values. `make_local_staged_generator` uses the existing no-retry,
loopback-only transport contract through the additive
`LocalStagedQwenDesignerModel`; no paid/cloud provider or new dependency is
introduced. The v14 `LocalQwenDesignerModel` is not changed. Neither scientists
nor the designer model weights are trained.

The model emits one JSON object per call:

| Tool | Model supplies | Trusted host does |
|---|---|---|
| `inspect` | exact mechanism ID and local pointer, or any full-document pointer; optional string/list slice | returns exact current value or an explicit byte-cap descriptor |
| `edit` | atomic literal add/remove/replace operations | resolves exact IDs, checks paths, applies only those edits to a JSON shadow |
| `splice` | any existing string address, Unicode offset, deletion count and literal text | performs exactly that string splice; permits source in multiple short calls |
| `configure` | arbitrary declared factor/coordinate/logit fields | replaces only supplied distribution fields |
| `validate` | no policy arguments | invokes existing full static graph/source/ABI/distribution checks |
| `finish` | authored rationale | invokes the same checks and yields a definition only if valid |

New Python source, complete mechanism nodes, contract schemas, artifact types,
wires, schedules and process metadata can be authored through unrestricted
full-document JSON edits. Stable-ID addressing is an exact selector convenience,
not a mechanism whitelist. Distribution choices and continuous coordinates use
the existing literal stable-ID IR, including rejection of ambiguous,
branch-dependent pointers. Empty distributions are legal for a deterministic
single-draw blackbox proposal; they are not a new restriction on nested methods.

A draft can temporarily have an invalid graph or Python body while the model
builds the missing parts. Invalid **paths** reject the entire edit transaction;
invalid **finished systems** cannot produce a candidate. Every accepted edit
also returns static diagnostics, so the model can repair its own draft without
spending a native trial. An explicit `finish` remains required: a valid draft
is not automatically dispatched. Explicit retention is legal; exhaustion is an
invalid generation, never a silently supplied baseline. No novelty, fairness,
scientific-merit or adoption veto is added.

No generated source is evaluated on the host. Static AST/schema validation is
not a sandbox/native execution proof. Actual execution retains the original
no-network pinned container and original native scientist simulation. The author
uses **zero native probes**; subsequent campaign evaluation is separately charged.
The pinned operator image is checked in every reachable executable design.

## Bounded context without making the design space smaller

The initial prompt includes the exact loss, complete current node index and
top-level type/hash descriptors, all own scalar outcomes/failures/update reports,
the technical Python/port/distribution ABI and the tool schema. It does **not**
duplicate the full parent source and protocol bodies. The model can request any
exact current subtree with `inspect`, including the whole document when it fits.
Only the last full tool response is repeated, while every prior step's status,
exact addresses, scalar operands, raw-action hash, current-draft hash and
technical errors remain visible. Arbitrary prior literal bodies have explicit
type/length/hash descriptors rather than being repeated. These
omissions are declared, not an undisclosed tail truncation or cross-arm history.

An individual tool response over96000 UTF-8 bytes returns its exact type, length,
hash and explicit `value_included:false`, with instructions to inspect a narrower
field or string/list slice. The exact value is still in the journalled draft
reconstruction. Prompt cap240000 bytes, draft cap512000 bytes and aggregate
80 literal base edits are explicit finite implementation bounds. A too-large
prompt terminates authoring without a model call; it is not silently truncated.
The existing downstream compiler's source/support constraints still apply.

## Prospective conversational correction after a1

Actual a1 exposes a generic agent-interface failure: the model repeatedly
requests the exact same successful inspection of an unchanged draft, even
though each receipt and remaining budget are correctly present in the JSON
context. Those frozen source/raw records are not edited or silently retried.

A separate source revision keeps JSON action/context schemas but presents the
last authored action as an actual assistant conversational turn, followed by a
user turn explicitly identifying its **already returned** tool receipt. The
source-bound pure `build_conversation` function reconstructs these exact provider
messages. Current budget and the number of repeated successful inspections of
the unchanged draft appear at both ends of the context. The final-call notice
explains that only a valid explicit finish can yield a candidate.

These are technical progress cues, not an institution algorithm, a forced edit
or a novelty policy. All six tools remain legal after repeated inspection;
explicit retention remains legal. The host neither supplies a candidate nor
automatically finishes. The additive transport still performs one pinned-model
verification GET and one fixed loopback POST per dispatched call, with no
network retry, and archives the exact dialogue/payload/raw reply. Cold replay
checks that archived dialogue against the deterministic prompt reconstruction.
SCRIPTED tests verify the conversational and budget contract, not that the next
actual Qwen pilot will succeed.

A further **prospective** role-hierarchy correction puts the fixed source-owned
authoring instructions and technical ABI directly into the SYSTEM message,
rather than leaving them as strings inside the user JSON context. That SYSTEM
message explicitly says to minimize the exact numeric `exact_loss_spec` in
session data. World, history, generated source, labels and tool-result strings
remain untrusted observations; similarly named fields cannot replace the
trusted protocol. Current-call/budget/next-action narration is natural user-turn
text outside the observation JSON. Adversarial tests check that observation
strings claiming new SYSTEM authority never enter the actual SYSTEM message.
This correction does not add an institution algorithm, constrain which candidate
is scientifically acceptable, or change the fixed researcher model. Frozen
a1/a2 messages retain their original source-specific construction; an optional
future revision is not silently relabelled as having run in either pilot.

## Journal, crash and replay contract

Every exact campaign generation gets `generation-<request_sha256>/`:

```text
request.json                 exact request/provider/settings/protocol binding
step-00.started.json         exact prompt/schema/draft/previous-step hashes + intent
step-00.completed.json       exact raw/parsed reply/transport + deterministic tool result
...                         one intent per bounded model call
response.json                selected finish or generation failure + all receipt hashes
```

The protocol identity hashes this adapter, the stable-ID compiler, the existing
transport adapter, the action schema and instructions. Native world/source
identity remains in the caller's existing bound campaign request and plan.
All writes are atomic and each generation has an exclusive nonblocking writer
lock. A started dispatch with no completed receipt consumes its step and is
never redispatched. Its reply and model-call cost remain unknown. This is not
an exactly-once HTTP claim: a reply can have occurred before interruption.

Completed steps distinguish applied tools, rejected tools, valid finish,
transport failure and invalid raw/parsed responses. Errors contain technical
diagnostics only. The next prompt is deterministically reconstructed from the
request and previously receipted steps. Cold replay checks exact prompts, raw
actions, immutable provider/settings/source, each pure tool transition, every
draft hash and the selected complete definition. It does not trust a self-hash
as evidence that a modified compiler output was truly authored. Extra dispatches
after finish, orphan completions and noncontiguous intents fail closed.

`initial_draft`, `transition`, `build_prompt` and `compile_draft` are pure
inspection surfaces. `replay_staged_generation` requires an existing terminal
journal and never dispatches a model or fills missing files. The native kernel,
loss compiler, optimizer, technical validity and optional adoption remain separate.

## Read-only Foundry chronicle

`project_authoring_trace(directory, allowed_requests=..., provider_binding=...,
settings=..., authoring_protocol=...)` emits
`scienceutopia.authoring-chronicle.v15`, explicitly scoped
`observed-local-journals-not-independent-audit`. Callers should pass exact current
campaign requests (including pending), operator binding, step/token settings and
protocol identity to reject foreign journals. Unknown pending replies expose
null tool/result/cost, not invented code or zero cost. Completed steps preserve
literal authored actions, exact applied edits/source/wires and diagnostic
results. There is no usable candidate before `finish`. Corrupt/missing observations
are warned about; an observational UI does not substitute for independent replay.

## Verification boundary

`tests/optimization/test_native_staged_author_v15.py` uses only explicitly
SCRIPTED model replies. It covers exact inspection, arbitrary new topology,
temporary graph/source errors, model-authored repair, source chunking, free
distributions, no-host-execution, pinned images, failure/null behavior, bounded
steps, interrupted intents, cold replay, raw mismatch, rehashed tampering,
small original-parent initial context and read-only UI projection. These tests
also run two original native Simulation worlds with SCRIPTED corpus/replies:
staged tools finish both candidates and the second generation receives the first
world's measured loss, without a manual candidate inbox. This is software QA,
not Qwen institution authorship or a new scientific result. These tests
do not establish actual Qwen authorship, native scientific benefit, optimizer
superiority, novelty or recursive improvement of the author.
