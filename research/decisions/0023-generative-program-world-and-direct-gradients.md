# Decision 0023: Make institution rules executable data and differentiate a miniature world

Date: 2026-10-31

Status: implemented and recorded

The user's clarification requires both the creation of new mechanism rules
and the optimization of their relationships/processes. A fixed catalogue of
implementation names does not satisfy that requirement. The next increment
therefore represents institution rules as typed bounded numeric program ASTs.
One interpreter executes every valid generated rule in a new numeric world
and in the existing generic graph runtime.

The generative design space can synthesize and mutate rules, create custom
nodes, remove nodes (including all institutional nodes), rewire connections,
change latency and swap execution order. The black-box optimizer continues to
see opaque candidate JSON and versioned loss observations.

Direct differentiability is established over a complete recurrent numeric
world: mechanism invocations, memory, messages, world updates and loss are
one tensor calculation. Discrete choices are explicitly relaxed and projected;
the exact projected world is evaluated separately. The initial implementation
checks representative derivatives in all six variable families against
whole-rollout finite differences. It is distinct from Decision 0018's
hand-written analytic surrogate surface.

The first recorded experiment ran from clean commit `c035d1d` in an isolated
detached worktree. Qwen3-8B generated the SignalBoost program and initial
attributes; the numeric worlds then ran under two losses. A frozen-input
reproduction matched the numerical and structural artifacts exactly.

Claim boundaries remain explicit:

- the AST operator vocabulary, input/effect protocol and miniature world laws
  are fixed and versioned;
- a gradient episode has a finite generated program bank and supergraph;
- exact discrete thresholding and Qwen token sampling are outside autograd;
- arbitrary generated programs are not yet wired into the complete original
  longitudinal Qwen-agent simulator;
- the miniature result does not complete the broader original backend/game/
  ObjectiveSpec integration gate in Decision 0021.

The next source changes improve generic symbol scoping and viewer disclosure.
The c035d1d evidence remains immutable; subsequent runs use their own source
revision. New scale-up is still deferred until the richer integration works.
