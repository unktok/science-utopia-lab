# Whole-system structural black-box slice v1

Status: synthetic-tested feature branch

## Research role

This slice puts evaluation, publication, funding, government, and
communication choices into **one candidate `SystemSpec`**.  Earlier production
tracks established these mechanism families separately.  The joint grammar is
the next executable step from the fixed eight-parameter legacy topology toward
black-box optimization of the science system itself.

```text
explicit LossSpec
       |
ask complete SystemSpec
  -> validate typed graph
  -> execute registered mechanisms
  -> establish technical validity
  -> measure synthetic development signals
  -> evaluate scalar optimization loss
  -> tell observation
```

The same `AdaptiveRandomSearch` and `SearchSpace` boundary used by the legacy
parameter space accepts this structural space.  The optimizer does not inspect
mechanism families, graph events, or runtime state.

## Joint design language

`utopia.optimization.whole_system_structural` composes existing adapters rather
than creating family-specific runner branches:

| Slot | Choices |
|---|---|
| evaluation | absent, conference rate, conference fixed slots |
| publication | absent, production paper tracker |
| funding | absent, compact ranked allocation |
| government | absent, event responsive, cumulative threshold |
| communication | absent, broadcast, digest |
| government connection | observation absent/present; policy absent or one-/two-period latency |
| communication connection | delivery absent or zero-/one-period latency |

Required typed inputs make illegal partial structures disappear.  For example,
a publication node cannot exist without its evaluation-to-publication edge,
and a communication broker cannot exist without its knowledge-source edge.
Optional government and communication outputs can remain disconnected, so an
optimizer may add a mechanism and connect it in a later valid one-slot
mutation.

The finite grammar contains 770 valid graphs.  Every candidate has canonical
JSON, a complete graph fingerprint, and a bound structural selection.  Node
presence, evaluation configuration, government/communication implementation,
edge presence, and latency are all observable mutation axes.

## Runtime and checkpoint evidence

The graph runner remains family-agnostic.  One ordinary registry contains:

- the deterministic review/funding workload fixture;
- the deterministic knowledge-source fixture;
- production conference evaluation;
- production publication tracking;
- production compact funding;
- production stateful government;
- production broadcast/digest and strict knowledge receiver adapters.

Representative empty, full, and alternative systems execute without a model
call.  The full system crosses all five institutional families and retains
canonical causal lineage.  A two-period checkpoint JSON round-trip followed by
two-period resume is byte-equivalent to an uninterrupted four-period run for
events and final state.

`StructuralSystemSpace` now performs a cheap dangling-edge and required-input
prefilter before full validation.  This does not weaken validity: every
retained graph still passes the authoritative `validate_system_spec` path.  It
reduces joint-space construction from validating the entire raw Cartesian
product to fully validating only structurally resolvable candidates.

## Four separated concepts

This slice keeps the project's research boundaries explicit:

1. **Optimization loss:**
   `WHOLE_SYSTEM_ENGINEERING_LOSS_SPEC` is an ordinary, hashable
   `scienceutopia.loss-spec.v1`.  It consumes only deterministic development
   signals and is labeled `synthetic-development-only`.
2. **Technical validity:** graph validation, implementation resolution, runtime
   contracts, checkpoint binding, and finite loss production are separate
   gates.  A technical exception propagates and is never converted into a
   numeric penalty.
3. **Held-out evaluation metrics:** none are defined or consumed here.  The
   development signals are not called held-out evidence.
4. **Promotion policy:** none is defined or applied.  A low engineering loss
   does not authorize scientific or policy promotion.

The synthetic loss rewards integration-test activity.  It is useful only to
prove result-dependent black-box plumbing and must not be reused as a science
policy objective.

## Tests

`tests/optimization/test_whole_system_structural.py` proves:

- all 770 joint structures are valid and have distinct fingerprints;
- all five families expose the intended absence/implementation axes;
- representative systems produce different deterministic behavior;
- checkpoint/resume equality across the complete mixed graph;
- one-step mutations cover node presence, configuration, implementation, edge
  presence, and latency;
- ask/execute/LossSpec/tell produces complete, fingerprint-bound observations;
- an unresolved implementation remains a technical failure with no loss.

Existing structural, production, government, and communication tests remain
unchanged and passing.

## Deliberate limits and next boundary

- The workload and knowledge sources are synthetic fixtures.  No Qwen, GPU,
  active experiment registry, raw output, or held-out seed is touched.
- The native ScienceUtopia simulator-plan compiler still supports only its
  narrow fixed topology and exact prospective overlays.  It correctly rejects
  arbitrary members of this joint grammar rather than silently collapsing
  them.
- Funding policy output is declared and provenance-bound, but the v1 joint
  grammar varies only the government-to-evaluation policy connection to keep
  the first combined space finite and auditable.
- Research generation remains a fixture source, not a production research
  mechanism.  Employment, education, and collaboration remain future slots.
- A real campaign still requires a preregistered scientific LossSpec, separate
  optimization seeds, a versioned technical validity contract, a frozen
  grammar and proposal budget, and an untouched held-out metric suite.

The next safe increment is a sealed structural-campaign plan that binds grammar
revision, LossSpec hash, optimization seeds, implementation registry versions,
and execution backend without starting a run.  Native model-backed execution
should follow only after that plan can be admitted into an isolated experiment
worktree.
