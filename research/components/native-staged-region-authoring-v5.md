# Staged open institution authoring v5

This is an additive authoring route, not a reinterpretation or silent extension
of the preserved v5/a2 technical-draft budgets. Its software QA uses scripted
model outputs and the original native researcher world with real isolated
Docker execution; QA does not establish actual LLM invention or benefit.

`NativeStagedRegionProposer` separates two independently bounded phases:

1. **Graph/protocol plan:** the model chooses arbitrary local nodes, interfaces,
   payload schemas, JSON parameters/state schemas, explicit ingress/internal
   source references, all native export references and execution order. The
   plan contains no `python_code`. The schema checks all required interfaces;
   independent malformed references are reported together. Existing compilation
   checks channels, artifact types, boundary closure and native invariants.
2. **Implementation source:** with that exact accepted plan fixed, the model
   supplies `{sources:{local_node_id:Python_string}}` for every node. All node
   source/ABI errors are collected before any code execution. Exact source
   bytes are attached without edits, compiled through the existing IR compiler,
   then probed on every complete recorded native year with candidate memory
   carried chronologically. Only a successful full probe returns a candidate
   patch to the native optimization controller. Fresh researcher-world
   execution/loss evaluation remains a separate subsequent step.

Structural compilation uses an AST-valid placeholder that immediately raises
if called. It is never executed, returned, persisted as a candidate or used to
produce outputs. No host institutional algorithm, missing edge, decision logic,
payload wrapper or source repair is supplied. Arbitrary new internal protocols,
institutional code, multi-node order and connections remain model choices.
This initial route retains the existing zero-delay native graph-cut scope.

## Prompt shape and objective binding

The route reuses a2's mechanically aligned actual ingress aliases. Every native
period is represented in prompts; prose and list lengths can be reduced, but
nested JSON container types remain faithful (lists never become diagnostic
dictionaries). Full untouched contexts drive probes, not the lossy prompt views.
Source prompts show the complete chosen plan, exact input-list/envelope access,
actual submitted-paper **list** shape, output port names versus export aliases,
and the real empty-year/publication contracts. These are transport/domain
contracts, not a choice of institutional algorithm or a hidden merit veto.

The explicit LossSpec, full observation history hash, actual parent fingerprint,
all native context-bundle hashes, runtime image, instructions, temperature,
schema hashes and phase budgets bind prompts and receipts. Original host bodies
are withheld initially; generated incumbent and at most two prior generated
designs are shown with their actual objective feedback and exact generated
source. The model supplied by the caller controls thinking; the proposer does
not change researcher weights, researcher inference settings or thinking mode.

## API, budget and replay

```python
NativeStagedRegionProposer(
    model, executor, removed_nodes=["world.selection"],
    context_provider=provider, receipts=receipt_directory,
    instructions="...", plan_attempts=3, source_attempts=3,
    max_tokens=8192,
)
```

`max_attempts=3` is a compatibility alias setting both independent phase budgets
to3. A proposal uses at most3 plan drafts and, only after a valid plan, at most3
source rounds—not repeated nested retries. Technical drafts have null loss.
Failed source rounds do not silently replan or restart the original budget.

The schema binding is `scienceutopia.native-region-proposal.staged-v5`.
`plan-{index}-{attempt}.json` and `plan-prompt-*` retain exact plan responses and
prompts; plan statuses are `invalid-technical-plan` or
`structural-plan-passed-not-executed`. `region-{index}-{attempt}.json` and
`region-prompt-*` retain exact source responses and prompts. The first source
receipt links the accepted plan receipt; later source receipts hash-chain their
predecessors. Source bindings include exact `plan_sha256` and
`plan_receipt_sha256`. Successful source receipts include the complete assembled
IR, exact source hashes, patch, fingerprint and native probe receipts. Interrupted
validation resumes saved responses without another model request. Reopening
reconstructs the accepted plan and successful patch; changed bindings, receipts
or prompt bytes fail closed. The historical outer exhaustion error is preserved
for driver compatibility; phase-specific raw receipts retain the actual cause.

This code alone is not evidence that open institutions are useful or that a
native optimization loop improved. Any new live pilot needs its own pinned
runtime, explicitly declared phase/token/thinking budgets and independent audit.
