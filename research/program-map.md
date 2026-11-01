# Science Utopia Lab — program map

Updated: 2026-11-01

The active acceptance gates are
[non-scale completion v6](milestones/2026-11-01-non-scale-completion-v6.md).
The [status page](STATUS.md) is the current execution ledger; old milestones
remain historical. Population/seed expansion is not the next task.

## Current original-goal map

| Original goal | Implemented interface | Evidence already available | Remaining non-scale boundary |
|---|---|---|---|
| Change the objective and optimize the scientific system | Versioned LossSpec, independent evaluation metrics, durable black-box ask/execute/measure/tell | Parameter-level held-out study; v5 free-code/graph paths `[-1,-3,-3]` and `[.70,.45,.45]`, five physical worlds | Richer defensible objective constructs, useful scientific discovery and generalization are not established |
| Invent institutions rather than tune a fixed review template | Arbitrary sandboxed Python, explicit protocols, state, ports and outputs; LLM/external complete manifests | Actual Qwen-source execution and externally authored institutions; local-Qwen joint-generation failures are retained | Native effect consumers, security/compute limits and actor ontology remain explicit; external Codex authorship is not autonomous Qwen invention |
| Design system composition, process and relations | SystemSpec nodes/order/wires/latency; typed native plans and actual paper bundles; generic same-society migration | Six-year original-world equivalence and consequential activity edits in scripted native QA; actual code/graph execution | Annual native scheduler, original paper/corpus law and collaboration semantics still constrain the world |
| Optimize through a differentiable representation | Faithful local hard/soft operations, composed transition model, native-cost score-function backward; factorized code/protocol/wiring policies | Actual fresh-native v5 distribution update; v6 factorized six-year native QA and exact enumerated/finite-difference checks | Factorized v6 QA is not a new real-Qwen result; source-content/pathwise whole-world gradients are NOT achieved; transition fidelity failure remains |
| Continually redesign one scientific society | Objective-visible observation/proposal/consent/adoption/feedback session with complete checkpoints and crash recovery | Actual v6 a2: three years, two adoptions,130 replies, `[0,-5,-5]`; a1 failure retained; prospective interrupted-reply recovery QA | Sequential losses do not establish causal benefit; the designer itself is not improved |
| Make the system visible and game-like | English cyberpunk city, replay, graph/source editor, objective paths and exact-hash live adoption UI | Actual a2 browser: three intervals, two re-verified saved receipts, no duplicate POST/error/mobile overflow | Not a complete management game; presentation choreography is not scientific activity |

The two optimization workflows must not be merged in descriptions: a reset-world
campaign estimates design quality under an explicit loss; the persistent society
measures subsequent online intervals after adoption. Likewise, externally authored
institutional synthesis and finite-factor score-gradient optimization are
composable interfaces, not a demonstrated self-improving endogenous designer.

![Scientific-system design concept](../paper/figures/program-concept/science-system-design-program.png)

Concept, not completion evidence. [Current editable SVG](../paper/figures/program-concept/science-system-design-program.svg).
The [earlier progress-map SVG](figures/science-utopia-program-map.svg) is retained as history.

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

## Historical track snapshot (pre-native milestones)

The following table and immediate milestone are preserved as the earlier
planning snapshot, **not current tasks or evidence**. In particular, no numeric
miniature can substitute for containing and extending the original researcher
world. Use the current map above and STATUS for decisions.

Direction correction (Decision 0025): the original researcher world is a lower
bound to contain and extend, not an expressiveness ceiling. The new native
kernel binds open SystemSpec/code/LLM institutions to that live world; numeric
miniatures cannot substitute for this integration or for native differentiation.
Compatibility, new-protocol prompt delivery, decision replacement/removal and
checkpoint QA are implemented. See the native-kernel design/probe documents in
the index; unconstrained actor behavior, process generality and native gradients
remain open rather than being counted complete by the older numeric results.
The separate native Qwen probe now completed: five researchers/four years,
147 requests, 20 delivered messages and independently verified checkpoint/
replay/wire evidence. It is an integration result, not new optimized-policy
evidence; [result](results/native-science-kernel-integration-v1.md).

| Track | Current state | What is actually finished | Next evidence-producing step |
|---|---|---|---|
| Reproducible simulator | operational | local Qwen3-8B, repeated seeds, restart/provenance, longitudinal runs | keep completed v1.1 immutable while designing replicated campaigns |
| Metric-conditioned optimization | v1.1 complete | 45/45 logical development rows are terminal, three winners were sealed before held-out use, and all 15 common held-out rows completed | keep frozen as the parameter-level baseline; defer scale-up until the miniature whole-system slice works |
| Evaluation metrics | common suite, report-only semantic instrumentation, prospective objective landscape, and ObjectiveSpec compiler | executable diagnostics now sit beside versioned semantic events, missingness/gaming fixtures, a fail-closed recorder, a source-hash-bound audit of the current LossSpecs, nine metric cards/objective relations, and a constitution that requires governance, stakeholders, time, distribution, uncertainty, trade-offs, Goodhart audit, and measurement evidence before compiling future phase-specific LossSpecs; none changes the three frozen LossSpecs | wire prospective evidence into a separately preregistered campaign, validate constructs/cards, then make and seal the explicit normative ObjectiveSpec choice before compiling a new LossSpec |
| Whole-system abstraction | first native structural mechanisms beyond the legacy topology | canonical runs feed typed SystemSpec workloads; communication and government overlays have checkpointed causal lineage | freeze a three-plus-family miniature grammar and execute it through a compact model-backed world |
| Black-box optimization | baseline operational | opaque `ask/tell`, persistent adaptive random search, real result-dependent suggestion | produce one structural result-dependent proposal inside the shared miniature slice |
| Structural optimization | multiple production vertical slices | government and communication spaces already vary node presence, implementation, edge/fan-out presence, and latency through fingerprint-bound ask/execute/loss/tell boundaries | compose a small subset with evaluation and funding/publication in the shared miniature campaign |
| Differentiable systems | prospective synthetic-tested v0 | whole-system relaxation, analytic gradient, deterministic projection, and black-box outer validation work on synthetic fixtures | project one differentiable candidate into the same discrete miniature grammar and evaluate it in the same model-backed outer loop |
| Generated institution programs | recorded numeric miniature | recursively generated rules/custom nodes, graph/latency/order mutation, direct whole-world gradients and exact discrete evaluation ran from clean c035d1d; Qwen generated SignalBoost and initial attributes; frozen-input reproduction passed | extend the fixed numeric feature/effect protocol and connect generated programs to the full original Qwen-agent backend |
| Generated implementation code | initial model-backed execution recorded; code search incomplete | actual Qwen Python/new schema runs through isolated execution and production PaperTracker, with exact replay/resume; result-conditioned revision fails technically and source-inspection exposes weak memory/actor references | separate protocol/code synthesis and repair, jointly generate producer/consumer protocols, then connect them to live researcher behavior; see the explicit non-scale limitation inventory |
| Generative lab evidence view | browser-verified | two losses, four selected-system views per loss, programs, graph, six-agent state, search paths and canonical events load from one recorded artifact | connect intervention/branch creation to the city without duplicating transitions in the browser |
| Game and replay | research arcology, replay, sandbox, branch comparison, and optimization observatory exist | the pixel-art hub already consumes canonical evidence while separating presentation-only choreography | bind the miniature objective, black-box/differentiable lineage, graph differences, world events, and losses into one playable research view |
| Paper and scientific graphics | held-out result published; narrative revised | automatic evidence slice plus objective-conditioned framing, search-path interpretation, claim boundary, and Suto/Lab contrast | add replicated optimizer comparisons and parameter/mechanism path graphics when new evidence exists |
| Compute | measured | one local Ollama endpoint at four workers gave only about 1.016x throughput | use independent endpoints/GPUs for material parallel speedup; retain seed isolation |

## Historical dependency logic

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

## Historical immediate milestone (superseded)

Metric-Conditioned Optimization Study v1.1 is complete. The next milestone is
Miniature Whole-System Design Lab v0, which prioritizes breadth before scale:

1. choose one versioned miniature ObjectiveSpec and its loss/diagnostics;
2. freeze a small structural grammar with at least three mechanism families;
3. generate result-dependent black-box and differentiable candidates;
4. project both into the same discrete SystemSpec validator;
5. execute them in a short, small-population, model-backed world;
6. freeze common comparison and canonical replay artifacts;
7. inspect the objective, search paths, graph differences, world activity, and
   losses in the game UI.

Only after this works do we increase seeds, optimizer replications, candidate
budgets, population, or horizon. Model-backed runs remain clean,
commit-pinned, and separate from active development worktrees.

