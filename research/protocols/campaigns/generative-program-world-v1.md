# Generative Program World v1: miniature development protocol

Status: engineering protocol written before the recorded execution.

Purpose: exercise mechanism invention, structural/process mutation, direct
whole-rollout gradients, discrete evaluation and canonical viewing once at
small scale. No held-out or optimizer-superiority claim is planned.

## Frozen design

- Backend: numeric-program-world-v1 with explicit equations in the component
  design document.
- Initial institutional graph: research, evaluation, publication and funding
  programs, with a fifth generated custom mechanism when local Qwen generation
  is requested.
- Generation: recursive numeric ASTs, parameters, node/edge add/remove,
  zero-/one-period delay and schedule swaps.
- Population: 6 agents.
- Periods: 3.
- Development worlds: seeds 811 and 821. In the Qwen variant seed 811's
  attributes are generated once and frozen with model receipts.
- Loss arms: negative mean production and positive mechanism activity burden.
  No extra feasibility floor, welfare veto or promotion policy is introduced.
- Black-box: AdaptiveRandomSearch, seed 17, 2 initial proposals, budget 5.
- Direct gradient: Adam, 24 updates, learning rate 0.12, gradient norm clip 5,
  3 generated rule alternatives per initial node and complete directed
  supergraph over those nodes, process freedom.
- Hybrid: begin from the gradient-projected discrete system, then
  AdaptiveRandomSearch seed 29, budget 5.
- Explicit showcase: execute each of the eight mutation operator types once.
  These are interface tests, not additional optimizer-selected outcomes.

## Evidence and checks

1. Record a clean source commit, dependency/runtime context, source file hashes,
   all worlds and SystemSpecs, and the model digest/receipts when used.
2. Match whole-rollout gradients with central differences for parameters,
   rule choice, node gate, edge gate, delay and schedule. Tolerance is
   `1e-6 + 1e-4 * abs(numerical_gradient)`.
3. Preserve every proposal, its parent observation and complete/failed status;
   never use a numeric loss for a technical failure.
4. Record initial/final relaxed and exact projected losses and the projection
   gap; inspect whether improvements survive hardening.
5. Compare the *resulting designs* under both losses using the same two
   development worlds. This is development cross-scoring, not held-out evidence.
6. Emit canonical trajectory events and a checksum-bound view payload.
7. Re-run the frozen numeric inputs from the same source revision and verify
   program identities, losses and event hashes (excluding wall-clock fields).

## Interpretation boundary

The gradient method has direct access to numeric simulator derivatives while
black-box search sees scalar results. Budgets are deliberately small and not
matched for computation or information. Any observed difference is an
engineering observation, not method superiority.

The numeric world and generated Qwen attributes are synthetic modelling
objects. Qwen text generation is outside autograd. The experiment does not
extend arbitrary graph execution or differentiation to the original full
ScienceUtopia simulator. That integration remains explicit future work.
