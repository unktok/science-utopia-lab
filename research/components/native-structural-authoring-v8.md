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

## Fresh saved-file authoring validation and the a1 binding failure

The first a1 manifests were invalid before ANY scientist world/reply: authoring
tooling passed the saved request through JavaScript, which turned integral
floats such as `1.0` into integers such as `1`. This changed the parent canonical
fingerprint from `88912a72e5d2f30eace4a595548bcce0ee828bb8e1c40301c438daf13abaa2f4`
to `af6228e18f41c8051607f6c5dba6c97d59b0d794baf4ce285e05488b3f980bdc`.
The previous author claim of exact saved-request validation was therefore wrong:
only a numerically normalized in-memory parent had passed. The host correctly
rejected the authored patch. This is authoring error, not a host repair or a
scientific result. Consumed a1 files and both null failures remain unchanged.

The new pure `utopia.optimization.native_external_validation` function
`validate_saved_generated_response(request_path,response_path,learning_rate=.1)`:

- Freshly reads BOTH saved files using Python's strict JSON decoder, preserving
  integral float types; rejects duplicate keys, nonfinite numbers, symlinks and
  identity changes. It does not accept an earlier in-memory object instead.
- Validates the exact request/response binding, actual original parent, supplied
  loss, seed, declared batch size and optional explicit learning rate.
- Constructs the existing `GeneratedMixedDesign`, compiling every REACHABLE
  conditional factor assignment and parsing literal source without execution.
- Produces exactly the declared number of deterministic in-memory design draws
  using the actual request seed/version/history. It reports their fingerprints,
  probabilities, source hashes and any null technical errors without replacement.
  These are design draws, NOT native scientific forward observations.
- Reports saved-byte hashes, canonical hashes, exact parent fingerprint and
  compiler-file hashes. Either file changing during validation aborts. A later
  consumer must independently recheck the reported file identities.
- Writes no files, consumes no inbox and never rebinds/normalizes/repairs a
  response, imports authored source or calls native worlds, Docker or models.

To validate an external file with an unchanged older experiment source pin,
load the helper by path while imports resolve against the pinned worktree:

```python
# Run Python from the clean pinned experiment cwd with PYTHONPATH=.
import importlib.util
spec = importlib.util.spec_from_file_location('external_validator', helper_path)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
report = validator.validate_saved_generated_response(request_path, response_path)
assert report['status'] == 'passed'
# Independently preserve/recheck the exact reported file hashes before consumption.
```

This author-side preflight is not inserted into the immutable 425ec10 source.
A separate a2 amendment reuses that SAME correct source pin and initial literal
algorithms, with explicit prior-failure provenance and a newly authored correct
parent binding. It retains the SAME eight-actual-world maximum across attempts;
a1 consumed no worlds. Freshly saved a2 responses passed validation using the
actual 425ec10 classes, not a normalized request. No successful native-world
outcome or algorithmic improvement is implied by this preflight.
