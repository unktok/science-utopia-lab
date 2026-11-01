# Native research activities as explicit graph contracts v6

This is an opt-in extension of the **original researcher world**, not a smaller
numeric world. Its scientific agents, corpus selection, project production,
paper registration, review, publication, costs and funding methods remain the
native Simulation methods. No additional scientific-quality/fairness veto is
introduced. All evidence below is scripted HTTP/retrieval software QA, not new
live-Qwen optimization or evidence of scientific benefit.

## What was private, and what is now open

The unchanged legacy kernel passes four values through its annual private frame:
`directions` and `authors` from research to collaboration/submission,
`resubmissions` to submission, and `submissions` to funding. Those are genuine
native domain dependencies, not just cosmetic signal wires.

`activity_world_system()` is a separately fingerprinted opt-in graph. It replaces
only those five native stage adapters and inserts one explicit research-plan
effect capability. It never reads or writes those four private frame entries.
The shared current year/results and native Simulation are still lifecycle state.

| Producer | Public output | Consumer |
| --- | --- | --- |
| `world.research` | `plans`: `native-research-plan-v1` | `research-plan-effects.plans` |
| arbitrary Python/LLM institution | amendment protocol | `research-plan-effects.amendments` (optional) |
| `research-plan-effects` | `applied`: research plan | `world.collaboration.plans` |
| `world.collaboration` | `planned`: research plan | `world.submission.plans` |
| `world.resubmissions` | `papers`: `native-paper-batch-v1` | `world.submission.papers` |
| `world.submission` | `submitted`: paper batch | `world.funding.papers` |

The ordinary SystemSpec remains editable. Producers, algorithms, protocol adapters,
edges, node presence and schedule can be changed explicitly. No host algorithm
fills missing wires. Missing required edges fail structural validation; an
undelivered required value blocks its consumer rather than falling back to frame
data. Native adapters still require coherent domain chronology.

## Research plans are not an institution or topic catalogue

One plan bundle has exactly:

```json
{
  "schema": "native-research-plan-v1",
  "year": 1,
  "assignments": [{
    "actor_id": "<existing native author ID>",
    "direction": {
      "topic": "A previously unenumerated topic",
      "focus_areas": ["Any text"],
      "years": 1,
      "keywords": ["Any text"],
      "related_topics": []
    },
    "detailed_focus": "An authored research plan",
    "reason": "An authored rationale",
    "project_start_year": 1,
    "project_end_year": 1
  }],
  "submit_actor_ids": ["<existing native author ID>"]
}
```

Direction keywords/related_topics may also be null, matching native ResearchDirection.
Assignments/submission IDs are ordered, unique real author identities. Text is
not checked against AVAILABLE_DIRECTIONS. Positive project duration has no
catalogue maximum; project end must equal start + duration - 1, and start must
not be in the future. Native submission requires an active real actor whose
project completes **this** year. These are existing native production semantics,
not objectives. A producer can suppress submission without suppressing research.

The effect consumer atomically validates the **whole** plan plus all amendments
before updating actual native `newest_direction`, `project_start_year` and
`project_end_year`. It returns the applied plan, and downstream adapters check
that it matches actual agent state. Plans change real intention prompts, retrieval
queries and which real agents produce/register papers; they are not decorative
institutional-context text. Algorithm choice is entirely the producer's.

For a fixed interface, an arbitrary producer can replace the primary `plans`
edge with a complete authored plan. For incremental/stateful/delayed algorithms,
`add_activity_plan_authority(spec, source=..., source_port=..., latency=...)`
explicitly grants the optional amendment input. Its producer port must have
artifact type `native-research-amendment-v1`. Each message has exactly:

```json
{
  "schema": "native-research-amendment-v1",
  "target_year": 2,
  "assignment": {
    "actor_id": "<existing native author ID>",
    "direction": {"topic": "An arbitrary new topic", "focus_areas": [],
                  "years": 1, "keywords": [], "related_topics": []},
    "detailed_focus": "An authored plan for delivery year 2",
    "reason": "An authored rationale",
    "project_start_year": 2,
    "project_end_year": 2
  },
  "submit": true
}
```

The assignment must reference an actor already present in the current base plan.
No conflicting simultaneous writers for one actor are silently resolved. The
target year must be the actual delivery year. Current-year base plans must be
produced this year; they are not automatically rebased when an edge is delayed.
Delayed amendments must explicitly design their project dates for delivery.

## Real artifact identity and provenance

Paper bundles contain schema/year/kind (`resubmission` or `submission`) and a
list of native paper dictionaries, including an explicit empty list for empty
scientific years. The consumers validate unique actual archive IDs, year and
content before calling native methods. Submission snapshots may precede native
status/review updates; funding resolves the checked IDs back to actual current
venue paper objects. Resubmission resolves to archive-backed dictionaries so
the original shared review-history references remain intact. A naive JSON copy
was rejected during development because it changed six-year review histories.

Research-effect events carry applied-plan hash, selected submitter IDs and exact
amendment bodies/hashes, producer/port/emitted year and input event IDs. Canonical
runtime provenance additionally binds the whole invocation to its inputs and
system fingerprint. Generated Python executes only in the existing pinned,
networkless Docker boundary; this module never imports/executes authored source
on the research host. Native agent checkpoints and graph queue/state/events
preserve applied plans and delayed amendments on a cold restart.

Atomicity is a plan-effect invocation, **not a whole scientific year**. Invalid
inputs cannot partly amend native agents. Earlier native research assignment or
resubmission effects in the same failed year are not rolled back: as elsewhere
in the native kernel, restore the preceding portable checkpoint before retry.
Rollback covers the base native project attributes, not arbitrary side effects
inside custom user-defined attribute setters.

## Original-world structural requirements still inherited

Native yearly opening initializes actual venue/agent/accounting cycles. Native
research assignment also resets funding programs, records direction assignment
history, and computes ready authors; replacing that whole producer must explicitly
provide the cycle effects that the remaining native consumers require. Native
collaboration updates its own pairing/tracker/conflict state, and its existing
formation algorithm only runs in the preferential-attachment experiment. Native
submission selects **existing real corpus documents**, applies project/output
costs, registers the paper/archive/RAG status, then registers it with a real venue.
It is not a free-text generator of arbitrary newly invented paper artifacts.
Resubmissions have already been selected, charged and archived by their exporter.
Review/publication/funding depend on those actual collections and lifecycle.

The contracts remove hidden activity-data transport, not all original scientific
domain laws or all side effects in those methods. Rewiring required native stages
into an incoherent order fails rather than silently synthesizing missing papers,
venues, program resets or accounting transactions. Domain-law replacement needs
another explicit capability, not a host semantic repair or a simpler toy world.

## Verification and remaining limits

`tests/system/test_native_activity_contracts.py` checks:

- Six-year original scientific state **and every model request** exactly equal,
  for both one-year projects and two-year projects with empty publication years.
- Existing original scientific phases all execute; no toy actor/world replaces them.
- Real sandboxed arbitrary Python changes actual native intention inputs and a
  noncatalogue topic, with source-event/hash receipts.
- Its choice of a submission subset changes actual first-year production from
  four to three real submissions, not merely a reported metric.
- Disconnection has no amendment effect; explicit one-year latency changes the
  first affected year. A missing/delayed mandatory plan has no private fallback.
- Delayed source state, native scientific state, events and queued messages are
  identical after interrupted-year/cold restart.
- Unknown/duplicate/inactive actor IDs, stale years, inconsistent dates,
  nonfinite data and conflicting writers reject before any plan mutation.

The old `legacy_world_system()` and resource-transfer capability are unchanged.
Existing legacy-equivalence/resource tests are rerun separately.

This opens native **research planning and submission participation**, not all
possible scientific ontology. Collaboration formation now consumes explicit
plans but still uses the original formation method; arbitrary authored partner
transactions are not supplied here. The original resubmission method still
chooses/charges resubmissions before exporting them. New actor kinds, arbitrary
new paper production laws, experiments/hypothesis validation, and replacing all
venue/archive/funding semantics need additional explicit effect capabilities.
Project-end consistency is currently inherited from the original paper producer.
Arbitrary source and LLM calls remain black boxes, not automatic autograd paths.
No live candidate, objective improvement or fully differentiable native world
is claimed by these tests.
