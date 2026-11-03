# Open institution-authored work by original native researchers (v15)

## Why this is a new capability

Before this extension, arbitrary Python/LLM institution nodes could invent
their own protocols, state, custom actors/artifacts, resource transfers and
research-plan amendments. An anonymous LLM institution could also generate
arbitrary messages. However, invoking an **existing researcher as that actual
researcher** was still coupled to original built-in direction, submission,
review, citation and funding routines. An arbitrary new scientific workflow
could not directly request differently structured work from those researchers.

`native.researcher.work.v15` supplies that missing connection. It is a trusted
effect capability, **not** another menu of hypothesis/review/experiment types.
Institutions author the task instruction, arbitrary JSON content, recipient,
artifact references and response schema. The fixed original researcher renders
their existing persona, memory, project, resources and received institutional
context; the same original-world LLM transport produces the response. Researcher
weights/personas are not optimized, swapped, trained or fabricated.

This is implementation and SCRIPTED integration evidence, not an actual-Qwen
scientific experiment, automatic institutional invention, useful research,
optimizer improvement, or a claim that proposed experiments really occurred.

## Consumer interface

An ordinary custom mechanism has implementation `native.researcher.work.v15`,
one optional artifact input `tasks` of type
`native-researcher-work-request-v15`, one optional artifact output `responses`
of type `native-researcher-work-response-v15`, and the technical parameter
`max_requests_per_invocation` (integer 1 through 64). Extra dependency inputs
are permitted by the existing process compiler. The convenience function
`add_researcher_work_receiver` adds these declarations, one schedule and the
explicit caller-selected producer edge. It never creates a task or a reply.

Each input value addresses exactly one original author and carries this body:

```json
{
  "schema": "native-researcher-work-request-v15",
  "request_id": "an-institution-chosen-work-id",
  "actor_id": "an-existing-native-author-id",
  "instruction": "An institution-defined scientific task, not a built-in task enum.",
  "content": {"arbitrary": "scientific content or a custom protocol"},
  "artifact_ids": [],
  "response_schema": {"type": "object"}
}
```

The value's `actor_ids` must be exactly `[actor_id]`; `artifact_ids` must match
the body. Available references resolve against actual PaperTracker papers,
persistent open-domain artifacts, or declared generic artifacts from completed
graph checkpoints. The prompt includes the actual referenced scientific records,
not just claimed IDs. The original paper projection omits known operational clock
keys; arbitrary domain/store content is preserved literally, including scientific
fields named `timestamp`. Unknown, future/unavailable and mismatched references
fail closed.

Responses are ordinary typed graph data:

```json
{
  "schema": "native-researcher-work-response-v15",
  "request_id": "an-institution-chosen-work-id",
  "actor_id": "an-existing-native-author-id",
  "response": {"arbitrary": "schema-valid model response"},
  "receipt_sha256": "the exact corresponding native receipt digest"
}
```

They retain the real author/artifact addresses and causal event prefix. An
arbitrary sandboxed Python consumer can inspect/combine them, define new custom
artifact contents, send scientific discussion to other researchers, request
more work in a subsequent graph invocation, or issue existing explicit native
project/context/resource commands. Merely generating a response does **not**
publish a paper, mint resources, assign a review score, or overwrite the author's
project. Those privileged effects still require separately wired capabilities.

## Original world, safety and compute accounting

- Original phases and prompt bytes are unchanged if this opt-in node is absent.
- Recipient must be an existing author-capable actor sharing the original
  world's exact LLM object. No additional active-status or merit veto is added.
- Every request in the batch is checked before the first model call. The cap is
  not clipped; malformed actors, schemas, references, addressing, availability
  and duplicate identities stop the batch before work begins.
- JSON schemas use the existing bounded, reference-free, regex-free contract
  checker; request and prompt byte limits are explicit technical bounds. No
  schema expression or generated source is evaluated/imported on the host.
- Scientist temperature/token overrides, model/corpus/source identity and
  CompletedResponseCache are inherited from the original world, not separately
  chosen by the institution. Each response costs a scientist model request.
- The original portable safe point precedes each call. A later model/schema
  failure can leave earlier physical responses in the durable response cache;
  no claim of rollback of inference cost or successful batch commit is made.
- Process repetition is explicit. A cap of one with two iterations allows at
  most two calls, not one hidden annual call. Iteration IDs distinguish the
  physical tasks. Existing process `count`/`limit` remain the outer compute bound.
- Removal or latency of graph edges changes whether/when work and downstream
  original researcher-input effects occur. No implicit routing is inserted.

## Read-only receipts and cold restart

Each `native.system.researcher_work_completed` event contains the exact request,
source mechanism/port/emitted period/input-event IDs, actual native snapshot,
rendered prompt, parsed response, request identity, original-model seed context,
execution-contract digest, predecessor digest and receipt digest. Independent
hashes cover request, native snapshot, prompt and response. Raw assistant bytes
remain in the existing scientist response cache; a parsed receipt is not a new
physical reply. A UI can display these fields read-only without executing source.

Request identities include the actual source lineage, body, recipient, year and
execution node. Seed context additionally binds the native snapshot and exact
execution contract. Changing a task, producer, year or process iteration cannot
reuse a different task's reply. Rewinding the **same** physical task reuses its
exact completed response rather than calling the model again.

Persistent receipt chains are checked against canonical events on direct and
wrapped cold restore. Restoring validates exact rendered prompts, all content
hashes, response-schema conformance, actor/artifact identity consistency,
actual producer lineage and current execution contract. Migration retains old
source/event identity; it does not relabel earlier receipts as new executions.
These consistency checks are not an independent proof that all stored content
is scientifically true, nor a defence against replacing an entire evidence
bundle and all of its source/receipt hashes.

## Executed SCRIPTED verification scope

`tests/system/test_native_researcher_work_v15.py` uses the actual original
Simulation, four actual UniversityResearcher instances, original phases and
real pinned Docker execution. Only corpus/retrieval/HTTP replies are scripted.
The institution's arbitrary Python creates a non-paper custom scientific
artifact, asks an existing researcher to discuss it, and passes that researcher
response through different arbitrary Python into an explicit native-context
command. The response appears in original direction-selection model input.

Checks cover six-year execution, edge-removal control, original model/persona/
memory/context use, per-invocation caps including process repetition, distinct
task/source/iteration cache identities, exact rewind reuse, whole-batch
preflight, unknown references, finite/schema bounds, malformed model output,
causal-prefix outputs, native-paper snapshots without paper/score creation,
receipt corruption, canonical replay references, and interruption after year-3
effects before commit followed by cold restart. Completed year-3 responses are
reused; the resumed world matches the uninterrupted scientific/kernel state.

## Remaining boundaries

This removes one concrete workflow restriction, not every original-world law.
Researchers still use the original fixed persona and underlying model. New
custom actors are data-defined actors, not automatically endowed with native
researcher methods. Scientific work produces model responses, not actual lab
equipment, measured empirical results or automatic corpus papers. Institution
logic, recursive dialogue and effects must still be explicitly authored/wired.
New privileged world effects still require trusted capability extensions.

The annual scientific checkpoint boundary remains. A generic store's newly
created same-year record is not yet available through its completed-checkpoint
lookup; use an open-domain artifact (available immediately after its committed
command), carry scientific content in the task, or schedule the task after a
checkpoint. Actual-Qwen use, optimized task allocation and useful invention are
not established by these SCRIPTED tests. No hidden novelty/quality/fairness
constraint or extra optimization loss is introduced.
