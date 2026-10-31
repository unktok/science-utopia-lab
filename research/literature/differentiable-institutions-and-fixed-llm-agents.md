# Differentiable operations, fixed LLMs and multi-agent systems

Read: 2026-10-31. Primary-source notes and implementation implications, not a
claim that this project has implemented every method or that these works are
new. The user proposes softening memory access/selection without impoverishing
the science system; model weights remain fixed, institutions are optimized.

## Operations that can have paired hard and soft forms

| Operation | Primary method | Meaning for this project |
|---|---|---|
| Indexed memory access | [Neural Turing Machines](https://arxiv.org/abs/1410.5401) uses differentiable addressing/read/write | A reference or routing choice can be represented by attention weights; tensor memory must remain in the graph across time |
| Categorical selection | [Gumbel-Softmax](https://arxiv.org/abs/1611.01144) relaxes categorical sampling | Appropriate for declared stochastic choices; deterministic softmax addressing is not automatically a Gumbel reparameterized sample |
| Sorting | [NeuralSort](https://arxiv.org/abs/1903.08850) provides a continuous row-stochastic relaxation of sorting | A score vector can produce a soft rank matrix during fitting and an actual permutation during hard execution |
| Matching | [Gumbel-Sinkhorn](https://arxiv.org/abs/1802.08665) develops continuous matching/permutation relaxations | Sinkhorn normalization can soften an assignment matrix; deterministic Sinkhorn without Gumbel noise is not the full stochastic method |

Current implementation uses deterministic addressing/branch relaxation,
NeuralSort and deterministic Sinkhorn paired with exact linear assignment.
No Gumbel-sampling implementation is claimed. At ties/multiple optima the soft
limit need not equal a particular deterministic hard tie-break. Low temperature
can also cause numerical or gradient problems; a calculus check is not a world
fidelity guarantee.

## Agents and groups: what is actually differentiated?

- [DIAL](https://arxiv.org/abs/1605.06676): during centralized learning,
  agents pass derivatives through continuous/noisy communication channels;
  execution can be decentralized. This establishes a genuine inter-agent
  differentiable communication route, not that arbitrary natural language or
  external LLM APIs become differentiable.
- [CommNet](https://arxiv.org/abs/1605.07736): continuous communication among
  cooperating neural agents is learned jointly with policies. Relevant to
  representing coordination, but our current target is institutions surrounding
  fixed researcher models, not retraining their policies.
- [GPTSwarm](https://arxiv.org/html/2402.16823v1), sections 2.3–2.4: agents
  compose as graphs; edge selection uses REINFORCE over a graph distribution,
  while node prompts are revised separately. The paper explicitly notes that
  differentiable graph sampling does not remove LLM tokenization opacity.
- [G-Designer](https://arxiv.org/html/2410.11782v3), section 4.3: a graph
  encoder/decoder proposes task-dependent communication topologies; external
  API-dependent utility is optimized with policy gradients. It does not
  establish pathwise backpropagation through complete LLM dialogues.
- [LOLA](https://arxiv.org/abs/1709.04326): policy updates account for another
  agent's anticipated learning update. Interesting for eventual adaptive science
  societies, but not a reason to train researcher weights in the present project.

These are inspirations with different assumptions, not interchangeable proofs
that a complete LLM society can be differentiated exactly.

## Fixed LLMs can still transmit input gradients

[Prompt Tuning](https://arxiv.org/abs/2104.08691) learns continuous prompts with
a frozen language model. This is direct evidence that freezing pretrained
weights need not stop input derivatives. For our setup, an autograd-capable
forward with continuous institutional inputs would be needed. Discrete text
prompt construction and the current Ollama JSON API do not expose such a
computation graph. The useful distinction is weights fixed versus responses
fixed, not "training" versus "inference" alone.

[TextGrad](https://arxiv.org/abs/2406.07496) propagates textual feedback to revise
compound systems. Its gradient analogy concerns natural-language feedback,
not ordinary numeric automatic differentiation through token generation.
It is a plausible source/architecture proposal method; do not label its text
critique an exact derivative of native loss.

## Current implementation and next extension

`program.tensor.v1` is a compositional institution representation embedded in the
actual native graph. Hard execution commits through real consumers; observed
traces are replayed with autograd across represented nodes/edges and memory.
Opaque feature extraction, LLM decisions and subsequent world feedback remain
conditioning data during a trace fit. A fresh native rollout rechecks the
projected proposal under the unchanged fixed model and declared LossSpec.

Our inference from the literature: add local input-gradient or identified
response adapters at explicit boundaries, and compare their gradients/proposals
against fresh native execution. Never claim that a frozen trace captures all
institution-induced changes in future researcher behavior. Do not simplify the
whole world into fixed equations merely to advertise end-to-end autograd.
