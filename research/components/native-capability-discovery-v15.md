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
The current source yields34 default registrations plus the conditional code ID.

Detailed cards cover:

- `native.researcher.work.v15`: arbitrary institution-authored work by the
  original fixed-model researchers, with authored object response schemas.
- `native.world.resource-transfers.v1`: conserving actual author transfers,
  not a host allocation rule.
- `native.domain.commands.v1`: actually registered action payload schemas,
  explicit role grants and persistent/native effect boundaries.
- `native.process.activity.v1`: explicit bounded delegate/control/iteration ABI.
- `code.python.v1`: arbitrary literal source, ports/state and isolated runtime ABI.

Every other registered identity remains visible, but its full interface is
explicitly **not** supplied by this first detailed-card slice. Operator-specific
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
