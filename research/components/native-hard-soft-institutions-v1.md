# Native operational institutions with hard and soft interpretations

Updated: 2026-10-31. Implements Decision 0027, not full native-world autograd.

## What is new

`utopia/system/tensor_program.py` adds `program.tensor.v1`, a bounded tensor
dataflow IR with dynamic input shapes, explicit parameters, persistent tensor
memory, arbitrary composed nodes and multiple output ports. Arithmetic,
matrix multiplication, memory addressing, branching, sorting and matching are
operations, not a menu of named scientific institutions. No forced tanh or
invented scientific production equations are applied to all outputs.

The same program has hard and soft operational interpretations:

| Operation | Hard execution | Soft fitting |
|---|---|---|
| address / choose | one-hot argmax | temperature-scaled softmax |
| gate / branch | binary threshold and selected branch | sigmoid gate and weighted branches |
| sort | stable descending permutation | NeuralSort rank matrix |
| match | exact maximum-weight assignment | log-space Sinkhorn matrix |
| memory | explicit tensor state updates | same updates retaining autograd history |

Inputs, graph references, tensor ranks/elements, schemas and finite values are
validated. No generated Python is evaluated on the host. Arbitrary isolated
Python and native LLM institutions remain available; they are not forced into
this IR, nor silently made differentiable.

## Actual original-world connection

The native kernel registers the tensor implementation beside original phases,
Python and LLM institutions. A generic handler consumes numeric payloads from
typed ports, carries actor/artifact records and persistent memory, and emits
new tensor protocols. Generated Python/LLM producers may choose how actual
world records become inputs; consumers choose what tensor outputs do.

The concrete example retains original research/retrieval/reviews/publication/
funding. A Python producer extracts real paper review features and identities.
A tensor institution addresses threshold slots, gates decisions and remembers
past accepts. A Python consumer commits the decision tensors to native
conference/PaperTracker state. This is programmer-authored policy, not science
world laws or LLM institutional discovery.

`native.tensor.executed` retains actual inputs, source references, hard outputs,
identity records, before/after memory and program fingerprint. Completed-year
resume reproduces scientific state and complete kernel evidence in QA.

## Gradients without discarding the world

`utopia/optimization/native_relaxation.py` verifies hard trace reproduction and
replays represented institutions with autograd. Tensor-to-tensor edges and
memory across years stay in the graph. Native/code/LLM observations remain
frozen conditioning inputs during the fit. A short explicit conditional
objective updates selected institution parameters, then the candidate program
returns to a normal SystemSpec and a fresh native execution.

The conditional soft objective, its hard projection on the frozen trace, and
the resulting native-world LossSpec are separate values. A fresh fixed-LLM
world may diverge materially; only its actual loss enters outer selection.
Freezing LLM weights is intended; freezing its counterfactual reactions is not
an assertion that those reactions are irrelevant or differentiable here.

QA checks soft derivatives against numerical differences, unique-optimum
hard/soft low-temperature agreement, explicit tie disagreement, coupled state
gradients, native decision counts, learned-proposal reexecution, tamper failure,
completed-year resume, and a gradient crossing TWO actual native institution
nodes. The first full focused regression passed 648 tests with three skips;
the additional gradient-scope metadata is separately rechecked.

## Runnable short native probe

From clean pinned source, local Docker/Ollama and original data cache:

```sh
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=1301 /path/to/venv/bin/python \
  scripts/run_native_relaxation_probe.py --output outputs/native-relaxation \
  --data-cache /path/to/cache --years 2 --steps 30 \
  --loss research/objectives/losses/native-accepted-count-engineering-v1.json
```

Two native systems; first real trace -> 30 inexpensive tensor updates -> second
real execution. The accepted-count target is explicitly gameable engineering,
not scientific value. Protocol: `protocols/campaigns/native-trace-relaxation-v1.md`.
Live evidence must be recorded separately; QA alone does not claim it happened.

## Remaining boundaries

- Exact full-world gradients, gradients through the current Ollama endpoint,
  arbitrary Python, text construction and discrete native state are absent.
- Soft graph computations do not yet freely rewrite native phase prerequisites.
- Tensor vocabulary is a compositional option, not all possible programs.
- Soft ties, low-temperature instability and state-dependent branch divergence
  can invalidate apparent improvements; report outer failures and gaps.
- Multi-node tensor communication is not proof of differentiating natural-
  language dialogue among the original fixed Qwen researchers.

Primary-method notes and fixed-LLM extension routes:
[research review](../literature/differentiable-institutions-and-fixed-llm-agents.md).
