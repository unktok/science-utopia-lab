# Science Utopia Lab — program map

Updated: 2026-10-31

![Science Utopia Lab program map](figures/science-utopia-program-map.png)

Editable source: [`science-utopia-program-map.svg`](figures/science-utopia-program-map.svg).

## What this project is trying to do

Treat a complete scientific system as a design object. Evaluation, publication,
funding, governance, communication, and other mechanisms may be added, removed,
replaced, parameterized, or eventually rewired. Run candidate systems as
stochastic simulations and study which institutions emerge as desirable under
different explicitly chosen objectives.

The central experiment is **metric-conditioned system optimization**:

```text
choose optimization metric A -> optimize the system -> freeze system A*
choose optimization metric B -> optimize the system -> freeze system B*
choose optimization metric C -> optimize the system -> freeze system C*
                                              |
                                              v
                 evaluate A*, B*, C* on the same held-out metric suite
```

Here, an optimization metric (`LossSpec`) is analogous to a training loss: it
changes which system the optimizer searches for. A held-out evaluation metric
(`EvaluationMetricSpec`) is analogous to accuracy, F1, calibration, or a test
set diagnostic: it is used after candidates are frozen to understand what each
objective produced. Technical validity and an optional policy decision are
separate again. Objective resolution is useful QA, but it is not the research
question by itself.

Accordingly, the central comparison is a matrix: rows are systems obtained by
optimizing different losses, while columns are shared held-out evaluation
metrics. A result such as “loss A produced system A*, which scores this way on
metrics A/B/C” is the intended evidence. Testing whether loss A can reliably
distinguish two already chosen systems is only supporting measurement QA.

The paper-level claim is deliberately narrower and clearer: v1.1 is the first
existence proof of the full map above. It is not yet evidence that the baseline
optimizer is sample-efficient, that each objective yields a distinct design,
or that the whole mechanism graph has been optimized. These gaps define the
next experiment rather than being hidden as implementation details.

## Current tracks

| Track | Current state | What is actually finished | Next evidence-producing step |
|---|---|---|---|
| Reproducible simulator | operational | local Qwen3-8B, repeated seeds, restart/provenance, longitudinal runs | keep completed v1.1 immutable while designing replicated campaigns |
| Metric-conditioned optimization | v1.1 complete | 45/45 logical development rows are terminal, three winners were sealed before held-out use, and all 15 common held-out rows completed | replicate paths with larger valid budgets and multiple optimizer seeds |
| Evaluation metrics | common suite, report-only semantic instrumentation, prospective objective landscape, and ObjectiveSpec compiler | executable diagnostics now sit beside versioned semantic events, missingness/gaming fixtures, a fail-closed recorder, a source-hash-bound audit of the current LossSpecs, nine metric cards/objective relations, and a constitution that requires governance, stakeholders, time, distribution, uncertainty, trade-offs, Goodhart audit, and measurement evidence before compiling future phase-specific LossSpecs; none changes the three frozen LossSpecs | wire prospective evidence into a separately preregistered campaign, validate constructs/cards, then make and seal the explicit normative ObjectiveSpec choice before compiling a new LossSpec |
| Whole-system abstraction | first native structural mechanism beyond the legacy topology | canonical runs feed typed SystemSpec workloads, validated legacy-compatible graphs compile to sealed plans, and an exact broadcast/digest communication overlay now executes through the production simulator handler with canonical lineage, latency, fingerprinted checkpoint/resume, and default-off isolation from legacy citation | implement the next unsupported mechanism runtime, then execute separately preregistered structural campaigns after the frozen baseline closes |
| Black-box optimization | baseline operational | opaque `ask/tell`, persistent adaptive random search, real result-dependent suggestion | compare random, Sobol, Bayesian, and evolutionary methods under equal budgets |
| Structural optimization | multiple production vertical slices | 145 government candidates and a separate 97-candidate communication space vary node presence, implementation, edge/fan-out presence, and latency; every candidate executes through a fingerprint-bound black-box ask/execute/loss/tell and checkpoint boundary | compare these structures under research LossSpecs after the frozen eight-parameter baseline closes |
| Differentiable systems | not started | conceptual direction only | differentiable surrogate/relaxation after stable black-box targets and measurements |
| Game and replay | research arcology, authoritative operations/interior/life-course layer, system sandbox, and optimization mission control | a pixel-art hub connects verified replay, the separate synthetic graph editor, and the hash-bound study snapshot; Evidence Quay, four institutional cutaways, and researcher dossiers bind activities, resources, active state, papers, reviews, and funding to cursor-bounded canonical events/frames while keeping rooms, poses, relationship layout, motion, packets, lighting, and narrative styling presentation-only | add verified collaboration/evidence navigation and connect the newly frozen winner fingerprints through the read-only adapter |
| Paper and scientific graphics | held-out result published; narrative revised | automatic evidence slice plus objective-conditioned framing, search-path interpretation, claim boundary, and Suto/Lab contrast | add replicated optimizer comparisons and parameter/mechanism path graphics when new evidence exists |
| Compute | measured | one local Ollama endpoint at four workers gave only about 1.016x throughput | use independent endpoints/GPUs for material parallel speedup; retain seed isolation |

## Dependency logic

The project is deliberately not a single linear backlog.

- The research core now moves from an engineering closed loop to the first
  comparison of **systems optimized under different objectives**.
- The system-abstraction track now executes small family-independent mechanism
  graphs. It next expands from examples to checkpointable production adapters,
  so the optimizer may change mechanisms and graph structure rather than only
  eight parameters in one topology.
- The game track consumes canonical replay; it does not reimplement research
  logic. It can progress while commit-pinned experiments run elsewhere.
- The paper/graphics track records claims only after their evidence boundary is
  clear, but can continuously improve explanatory diagrams and methods text.
- Differentiable optimization is downstream of a trustworthy simulator target
  and held-out evaluation suite; otherwise it would optimize an undefined
  proxy faster.

## Immediate milestone

Metric-Conditioned Optimization Study v1.1 is complete, including its common
held-out split. The next milestone is to determine whether the observed
objective-conditioned patterns survive a stronger optimization design:

1. preregister multiple optimizer seeds and a larger valid evaluation budget;
2. compare adaptive search with equal-budget random and Sobol baselines;
3. report incumbent loss versus evaluation count and proposal lineage;
4. collapse duplicate system fingerprints in institutional comparisons;
5. broaden the objective family through the Objective Constitution boundary;
6. seal a separate simulator-backed structural campaign over mechanism graphs.

In parallel, connect the verified game views to the completed evidence package
and continue turning the generic mechanism runner into production adapters.
Long model campaigns must run from a clean, commit-pinned worktree, separate
from active game and abstraction development.

