# Native review-work authority and complete plan provenance v13

This is a prospective native-world capability, not an invented institution,
scientific result or new optimization constraint. Historical v12 receipts stay
unchanged and retain their missing full-upstream-plan limitation.

## Actual review tasks, not generated scores

`utopia/system/native_review_routing.py` registers two explicitly selected native
implementations. Registering them alone changes no default graph, prompts,
reviewer sampling, RNG, paper selection or model calls.

- `native.world.review-inputs.v13`: reads actual current submitted papers and
  original reviewer eligibility, and emits one `native-review-input-batch-v13`.
- `native.phase.review.with-routing.v13`: consumes that exact batch plus one
  source-authored `native-review-routing-plan-v13`, validates the whole command,
  and invokes the original Simulation phase-3 batch/prompt/parser/review-record/
  received-review-experience path with those explicit reviewer assignments.

No generated function is run in the host. Arbitrary candidate source continues
to execute in the existing networkless, read-only, unprivileged Docker executor.
The native effect is trusted identity/accounting transport, not an algorithm
catalogue. It neither selects reviewers nor invents their scores.

### Public data ABI

Input batch:

```json
{
  "schema": "native-review-input-batch-v13",
  "year": 1,
  "papers": [{
    "conference_id": "actual-venue",
    "paper_id": "actual-paper-id",
    "paper": {"id": "actual-paper-id", "...": "the complete actual native dict"},
    "eligible_reviewer_ids": ["actual-native-reviewer-id"]
  }]
}
```

Command (exact keys, including an empty `tasks` list when desired):

```json
{
  "schema": "native-review-routing-plan-v13",
  "year": 1,
  "batch_sha256": "SHA256 of canonical complete input batch",
  "tasks": [{
    "conference_id": "actual-venue",
    "paper_id": "actual-paper-id",
    "reviewer_id": "actual-native-reviewer-id"
  }]
}
```

Canonical hashing is
`hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')).hexdigest()`.
The source returns the normal code-node envelope:
`{'outputs': {'routing': [{'payload': command}]}, 'state': {}}`.

### Explicit installation

The designer declares an arbitrary producer with an ARTIFACT input named
`batch` of artifact type `BATCH`, an ARTIFACT output named `routing` of type
`PLAN`, source code and an explicit schedule (110 in the unchanged baseline).
Then:

```python
from utopia.system.native_review_routing import BATCH, PLAN, enable_review_routing
spec = enable_review_routing(spec, source='my-new-institution', source_port='routing')
```

These numeric defaults apply to the **raw legacy/activity graph**, before an
explicit process compilation: the helper adds the data-only snapshot at phase
105 after costs at 100, wires its batch to both the producer and review, and
wires the producer's command to review at phase 120. It inserts no producer or
reviewer policy. They are NOT universal phase IDs. For example,
`open_native_system` has already called `compile_dependencies`, which reindexes
its actual schedules (costs 80 and review 90 in the current seed graph). A
designer extending that graph must inspect its actual schedules and explicitly
choose compatible producer/snapshot priorities, such as producer 85 and
`snapshot_phase=83`, or explicitly rebuild its process ordering.

After inserting the new nodes/edges into an already compiled process, recompile
the process metadata/order as well. Its previously materialized dependency
edges remain real edges; passing empty dependency lists for **every** current
node to `compile_dependencies` retains those edges without inserting duplicate
`requires-*` control ports. Alternatively rebuild from the original uncompiled
spec with a complete explicit dependency/priority map. Neither the helper nor
the runtime silently moves nodes or repairs contradictory process plans.
Different node IDs/input names/snapshot phase are explicit helper arguments.
The helper deliberately refuses already-replaced review implementations rather
than silently discard a previously selected mechanism. A designer can manually
compose other interfaces; delivered-review-context and routing have not yet
been combined as a native implementation.

### Technical legality versus optimization

Eligibility exactly follows the original native semantics: `can_review` plus
exclusion of all paper authors and their existing conflict-of-interest IDs.
It does **not** add an `is_active` restriction, balancing, minimum reviews,
quality floor, fairness test, novelty incentive or loss veto. Paper/reviewer
IDs must be real, the conference/year/batch hash must match, and duplicate
paper/conference/reviewer tasks are rejected because the original native
review identity model assumes one such record per annual review round.

The task list can freely select any subset of eligible pairs, including zero.
The original native outer conference/paper order is preserved; within a paper,
reviewer order follows the supplied list. Global arbitrary interleaving of
review calls is not a capability of this version.

Importantly, original legacy selection later raises on unreviewed papers.
A system choosing zero/partial review coverage must **also explicitly supply
its own compatible selection source** using the existing free decision-code
interface. The host does not secretly fill reviews or invent an admission
policy. The zero-review test uses a labelled test-authored selection source.
The original phase-3 internal no-review fallback is not a real review and must
never contribute to raw reviewer mean Q or actual review count R.

Original review work does not itself charge an author resource fee. This
capability changes actual model work, records, review experiences and original
downstream behavior; it does not invent resource charges. Any resource policy
must be separately authored using the existing transfer/action capabilities.
The legacy `peer_review.reviews_conducted` summary counts reviewed papers;
audit R must instead count the actual individual native review records.

### Causality, persistence and failure

The complete command is checked before conference review status, prompts,
model calls or review records are mutated. Unknown identities, mismatched
content/hash/year, duplicate tasks and malformed commands fail without a
partially executed review batch. This is not a general rollback of an already
executed world or a failed model provider response: those attempts remain
technical failures under the existing checkpoint contract.

`native.system.review_inputs_bound` commits the complete batch/hash.
`native.system.review_tasks_bound` records exact original task indices,
reviewer/paper/conference IDs, prompt SHA256, parsed response SHA256, original
native score and native review-record SHA256.
`native.system.review_routing_applied` binds input/source-port/event lineage,
the complete command/hash and all executed tasks. The actual task set/order is
checked against the plan after original execution. A hash-bound mechanism state
joins the last committed receipt and survives cold restart. Rewinds/repeats and
tampered persistent state fail; original portable response replay remains the
same mechanism rather than a new trial or source execution.

## Complete applied research-plan provenance

The existing `native.system.research_plan_applied` event now additionally
retains `base_plan`: its complete unmodified upstream plan, canonical hash,
source mechanism/port, emitted period and input event IDs. Existing amendment
commands and their hashes/lineage are retained. The pure read-only helper
`reconstruct_applied_plan(receipt)` replays the exact ordered amendments,
verifies submitter order and checks the resulting committed full-plan hash.
Prospective kernel restore also validates this reconstruction.

This addresses the v12 information gap rather than rewriting v12 history.
Historical receipts without `base_plan` are explicitly not reconstructable.
The reconstruction helper alone verifies data consistency, not world truth;
an independent audit must also join the named upstream/code/output events and
actual actor-state transitions.

## Verification scope

`tests/system/test_native_review_routing_v13.py` uses the actual original
six-year scientific phases with scripted HTTP/corpus/retrieval only. It tests
zero/one-review source plans, exact actual request/record identities, empty
tasks, invalid/foreign/self/duplicate/malformed commands, original eligibility,
default equivalence, portable cold restart and state-hash tampering.
`tests/system/test_native_plan_provenance_v13.py` tests complete original-plan
preservation, exact amendment reconstruction and missing/tampered context.
These are software/native integration tests, not fixed-Qwen experimental data,
successful institutional invention or an optimizer-benefit claim.
