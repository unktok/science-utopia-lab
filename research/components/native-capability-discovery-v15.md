# Read-only native effect ABI discovery v15

`utopia/system/native_capability_catalog.py` makes existing implementation
interfaces discoverable to an institution author. This is a catalogue of
**trusted effect ABIs**, not a finite list of scientific institutions, activity
types, policy algorithms or suggested tasks. Discovery does not install a node,
choose an instruction, grant a privilege, add a connection or change a candidate.
All use still requires explicit authored SystemSpec edits and real execution.

## What is indexed and what remains incomplete

The implementation/version index is derived from the actual default native
registry constructed for an empty graph. This registers closures but invokes no
handler. An empty graph is important: constructing the registry of a candidate
containing code could otherwise create a Docker executor. Conditional
`code.python.v1` registration is explicitly listed without constructing one.
Each identity says whether it has a detailed contract or is identifier-only.
The November12 source yields35 default registrations plus the conditional code ID.

Detailed cards cover:

- `native.researcher.work.v15`: arbitrary institution-authored work by the
  original fixed-model researchers, with authored object response schemas.
- `native.world.resource-transfers.v1`: conserving actual author transfers,
  not a host allocation rule.
- `native.domain.commands.v1`: actually registered action payload schemas,
  explicit role grants and persistent/native effect boundaries.
- `native.process.activity.v1`: explicit bounded delegate/control/iteration ABI.
- `code.python.v1`: arbitrary literal source, ports/state and isolated runtime ABI.
- `native.world.claim-verification.v1`: completed native count-assertion checks,
  not an independent scientific-truth verifier.
- `native.world.review-inputs.v13` and `native.phase.review.with-routing.v13`:
  actual current submissions/eligibility and authored eligible review tasks.
- `native.phase.open.v1`: the actual post-opening world observation, including
  native agents, projects, resources and in-flight paper state.
- `native.world.researcher-context.v1`: arbitrary addressed institutional
  information delivered to original researchers without forcing their actions.

Every other registered identity remains visible, but its full interface is
explicitly **not** supplied by these ten detailed cards. Operator-specific
`registry_extension` plugins, live actor/artifact identities and world data are
also excluded. Coverage and omissions are emitted as data; unknown contracts
are not invented. Native phase laws and trusted privilege boundaries are not
made arbitrarily writable by listing them.

## Inspect without touching the design

The existing author `inspect` tool accepts `resource`, defaulting to `draft`:

```json
{"tool":"inspect","resource":"capabilities","path":"/index"}
```

For details, use an exact JSON pointer into the read-only catalogue:

```json
{"tool":"inspect","resource":"capabilities","path":"/cards/native.researcher.work.v15"}
```

`path:""` reads the full catalogue including the complete index and detailed
cards. Exact pointer escapes, string/list slicing and existing response byte
bounds apply unchanged. Candidate mechanism selectors are invalid for this
separate resource. `edit`, `splice`, `configure` and `finish` cannot target it.
The compact complete index is also present in each initial/continuing author
prompt; full ABI cards are supplied only when inspected. At the development
source the complete index is under20KB and the full catalogue under45KB.

An institution absent from the seed graph can therefore discover the generic
researcher-work effect, read its actual request/response/port/parameter contract,
then explicitly author its own arbitrary task producer, consumer and wiring.
No task or default node is supplied by discovery. No hypothesis/review/experiment
activity enum is introduced. Additional effect privileges still require explicit
trusted implementation work; arbitrary generated source never becomes a host
plugin merely because it appears in a graph.

## Shape versus semantics, privileges and costs

Cards identify actual validator callables and source-file SHA256s. The index is
checked against actual registration, and domain action payload schemas are read
directly from `default_actions().actions`, not copied from an institution menu.

Shape schemas are labelled as shape schemas, not represented as full proofs.
For example, researcher work additionally requires a non-whitespace instruction,
an actual original author, available artifact references, correct causal value
addresses, a bounded reference-free/regex-free object schema and technical byte
limits. A JSON Schema integer check alone is not the exact Python `int` check
used by the runtime. These remaining semantic constraints are enumerated and the
actual validators remain authoritative. Discovery does not execute the checks
against a fabricated live world.

Researcher work costs one original-scientist call per actual task, bounded by
the authored per-invocation cap; explicit process iterations multiply those
calls. Responses are data, not published papers, measured experiments, minted
resources, review scores or project overwrites. Transfers conserve existing
balances and require exact representability. Domain actions require explicit
role grants. Code has arbitrary Python freedom inside its existing isolated
executor, not host/network access. Process control grants no privilege beyond
its explicitly chosen registered delegate.

## Source, safety and evidence

The catalogue source hash enters the staged-author protocol binding. Detailed
cards hash actual validator files, and the full catalogue records registry
source hashes. The caller's pinned campaign source remains the authority for
the entire native runtime and any operator plugins. Tool actions/results/draft
hashes and new prompt contents use the existing exact durable journal/replay.
Read-only discovery preserves the candidate's exact pre/post draft hash.

SCRIPTED tests compare the index with actual registration, cards with actual
validators/boundaries, action schemas with actual registries and source hashes
with files. They explicitly fail on Docker construction, model/session creation
or native-handler invocation. Author integration tests discover the unseeded
researcher-work capability and replay its receipt without mutation or inference.
This prospective implementation is not relabelled as used in frozen a1/a2 and
does not establish actual-Qwen use or beneficial new scientific institutions.

## November12 information interface extension

The closed61a1753 source indexes the opening/context implementation identities
without detailed cards for those two interfaces. That source is unchanged.
The prospective397b49b cards expose actual existing ports, top-level observation
shape, arbitrary JSON delivery envelopes, real recipient requirements and
storage/consumption/timing boundaries. There is no new trusted effect, message
algorithm, recommended topic, node, wire or validity requirement.

An author can inspect `/cards/native.phase.open.v1` and
`/cards/native.world.researcher-context.v1`, then explicitly create its own
protocol, computation and routes. The code envelope requires actual actor IDs;
its payload does not require an `instruction` key or a predetermined institution
vocabulary. Observations are post-stage records, not automatically refreshed
live state. A later message cannot retroactively change an earlier decision.
Context storage, presence in a later eligible native prompt, researcher choice
and completed output remain separate evidence. Not every model call consumes
this stored context; the actual source/consumer trace is still required.

The actual prospective catalog is42453 JSON bytes and the index10774 bytes,
within the unchanged45KB/20KB caps, with26 identities still identifier-only.
All89 checks pass9.04s, including actual original-Simulation observations at
78 phase boundaries over six years with scripted HTTP/corpus, arbitrary native
context delivery and public author inspect/replay. [Exact verification](../results/native-information-capability-discovery-v1.json).
The first run had a missing pytest fixture import and an invalid uppercase
scripted SystemSpec ID; those test setup errors are corrected, not passes.

This change repairs a concrete discoverability limitation, not a proven cause
of earlier author behavior. Existing61a1753 evaluation and5925d5b controls stay
frozen. Any new actual-model design campaign needs its own clean source-bound
real-backend readiness check; these software results do not replace it.
