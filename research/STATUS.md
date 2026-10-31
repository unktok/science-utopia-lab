# Program status

Updated: 2026-10-31

## Overall position

The project has a working stochastic simulation, evaluation environment, and
persistent closed-loop controller. Metric-Conditioned Optimization Study v1.1
has completed its optimization phase from clean source commit
`1078279d1ce833afe9ffb6b7c262da15357b76ab`: all 45 logical design-seed rows
are terminal, every arm observed exactly five suggestions, and all three arm
winners were sealed simultaneously before any held-out seed was registered or
run. All 15 common held-out runs are now complete with no technical failure,
and the fail-closed cross-evaluation and paper slice have been published.
Provenance-safe initial-trajectory adoption reused eight complete
canonical trajectories in each of two target arms while refusing the one
failed source. This remains a synthetic research experiment, not a validated
science-policy result.

The working paper is now explicitly framed around the map
`objective -> search path -> frozen system -> held-out profile`. The original
Suto paper's fixed, investigator-selected intervention comparisons are treated
as the base simulator's contribution rather than repeated as this project's
main claim. Decision 0020 records the revised claim boundary and next
experiment.

A separate miniature backend now generates new numeric mechanism programs
and custom nodes, mutates graph/process structure, and differentiates the
complete relaxed recurrent world. A clean recorded run at `c035d1d` used a
Qwen3-8B-generated SignalBoost rule and initial attributes under production and
burden losses; frozen-input reproduction and independent discrete recomputation
passed. This is a new executable numeric model. The full original Qwen-agent
simulator, its token generation, and arbitrary generated institutions are not
yet combined in one differentiable execution path. See the
[recorded result](results/generative-program-world-v1.md).

The next non-scale extension is direct implementation-code generation, not
another numeric-rule catalog. Generated Python mechanisms now have a generic
JSON/port/state contract, isolated no-network container execution, checkpointed
graph integration and a local-Qwen proposal/repair path. Production PaperTracker
integration tests pass. Qwen-generated initial source now executes and passes
frozen replay and split checkpoint/resume; result-conditioned revision failed
three technical attempts, so source optimization is not complete. See the
[initial execution/failure result](results/generated-code-mechanisms-v1.md).
This does not yet install arbitrary new protocols and
consumers in the original live researcher lifecycle. The explicit
[non-scale limitation inventory](audits/non-scale-limitations-v1.md) distinguishes
these gaps from seed/population/budget scale.

Repository: `/Users/shiro/unktok/dev/science-utopia-lab`

Remote: `unktok/science-utopia-lab`

## Capability map

| Layer | Status | Evidence / next gap |
|---|---|---|
| local Qwen3-8B simulation | operational | stable four-year runs through Ollama/Metal |
| repeated seeded execution | operational | registry, retry, checkpoint, provenance |
| parameter design space | partial | eight parameters; first closed loop can use this fixed topology |
| measurement | executable v1 | participation, topic spread, burden, coverage, attrition, activity, funding/resource diagnostics |
| semantic instrumentation | prospective report-only slice | default-disabled explicit producer API, run/system/model-bound append-only stream, and fail-closed checkpoint/resume; not wired into the current simulator or optimizer |
| optimization loss | v1.1 optimization complete | participation/review, topic-entropy, and review-burden arms each exhausted five suggestions under the same search conditions |
| metric / objective landscape | prospective report-only v1 | three frozen probes audited as constructs; nine plural future metric cards and a machine-checkable objective graph; no active campaign effect |
| objective constitution compiler | prospective synthetic-tested v1 | versioned stakeholder/construct/horizon/distribution/risk/tradeoff/Goodhart/evidence contract compiles only hash-verified validated metric cards into phase LossSpecs; no real metric promoted |
| held-out evaluation metrics | complete | all 15 common-split runs completed; five seeds for each of three frozen arm winners, with no terminal technical failure |
| held-out reporting | published experimental slice | commit-pinned report, independent revalidation, loss/metric tables, paired effects, three final figures, and atomic NeurIPS insertion are complete |
| candidate generation | integrated foundation | random/Sobol plus generic black-box `ask/tell` API |
| closed-loop optimizer | operational | restart-safe ask/tell plus multi-loss study controller, winner seal, and held-out firewall |
| post-optimization comparison | complete v1.1 | two distinct frozen designs, descriptive loss-dependent rank reversal, and no universal winner; all nine paired held-out loss intervals contain zero |
| parallel campaign execution | measured | bounded workers safe; one local Ollama endpoint gives no material n=4 speedup |
| canonical event replay | integrated | deterministic sidecar and game-view payload |
| Evaluation System API | first vertical slice | one example mechanism family, not the project abstraction |
| whole-system `SystemSpec` | prospective communication and government mechanisms | sealed plans map exact broadcast/digest and catalog-derived stateful government overlays into default-off native execution; government policies have delayed, fingerprinted, checkpointable evaluation/funding effects and canonical causal lineage |
| structural system optimization | joint synthetic slice | 770 valid graphs jointly vary evaluation, publication, funding, government, communication, connections, and latency through one fingerprint-bound ask/execute/loss/tell boundary |
| differentiable optimization | prospective synthetic-tested v0 | ObjectiveSpec-conditioned whole-system relaxation, analytic gradient, deterministic projection, and black-box outer validation are executable on synthetic fixtures; no simulator data, real metric, or active campaign input is used |
| optimization continuum | synthetic-tested common boundary | parameters (6 raw variables), mechanism configuration (16), and node/edge structure (26) are nested over one six-family template; black-box, gradient, and hybrid methods share projection and opaque outer evaluation; schedule/latency and model-backed execution remain open |
| generative mechanism programs | executable numeric miniature | typed ASTs encode input, parameter, memory and update rules; search synthesizes new rules and custom nodes, changes edges/delays/order, and can remove every institutional node; generated programs also run/checkpoint in the existing generic graph runtime |
| generated implementation code | recorded initial execution proof; optimization incomplete | Qwen-generated Python/new schema executes through production PaperTracker and a ledger; frozen replay and checkpoint/resume pass; code revision fails, and semantic memory/reference limitations remain; no automatic differentiability or full live-researcher integration |
| direct whole-world differentiation | executable numeric miniature | autograd traverses complete recurrent agent/world transitions; six parameter/rule/node/edge/delay/schedule gradient groups pass representative central differences; hard projection and outer evaluation share the numeric transition equations; full legacy Qwen simulator and token generation remain outside autograd |
| generative lab viewer | recorded and browser-verified | checksum-bound events, generated SignalBoost rule, graph/process, six-agent state and search paths load into `game-ui-v2/generative.html`; two losses × four selected-system views; Chrome verification passed with zero exceptions/failed requests and no mobile overflow |
| game UI | verified research arcology plus result-blind relay | the existing replay/sandbox/observatory views now include a separately hashed Common-Split Relay contract for 3 frozen systems × 5 seeds, current run, ETA, and technical failures; unfinished loss, metrics, ranks, model output, and provisional winners are rejected |

## Metric-conditioned study execution snapshot

The scientific independent variable is the optimization `LossSpec`. The
primary outcome is the resulting optimized `SystemSpec` and its held-out
behavior—not whether a metric merely separates a small set of preselected
candidates.

| Stage | Current state |
|---|---|
| frozen protocol | v1 is retained at source commit `9f9868d5bac631f6c7c373229d7807a26695a62f`; active v1.1 is tagged `protocol/metric-conditioned-optimization-v1.1` at `1078279d1ce833afe9ffb6b7c262da15357b76ab` |
| three initial proposals per arm | byte-identical and registered; 27 initial logical runs total |
| total optimization budget | 45 runs = 3 losses × 5 candidate systems × 3 development seeds |
| completed optimization runs | 45 of 45 logical rows terminal: 30 complete and 15 technically failed; 29 rows were physically executed and 16 complete logical rows were provenance-safe adoptions |
| currently running | none |
| failures / retries | 15 terminal rows exhausted two attempts at the preregistered reviewer-capacity boundary; invalid suggestions retained `loss: null` and no numeric penalty or extra policy constraint entered an optimizer |
| remaining optimization runs | 0 |
| frozen arm winners | 3 of 3, sealed together in freeze `254c3366e921787ad6a36776801b1cb3b278e2cb36ef247da4cb127b6459244d` |
| held-out evaluation runs | 15 complete, 0 running, 0 planned, 0 failed; completed 2026-10-31 05:59 JST |

The three objectives selected two distinct designs. Participation/review chose
`db197e2eb5b1a`; topic entropy and review burden both chose
`d3536002463db`. Held-out ordering changed with the scoring loss, but all nine
paired loss contrasts have 95% intervals containing zero. This is a
descriptive objective-dependence result, not stable pairwise superiority or a
universal science-policy recommendation. The participation-selected design
had 11.6 accepted papers and complete review coverage on average, versus 4.0
accepted papers and roughly 0.55 coverage for the duplicated narrow-proxy
design, while carrying substantially higher review burden.

Across all arms, 45 physical process attempts consumed 107,966.6 serial
seconds (29.99 hours). Eight complete canonical trajectories were adopted into
each of the two other arms; all 16 links currently reverify their execution
identity, immutable bundle receipt, raw-file set, and source-attempt
provenance. The one failed canonical initial trajectory was not reused and was
executed independently in both target arms. A measured four-worker
microbenchmark against one local Ollama endpoint improved throughput only
about 1.016× while increasing request latency, so local concurrency is not
being treated as a fourfold speedup.

## Completed experiment boundary

The 30% versus 50% funding-capacity experiments are repeated evaluations of two
manually chosen design points, not a parameter search. Their historical
promotion decision remains preserved, but its protected-slice veto is not a
default constraint for future optimization.

## Next milestone

The preregistered common held-out comparison is complete. The next milestone is
**Miniature Whole-System Design Lab v0**, a breadth-first integration slice.
Before increasing seed counts or candidate budgets, it will connect one small
objective abstraction, structural mechanism grammar, result-dependent
black-box path, differentiable proposal path, model-backed outer evaluator,
canonical replay, and game view through shared `SystemSpec` and evidence
contracts. One or two development seeds and a short world are acceptable; the
gate is integration and reproducibility, not statistical confirmation.
The scale envelope, shared object graph, work packages, and exit criteria are
recorded in
[`components/miniature-whole-system-design-lab-v0.md`](components/miniature-whole-system-design-lab-v0.md).

The new Generative Program World completes a bounded rule-generation,
structural/process optimization, direct relaxed-world differentiation, canonical
evidence and viewing slice. It does not complete this broader milestone:
ObjectiveSpec compilation, richer artifact protocols, arbitrary-program
integration with the original Qwen-agent backend and city intervention remain.

Scale-up is deferred until this slice works. Later campaigns will add optimizer
seeds, equal-budget baselines, larger populations, longer horizons, and broader
held-out splits one axis at a time. Seeds 701, 709, 719, 727, and 733 remain
consumed by v1.1 and must not be reused as fresh held-out evidence. Seeds 523,
541, and 547 remain attached to the first campaign.

The next execution steps are:

1. **complete:** freeze and audit the three experimental loss arms, executable
   common evaluator, analysis contract, and seed firewalls;
2. **complete:** execute all five candidates per arm, safely adopt only valid
   byte-identical initial trajectories, and retain every invalid observation
   without a fabricated loss;
3. **complete:** freeze one winner per arm simultaneously before consuming the
   new study-held-out split;
4. **complete:** execute the five common held-out seeds for the three frozen
   winners and publish the cross-evaluation matrix, rank reversals, trade-offs,
   gaming, and generalization without selecting a universal winner;
5. **next:** freeze a miniature grammar spanning at least three mechanism
   families, with node/implementation and edge/schedule variation;
6. **partially complete:** black-box, differentiable, and hybrid proposal paths
   now share one discrete validator/projection and opaque evaluator interface
   on a synthetic six-family template; next connect that interface to the
   compact model-backed outer evaluator and add schedule/latency freedom;
7. publish canonical events and comparison artifacts that the game can display
   as objective, lineage, graph difference, world activity, and observed loss;
8. only after this integration gate, design larger replicated optimizer and
   held-out campaigns;
9. keep every model-backed run commit-pinned and separate from active
   development worktrees.

The first closed-loop result is frozen at revision `9a10029807d5`. Its untouched
held-out seeds must not be repurposed for tuning.
