# 0027 — Open institutional invention first, paired operational relaxations

Date: 2026-10-31. User clarification: the main freedom axis is not us adding a
fixed catalog of hypothesis/experiment activities. It is the increasing freedom
to invent institutions, protocols, rules, wiring and processes. Richer science
activities may be useful but are not a prerequisite for institutional invention.
A compelling game remains desirable; an honest, inspectable game-like UI is an
acceptable first integration target.

## Fixed agents, trainable institutions

The optimization target is the institution/design, not learning Qwen weights
or redefining researcher personas. The same pinned LLM may react differently
to changed institutional inputs. **Frozen model weights are not a stop-gradient
through the input/output relation.** A local differentiable forward can freeze
weights while retaining input derivatives. The current Ollama HTTP interface
does not return those derivatives; do not pretend they exist or freeze all
future researcher reactions because weights are frozen.

## Implementation sequence

1. Keep arbitrary isolated Python and host-brokered LLM institutions available.
   A tensor vocabulary must not become the only legal institutional language.
2. Add a compositional tensor dataflow representation beside those routes, with
   the SAME program interpreted operationally (hard) or continuously (soft).
   Include addressing, branching, sorting, matching, memory and inter-node
   communication, not a catalog of review/funding algorithms.
3. Connect tensor outputs to actual native actions. Record genuine native
   inputs, identities, source fingerprints, hard outputs and memory transitions.
4. Differentiate the represented mechanism/communication/memory computations on
   these observed traces. Label frozen opaque inputs as conditioning data, not
   an exact derivative of the whole counterfactual world.
5. Project the learned program back into an executable SystemSpec and rerun the
   SAME fixed Qwen/native world. Only this native observation supplies the outer
   LossSpec. Keep conditional fitting loss separate from actual world loss.
6. Extend input/output gradient coverage at explicit opaque boundaries using
   an autograd-capable frozen-model backend, or an identified/validated response
   approximation/estimator. Measure fidelity rather than reducing world behavior
   until it is easy to differentiate. No inference-to-training migration or
   new model download is implicitly authorized by this decision.

Straight-through, policy-gradient, local tensor autograd, input-gradient through
a frozen LLM, learned behavioral surrogate and textual feedback are different
methods. Record which gradient actually ran. Arbitrary discrete text/code is not
automatically differentiable. Hard/soft ties can differ; report gaps, especially
when branching changes later researcher trajectories.

## Fast implementation gate

Use small native runs and short trace fits to complete end-to-end paths before
scaling seed budgets. Freeze only what the current run needs; do not turn every
engineering slice into a large policy-comparison study. Source/model/corpus
pinning, isolation, real losses and explicit failures remain required.
