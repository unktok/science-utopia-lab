# Miniature Whole-System Design Lab v0

Status: integration design; no model-backed campaign started

Decision: [0021](../decisions/0021-breadth-first-miniature-whole-system-v0.md)

## Purpose

Build one inexpensive but real vertical slice that exercises the complete
research program before any further scale-up. The slice should be small enough
to run and debug locally while using the same contracts intended for later
large campaigns.

The object is not a better estimate of the v1.1 winners. It is proof that one
objective can drive both structural black-box and differentiable proposal
paths, that their projected systems can execute through the same model-backed
outer simulator, and that the game can inspect the resulting evidence.

## Scale envelope

The first runnable configuration should stay within:

- at most 10 researcher agents;
- at most 2 simulated years;
- 1 or 2 development seeds;
- at most 5 black-box proposals;
- 1 differentiable optimization/projection episode;
- at most 2 final systems per proposal path for the comparison view.

These are ceilings for v0, not scientific sample sizes.

## Shared object graph

```text
ObjectiveSpec
  -> compiled LossSpec + diagnostic metric suite
  -> MiniatureStructuralGrammar
       -> BlackBoxSearchAdapter -> proposed SystemSpec
       -> DifferentiableRelaxation -> projection -> proposed SystemSpec
  -> SystemSpec validation + implementation registry
  -> model-backed miniature simulator
  -> canonical events + run summary + loss observation
  -> campaign comparison artifact
  -> game replay + graph/path/branch inspection
```

Both proposal paths must converge before execution. After projection, the
simulator must not know whether a candidate came from a gradient or black-box
optimizer.

## Existing foundations to reuse

| Required layer | Existing foundation | Integration gap |
|---|---|---|
| objective | Objective Constitution compiler and metric cards | choose one explicit v0 objective and compact diagnostics |
| structural grammar | joint 770-graph synthetic grammar; production mechanism registries | freeze a small executable subgrammar |
| black-box path | restart-safe generic ask/tell controller | bind structural candidate adapter to compact model-backed execution |
| differentiable path | synthetic whole-system relaxation and projection | target the same v0 grammar and validate projected fingerprints |
| outer simulator | Qwen3-8B longitudinal runner and simulator-plan bridge | support the selected structural mutations without silent fallback |
| evidence | run registry, canonical events, provenance, comparison reports | define one miniature campaign manifest and comparison artifact |
| game | replay, system sandbox, branch comparison, optimizer observatory | consume the real miniature artifact instead of separate fixtures |

## Integration checkpoint: common proposal boundary

Decision 0022 and `utopia.optimization.continuum` now separate design freedom
from search method. Parameters, mechanism implementations, and node/edge
structure form nested mutable views of the existing six-family relaxation.
Gradient-free black-box, differentiable-surrogate, and hybrid proposal paths
all project through the same discrete `SystemSpec` boundary and call the same
opaque outer-evaluator interface.

This closes the synthetic API part of work package 3, not the work package as
a whole. The common template still lacks schedule/latency relaxation, and the
outer evaluator in this checkpoint is synthetic rather than the miniature
Qwen-backed simulator.

## Minimum structural grammar

The grammar must include evaluation and at least two additional families from
publication, funding, government, and communication. It must expose:

- one optional node or implementation substitution;
- one optional or alternative typed connection;
- one schedule, latency, or allocation parameter;
- explicit invariants preventing graphs that cannot execute;
- a stable fingerprint covering structure, parameters, implementations, and
  objective binding.

Unsupported structures must fail validation. They may not silently compile to
the legacy topology.

## Objective boundary

The v0 objective is a research probe. It must be versioned through
`ObjectiveSpec`, compile to a search-visible `LossSpec`, and declare separate
report-only diagnostics. Technical validity remains non-numeric admissibility.
No protected-slice veto or policy rule enters implicitly.

The probe should be sensitive to at least two mechanism families so structural
changes can reach the measured outcome. It need not represent scientific or
social welfare.

## Black-box path

The black-box path must persist suggestions and observations and produce at
least one proposal whose lineage names a prior valid observation. A tiny budget
is sufficient. The result is evidence of structural result dependence, not
search efficiency.

## Differentiable path

The differentiable path may use an analytic or fitted surrogate, provided that:

- its variables correspond to the same frozen structural grammar;
- it records relaxed values, gradients, projection, and projection gap;
- projection is deterministic and produces a valid discrete fingerprint;
- the projected candidate is evaluated only by the common outer simulator;
- surrogate score and simulator loss remain visibly distinct.

## Game and replay contract

The game view must expose, from commit-pinned artifacts:

- the chosen objective and search-visible loss;
- black-box and differentiable proposal lineage;
- structural graph differences between compared candidates;
- researcher and artifact activity in canonical replay;
- evaluation, resource, policy, or communication flows used by the selected
  miniature grammar;
- simulator observations and report-only diagnostics.

Layout, animation, lighting, and narrative text remain presentation-only. The
UI may branch a recorded system only by creating a new versioned candidate and
run request.

## Work packages

1. **Manifest and grammar:** freeze schema, scale envelope, objective binding,
   implementation registry, and seed roles.
2. **Model-backed structural execution:** close the exact compiler/runtime gaps
   for the chosen three-plus mechanism families.
3. **Common proposal boundary:** bind black-box and differentiable adapters to
   the same validator, fingerprint, dispatcher, and observation schema.
4. **Compact comparison report:** emit path, graph, run, loss, diagnostics, and
   provenance in one hash manifest.
5. **Game adapter:** load that manifest and replay without synthetic fallback.
6. **Reproduction:** execute the documented workflow from a clean pinned
   worktree and verify byte-stable status on restart.

## Exit criteria

The v0 milestone exits only when all work packages operate on one real compact
campaign. Separate synthetic successes do not compose into completion by
themselves. Once complete, the project chooses the most informative axis to
scale based on observed bottlenecks rather than assuming seed count is first.
