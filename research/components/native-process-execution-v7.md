# Native process execution v7

`utopia.system.native_process` changes the process, not just institution knobs.
It operates on the existing native registry; it is not a simplified numeric
replacement world. Default `NativeScienceKernel` registers it in production.

## Data-authored dependencies and activities

`compile_dependencies(spec, dependencies, priorities=..., detach_serial=...)`
accepts dependencies for every node, preserves actual typed data edges, rejects
same-period cycles and computes a deterministic topological schedule. With
`detach_serial=True` it removes only the old native stage `after`/`next` chain,
not arbitrary source ports. Direct source ABI is never silently rewritten:
wrap a source activity before adding independent dependency controls. A producer
must actually emit its native `next` or process-completion value.

`controlled_activity(node, count=..., limit=..., control=..., guard_path=...,
count_path=..., until_path=..., initial_state=..., missing_control=...)` stores
the full delegate spec as data. Arbitrary registered Python, LLM, tensor,
domain and trusted custom activities can participate. Generated Python stays
inside the pinned networkless executor; it is not imported/evaled in the host.

- Typed control payloads come from actual connected mechanisms. Boolean guards
  and integer iteration counts are source-authored data, not an expression menu.
- Bounded repetition carries the delegate's actual JSON state. `until_path`
  terminates on an explicit boolean state field. Limits are technical compute
  budgets, not optimization vetoes. Invalid counts fail, never silently clip.
- Guarded/skipped/already-completed bodies need not have unused required inputs.
  Before an enabled body call, its original required inputs must really exist.
- `missing_control='wait'` explicitly skips without fabricated effects until
  a causally bound delayed message arrives. `'error'` makes the input required;
  missing input blocks the graph and fails the native lifecycle. It is not a
  reported successful scientific activity or an invented loss.
- Iteration invocation IDs separate actual code seed/LLM request contexts.
  Per-iteration output lineage excludes future events and preserves/rebases
  narrower causal prefixes explicitly declared by a delegate.
- Completion/skip receipts record requested/executed iterations, contract hash,
  state hashes and cumulative invocation count. Completion is a process-status
  protocol, not a claim that skipped research occurred.

The old native annual phase implementations use annual request identities and
have annual scientific side effects. Repeating those exact single-shot handlers
is rejected rather than silently reusing caches/charging twice. Repeatable new
activities can implement richer processes with explicit identities and actual
domain effects. The annual checkpoint/measurement boundary and the existing
paper/corpus production law remain native assumptions, not unlimited real-world
scientific semantics. New trusted action plugins can extend these laws explicitly;
the source executor cannot acquire privileged host access to do so itself.

## Evidence

`tests/system/test_native_process.py` covers original six-year scientific-state
and every-request equivalence under compiled dependencies, source-controlled
branch/repeat changing actual native researcher intention input, checkpoint
resume, iteration/cross-year memory, exact causal prefixes, already-true until,
delayed wait, invalid budgets/cycles and actual registered LLM request contexts.
Repeated tensor memory has autograd through all six invocations across two
periods, checked numerically. These are explicit original/native-handler or
isolated runtime QA, not new live-Qwen institutional discoveries.

The joint integration in `tests/optimization/test_native_open_composition_v7.py`
executes four original six-year worlds with real Docker and scripted HTTP. It
connects data-defined persistent actors/artifacts and actual project/context
effects, repeated source, mixed source/process/continuous generation, full native
loss feedback, subsequent generated source and recurrent tensor backward on the
same saved worlds. Separate G2 tests compare represented derivatives with actual
native perturbations and deliberately retain fidelity failure.
