# Generative Program World v1

Status: executable miniature; the full legacy Qwen simulator remains a separate backend.

## What this adds

The earlier continuum joined adapters around a hand-written synthetic loss
surface. This implementation adds an interpreted mechanism language, program
and graph generation, and a recurrent agent world. Candidate institutions now
contain their executable rules, rather than only the names of registered
implementations. Gradients are computed through the world's transitions.

The implementation has four objects:

1. A **mechanism program** declares typed numeric inputs, bounded parameters,
   vector memory, an output expression and simultaneous memory updates.
2. A **SystemSpec** contains program nodes, explicit effects on the world,
   typed signal connections, delays, and schedules.
3. A **world** holds six agents' quality, novelty, resources and accumulated
   knowledge. Its versioned transition equations define the environment.
4. A **LossSpec** selects which measured world output to optimize.

Evaluation and funding are examples of nodes. A generated custom node can
represent replication, mentoring, common infrastructure or another mechanism
without adding a family-specific interpreter branch.

## The institution language

```json
{
  "schema": "scienceutopia.mechanism-program.v1",
  "inputs": {"quality": "vector", "signal": "vector"},
  "parameters": {
    "weight": {"initial": 0.5, "minimum": -2.0, "maximum": 2.0}
  },
  "state": {"memory": 0.0},
  "output": {
    "op": "add",
    "args": [
      {"op": "mul", "args": [{"param": "weight"}, {"input": "quality"}]},
      {"input": "signal"}
    ]
  },
  "updates": {
    "memory": {"op": "add", "args": [{"state": "memory"}, {"input": "quality"}]}
  }
}
```

Expressions support addition, subtraction, multiplication, square, sigmoid,
tanh, population mean, softmax and threshold. Scalar results broadcast to the
population. Outputs and updated state are bounded by tanh. Maximum expression
depth is 10 and total program AST size is 160. Programs are JSON interpreted
by a fixed operator table; they are never evaluated as Python source.

The interpreter accepts arbitrary declared numeric input/state/parameter names.
The miniature world supplies the five features `quality`, `novelty`,
`resources`, `knowledge` and incoming `signal`. Adding new kinds of world
observation requires changing the world's feature protocol explicitly.

A generated program executes through the same generic interpreter as a
hand-written one. `register_program_interpreter` also connects it to the
existing `DeterministicGraphRunner`; the ordinary graph runner's checkpoint,
causal lineage and event machinery then apply without per-program handlers.
The numeric-world transition loop below is a separate backend.

## Generation and black-box optimization

`GenerativeSystemSpace` recursively synthesizes expression trees and mutates:

- an AST subtree or parameter;
- mechanism addition with a newly synthesized program;
- mechanism removal and its incident edges;
- edge addition/removal;
- zero-/one-period delivery delay;
- processing order.

This is compositional generation within a bounded language, not unrestricted
source-code invention. The resource envelope is 0–8 nodes and at most 56
edges. Mutation choices account for the current graph's available operations.
`AdaptiveRandomSearch` only receives candidate JSON and scalar observations.
Later candidates record the development observation that they depend on.

The optional local Qwen adapter also generates a rule, a semantic label,
explicit world effects and an initial six-agent world. Responses are parsed
and validated before execution; invalid output is retried once and then
fails explicitly. Model digest, exact request/response hashes and token/runtime
counts are recorded. There is no fixture substitution after a failed query.

## World equations

Each mechanism reads current agent attributes, its previous memory and a sum
of delivered signals, emits a vector, and updates its memory. A mechanism's
declared effects contribute to allocation, access, learning or effort. Family
labels do not change the transition code.

For each period, with population size `N`:

```text
allocation = N * softmax(allocation_effect)
resources_next = 0.65 * resources + 0.35 * allocation
production = quality * sigmoid(resources_next)
                     * sigmoid(effort_effect) * sigmoid(access_effect)
knowledge_next = 0.85 * knowledge + production * sigmoid(learning_effect)
quality_next = sigmoid(logit(quality) + 0.3 * knowledge_next + 0.1 * learning_effect)
```

Novelty is initially fixed per agent. Measured outputs are mean production,
final knowledge, novelty-weighted knowledge, resource dispersion and mechanism
activity burden. These environment laws are explicit modelling assumptions.
They are not empirical laws of science, and no welfare constraint is implicit
in the loss.

This is an actual recurrent simulation with endogenous outputs. It is still a
deliberately small numeric model, not the legacy paper/manuscript Qwen world.

## Direct differentiation

`RelaxedProgramSystem` exposes four nested freedom levels:

| Freedom | Trainable design objects |
|---|---|
| parameters | bounded numeric parameters inside each rule |
| rules | parameters plus mixtures of recursively generated rule ASTs |
| graph | rules plus node and edge presence gates |
| process | graph plus delivery delay and schedule mixtures |

The tensor calculation includes every mechanism invocation, internal state
update, signal transmission, world transition and LossSpec term over every
simulated period. There is no analytic stand-in loss surface in this path.
The central-difference audit checks gradients of the *entire unrolled loss*
for six variable groups: parameters, rules, nodes, edges, delays and schedules.

Threshold uses its exact comparison in discrete execution and a sigmoid in
relaxed execution. Node/edge gates use sigmoid. Rule choice uses softmax.
Latency interpolates between zero- and one-period messages. Schedule choices
mix within-period executions and their resulting recurrent states. This
last operation approximates a distribution over complete trajectories; the
report states the approximation explicitly.

The gradient episode uses a finite generated rule bank and supergraph. It
cannot add a new AST operator or node by an ordinary derivative. The outer
black-box generator can change the program/graph structure and then start a
new gradient episode. The hybrid runs the ordinary discrete search from the
gradient-projected system.

## Projection and outer evaluation

Projection chooses rule argmaxes, thresholds node/edge gates, chooses delays
and a total schedule, instantiates trained parameter values, and validates the
resulting SystemSpec. An empty institution graph is allowed: the background
research world evolves with zero institutional effects. Unsupported projections
fail instead of being silently repaired. Only the exact discrete
programs are then passed to the opaque evaluator.

The report records relaxed loss, discrete loss and their signed gap. A lower
relaxed loss does not guarantee a better discrete system. Technical failure
receives null loss, while a numerically poor world remains a valid observation.
The same ordinary LossSpec semantics aggregate the two development worlds.

## Scope of Qwen and differentiability

Qwen can generate the initial attributes and the institution program. Those
outputs are frozen before optimization. Autograd covers the complete numeric
world but does not cover Qwen token generation. The original ScienceUtopia
LLM-agent simulator is not made differentiable by this module.

There are therefore two independently useful execution paths:

- existing Qwen longitudinal world: validated fixed-topology parameter search;
- new numeric program world: generated rules/topologies/processes and direct
  differentiation through the complete miniature rollout.

Connecting arbitrary generated programs back into the full longitudinal
paper/assessment/funding simulator remains a next integration task. A model
trained on real simulator trajectories and differentiable sampling or score
estimators would be separate future approaches, not current capabilities.

## Evidence and game view

`scripts/run_generative_lab.py` records all SystemSpecs, programs, proposal
lineage, world seeds/hashes, parameter traces, gradient audits, projection
decisions, exact outer results and code hashes. Raw results live in `outputs/`.

The same completed discrete trajectories export canonical agent registration,
mechanism execution and period completion events. `generative.html` in the
game UI displays the selected objective, generated rules, graph/order/delay,
agent state, optimization paths and event evidence. It never simulates the
scientific transitions in the browser. The checksum covers the exact payload
string to avoid cross-language float serialization ambiguities.

## Reproduce

Use a clean feature/experiment checkout for a recorded run:

```bash
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=42 .venv/bin/python \
  scripts/run_generative_lab.py \
  --output outputs/generative-lab-v1 \
  --ui-output game-ui-v2/public/data/generative-lab-v1.json
```

Add `--ollama` to generate a mechanism and initial world with the installed
`qwen3:8b`. To reproduce that exact numerical experiment without querying the
LLM again, use `--proposal-input path/to/qwen-proposal.raw.json` and a fresh
output directory. A new query, even with the same seed, is not a promise of
bitwise-identical text generation.

Open `game-ui-v2/generative.html` through the existing Vite server, or choose
`viewer.json` through LOAD RUN. The development flag `--allow-dirty-development`
is only for smoke testing and marks the source accordingly.

## Related primary literature

- [Liu et al., DARTS](https://arxiv.org/abs/1806.09055): continuous relaxation
  of discrete architectural choices; it motivates the design-space technique,
  not a claim of simulator or science-policy validity.
- [AgentTorch](https://openreview.net/pdf?id=JlBBoZBOeF): differentiable
  agent-based modelling; it motivates differentiating state transitions.
- [Kalyan et al., Neural-Guided Deductive Search](https://arxiv.org/abs/1804.01186):
  compositional program synthesis. This implementation uses a much smaller
  numeric grammar and no learned deductive search engine.

