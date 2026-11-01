# Explicit structural authoring on the original native world

This optional authoring interface exposes complete institution source, schemas,
composition and wires. It is not a fixed institution catalogue. It adds no
scientific quality/fairness floor, topology reward or mandatory institution ID.
The arbitrary `SystemSpec`/JSON-patch APIs and external inbox remain available.

## Exact integration ABI

`native_authoring_contract(system)` returns an exact source-preserving copy of
the current system, its fingerprint, resolved execution-node IDs, flat sandbox
ABI and mixed-search parent-binding explanation. It executes no source and
redacts no parent source. A caller that requires withheld-parent authorship must
apply its own explicit information policy before presenting this view.

`explicit_graph_patch(parent, *, remove_nodes=(), put_nodes=(), disconnect=(),
connect=(), schedules, agent_types=None, artifact_types=None, metadata=None,
rationale='')` returns an ordinary `scienceutopia.system-design-patch.v1`.

- `put_nodes` are COMPLETE canonical mechanism dictionaries, not partial fields.
  Existing IDs replace in place; new IDs append in the given order.
- `disconnect` and `connect` are COMPLETE canonical connection dictionaries:
  `source_mechanism`, `source_port`, `target_mechanism`, `target_port`, `channel`,
  `latency`. A requested disconnect must exist exactly. No edge is inferred.
- `schedules` is the COMPLETE final array of `{mechanism_id,phase,trigger}`.
  Removing nodes does not implicitly delete their schedules or incident wires.
  The final atomic candidate must satisfy the existing structural validator.
- Optional type arrays and metadata replace their complete corresponding field.
  The helper never prunes unused types or chooses an execution order.
- Node ports are complete `{port_id,channel,artifact_type,required}` contracts.
  Wires must resolve to compatible channels/artifact types. A payload schema is
  not an endpoint object and does not replace these transport declarations.
- Python nodes supply literal source, complete input/output payload schemas,
  state schema and the exact pinned runtime image. Process wrappers retain the
  explicit delegate contracts; no source executes on the host.

The helper performs no host action registration or missing-connection repair.
Technical graph/source failures are not scientific losses. Some contracts
(capabilities, actual identities and runtime behavior) additionally validate at
the real native execution boundary, just as with arbitrary raw patches.

### Mixed search: two different parent scopes

A generator used by `NativeAdaptiveDesignCampaign` returns:

```python
{
    'base_patch': complete_patch_bound_to_request_parent_or_None,
    'factors': [
        {'id': 'free-choice', 'kind': 'categorical', 'choices': [
            {'id': 'one', 'operations': operations_relative_to_compiled_base,
             'provenance': explicit_provenance},
            {'id': 'two', 'operations': other_operations_relative_to_compiled_base,
             'provenance': explicit_provenance},
        ]},
    ],
    'continuous': [],
    'provenance': explicit_provenance,
}
```

`base_patch.parent_fingerprint` binds the exact request parent. Every factor's
operations apply after that base patch, in declared factor order, as one atomic
candidate transaction. `factor_operations(compiled_base, choice_patch)` checks
the correct post-base parent and extracts operations without implicit rebasing.
A literal identity choice is simply `operations: []`; no artificial patch is
needed. All factor assignments must be valid; choices are not filtered/remapped
after sampling. Continuous JSON pointers must exist in every compiled factor
assignment, with explicitly declared bounds. Integer fields need an explicit
discrete choice, not an implicit cast of a continuous sample.

History, exact source, grammar, distributions and seed/provenance are handled by
the existing durable campaign/inbox. This helper neither generates a catalogue
nor modifies the objective, strategy update, draw budget, resume or incumbent
rules. Freely authored raw patches may change institutions, algorithms,
protocols, domain/action compositions and processes beyond this optional syntax.
The original researcher/project/paper/RAG/resource forward-world contract, not
a catalogue of original review/funding institutions, defines containment.

## Sandbox Python and real native action ABI

The entrypoint is `step(context)`. Inputs are flat
`context['inputs'][PORT] -> list[envelope]`, never indexed by node ID.
An envelope has an object `payload`, actual `actor_ids`/`artifact_ids` and
transport provenance. Return exactly `{'outputs': {every_output_port:
[{'payload': {...}}]}, 'state': {...}}`. Optional output lists may be empty;
required outputs must actually emit. Source is literal sandbox data; no helper
imports or evaluates the authored function.

Original observations expose `world['ecosystem']['agents']` and
`world['papers']['papers']`. Nested conference storage is
`world['conferences']['conferences']`, a list; each conference has a
`submitted_papers` list and `reviews` mapping. These are actual native records,
not synthetic scores or writable privileged state.

Native commands use an explicitly wired `native.domain.commands.v1` receiver
with capability grants/type declarations and envelopes containing
`{schema:'native-domain-command-v1', command_id, actor_id, action, payload}`.
Commands act on actual original researcher projects/context/resources only via
declared actions. `native.project` requires a complete actual-author assignment:
`actor_id`, `direction` (`topic,focus_areas,years,keywords,related_topics`),
`detailed_focus`, `reason`, `project_start_year`, `project_end_year`.
Effects are atomic, identity-checked and persistent. No native paper IDs are
minted by an institution to fake original paper production or quality.

## Transparently developer-authored structural example

`structural_agenda_patch(parent,image_id,planner_source=...,adapter_source=...,
assigned_authors=1)` is an engineering seed, NOT an LLM discovery, novelty claim
or objective-conditioned improvement. The caller may supply any source bytes.
It replaces the two-node v7 open-source region with:

```text
actual world.open.world
    -> agenda-planner: arbitrary Python, new research-agenda-v8 payload
    -> agenda-commands: arbitrary Python, new institution-command-v8 payload
    -> agenda-effects: explicit capability-granted actual native actions
    -> world.research: explicitly authored state-effect prerequisite
```

This changes the actual graph from **19 nodes/27 edges to 20 nodes/28 edges**.
Both Python nodes have functional roles: one forms real-author project agendas,
the other maintains a custom institutional actor/records and translates those
agendas into actual native project/context commands. The original scientific
activities and original numerical selection route remain only for this example's
backward-compatibility QA; generated designs are not required to retain that
institutional topology. No decorative node-count requirement is introduced.

The example explicitly authors every added/removed edge and schema. Only after
its full dataflow is given does `compile_dependencies` calculate topological
schedules. That compiler does not invent an algorithm, source or effect wire.

## Verification and scope

`tests/system/test_native_structural_authoring.py` checks source preservation,
strict explicit editing/no repair, post-base factor bindings and arbitrary code.
Its integration test executes the original **six-year** scientific lifecycle
with actual Docker code execution, scripted researcher HTTP and fixed corpus.
The first authored setting makes six actual project updates and a second makes
twelve, reducing original first-year direction requests from three to two.
Real context reaches native researcher prompts. A crash after year3 effects,
followed by cold reopening, exactly matches the uninterrupted scientific and
native state. These tests are engineering evidence, not actual Qwen responses,
new native-world optimization results or institutional-benefit evidence.

Actual objective-conditioned authorship and measured exploration belong to the
separately pinned v8 runner/audit. This reusable example cannot substitute for
those actual native-Qwen worlds or be reported as autonomous discovery.
