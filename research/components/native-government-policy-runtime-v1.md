# Native government policy runtime v1

## Scope and claim boundary

This slice makes the existing production government mechanisms executable in
new prospective ScienceUtopia simulator campaigns. Government is an optional,
stateful control-plane mechanism, not a synonym for evaluation and not an
optimization objective.

The directives are the existing structural-space engineering fixture:

```json
{
  "evaluation": {"acceptance_rate": 1.0},
  "funding": {"award_amount_multiplier": 2.0}
}
```

They are deliberately conspicuous integration-test values. They are not a
policy recommendation, scientific-quality definition, welfare model, or
claim that intervention is better than absence. No loss, held-out metric,
promotion rule, or scientific ranking is introduced.

The runtime is default-off. `--government-policy-mode off` creates no runtime,
changes no acceptance or funding value, emits no policy event, and adds no
government checkpoint state or portable scientific-contract field.

## Reused structural catalog

The native overlay reuses the axes and production identifiers already defined
by `stateful-government-science-system-v1`:

- government absent or present;
- `production.governance.event-responsive-policy-v1` or
  `production.governance.threshold-policy-v1`;
- independently present evaluation, funding, and publication observation
  edges;
- independently present evaluation and funding policy edges;
- one- or two-year policy latency on each policy edge.

The overlay adds `native.government.policy-maker` as a governance-family node.
It adds optional policy input ports to the legacy evaluation and funding
nodes, plus the exact typed edges selected by the candidate. The legacy core
is recovered only after the overlay has passed exact reconstruction.

Changing a node implementation, parameter, input/output port, edge presence,
edge latency, schedule, artifact declaration, invariant, or overlay metadata
causes compilation to fail. Unsupported government variants are not ignored.

`native_government_system_spec_from_catalog_candidate(...)` accepts a canonical
candidate emitted by the existing 145-candidate structural space, verifies its
structural encoding, and transfers government presence, implementation,
observation-edge presence, policy-edge presence, and latency onto an executable
legacy simulator base. The translated SystemSpec records the source catalog
candidate fingerprint and complete structural selection.

## Sealed plan mapping

Compiler revision `1.2.0` maps the exact overlay to:

```text
--government-policy-mode
--government-minimum-observations
--government-repeat-interval
--government-directives-json
--government-observation-sources
--government-policy-edges
--government-system-fingerprint
```

Directives use canonical JSON rather than Python string representation.
Observation and policy edge arguments are derived from the validated graph,
not independently chosen runtime flags. Dry-run parsing reconstructs the typed
config and requires the complete source `SystemSpec` fingerprint.

The sealed plan retains the complete source graph, mappings, model, fidelity,
seeds, compiler revision, source commit, and argv hashes. Compilation neither
creates campaign directories nor calls a model endpoint.

## Native execution

The adapter invokes the existing production `event_responsive_government` or
`threshold_government` handler. It does not maintain a second policy-decision
algorithm. Its checkpoint embeds the handler's
`scienceutopia.government-state.v1` state.

At the end of each completed simulation year, the native boundary constructs
one explicit typed observation for every selected source edge:

- evaluation: accepted and rejected counts;
- funding: award and application counts;
- publication: count and stable accepted-output ids.

Each observation becomes a canonical
`native.government.mechanism_observed` event. The corresponding delivered
value cites that event, so the production handler's policy decision is bound
to canonical input lineage.

When the production handler issues a policy, the adapter emits
`native.government.policy_decided` containing the complete versioned policy.
It then queues one delivery for every selected policy edge:

```text
available year = issued year + SystemSpec edge latency
```

At the start of the available year, the production policy resolver checks
system fingerprint, issuer, emitted period, target directive, monotonic
version, replay, and ambiguity. A successful delivery emits
`native.government.policy_applied`, which cites exactly one decision event and
names the affected legacy mechanism.

## Explicit simulator effects

The evaluation application sets the conference acceptance rate after the
ordinary per-year schedule is loaded and before acceptance decisions. The
funding application multiplies the university award amount before resource
credit and funding-ledger recording. The year result records the active policy
identity, version, directive, and applied value.

These are explicit affected-mechanism effects rather than decorative labels.
Publication is an observed source in v1, matching the existing catalog; it is
not yet a policy consumer. Industry funding, policy conflicts, repeal, expiry,
appeal, and multiple jurisdictions remain outside this slice.

## Typed causal chain

The required chain is:

```text
mechanism observation event(s)
        -> versioned policy decision event
        -> delayed affected-mechanism application event
        -> observable evaluation/funding simulator behavior
```

The decision cites all observations used for that version. Each application
cites its decision and records target family, affected mechanism, directive,
issued year, applied year, observed latency, policy id/version, and complete
system fingerprint. The namespace is `native.government.*`; it is not mixed
with citation or communication events.

## Checkpoint, resume, and replay

The native checkpoint contains:

- exact config and config fingerprint;
- completed-year cursor;
- production government state;
- active target policies;
- pending delayed deliveries;
- complete canonical event history.

Restore cross-checks production observation ids, observation count, issued
policy ids, next version, last policy fingerprint, active policies, pending
decision references, edge latency, directives, and event history. On/off,
SystemSpec, config, lineage, version, or latency mismatch fails closed.

Only completed-year snapshots are supported. JSON round-trip followed by
resume is byte-equivalent to uninterrupted execution.

The canonical replay converter recognizes the optional checkpoint state,
reconstructs it through the same validator, and merges the events into the
ordinary replay stream. Event ids remain stable because canonical sequence is
not part of event identity; source events precede every cited downstream event
after canonical sorting.

## Deterministic evidence

`tests/government/test_native_government.py` uses only synthetic development
seed 1201 and small deterministic mappings. It verifies:

- default-off plan and parser behavior;
- both catalog implementations through SystemSpec, sealed plan, and parser;
- composition with the native communication overlay in either nesting order;
- direct translation of a canonical structural-space candidate, including
  absent observation edges and independent policy latency;
- real production government state and threshold accumulation;
- policy action to evaluation/funding application with independent latency;
- actual simulator acceptance-rate and funding-award effects;
- deterministic checkpoint/resume;
- structural and checkpoint tamper rejection;
- canonical replay with complete causal references.

No active v1.1 topology, registry, campaign, held-out seed, running worktree,
or raw output is read, changed, registered, or executed.

## Deliberate next gaps

- add a typed publication consumer rather than overloading the v1 observation
  edge;
- model expiry, repeal, appeals, jurisdiction, coalitions, and conflicts;
- replace conspicuous fixture directives with separately versioned candidate
  parameters only under a preregistered scientific protocol;
- expose policy attention and compliance rather than assuming immediate
  application on delivery;
- study government structure only with separately declared losses and
  untouched evaluation splits.
