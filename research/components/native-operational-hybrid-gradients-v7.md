# Operational representations and native hybrid gradients v7

This extends institutions inside the original native research world. It does not
replace its researchers, publication, costs, resources or fixed-LLM reactions
with new differentiable scientific production equations. Arbitrary isolated
Python and LLM mechanisms remain available outside the optional tensor IR.

## Concrete gaps addressed

| Previous gap | Operational extension | Remaining explicit boundary |
|---|---|---|
| Memory required hand-written arithmetic | Addressed `memory_read`, overwrite `memory_write`, additive `scatter_add` | Symbolic identities/text are not numeric memory coordinates |
| Addressing/routing had to be assembled from several low-level nodes | Hard/soft `route` and query-key-value `attention` | A soft mixture of numerical messages is not a derivative of natural-language interpretation |
| Stochastic operations had no explicit reparameterization input | `sample(logits, recorded_noise)` and `normal_sample(mean, scale, recorded_noise)` | Noise provenance/distribution is supplied by the author; the IR does not silently draw or certify it |
| Aggregation and numerical transforms were limited | `logsumexp`, `exp`, `log`, `sqrt`, `abs`, `minimum`, `maximum`, `clip`, `stack` | Invalid domains/nonfinite values fail rather than becoming invented losses |
| Native trace verification omitted recorded routed inputs/later memory-before | Hard replay now checks both against actual represented dependencies and recurrent memory | Native/code/LLM outputs are still conditioning observations, not newly differentiated transitions |
| Continuous Python institution parameters lacked a shared projection/evidence route | Exact bounded parameter addresses, optional explicit quantization, real installed source-parameter context receipts | Python parameters use native perturbation secants, not fabricated source autograd |
| Correct conditional backward could be mistaken for correct native derivatives | Independent actual-checkpoint endpoint extraction and native secant fidelity status | A fidelity failure remains a failure; finite-radius agreement never proves an exact whole-native Jacobian |
| Gradients/projections were separate from a verified reload | Hash-bound report plus remeasurement of saved endpoint checkpoints and code contexts on reload | Saved text/LLM calls are not executed or backpropagated during reload |

## Public APIs

`utopia.optimization.native_hybrid` provides:

- `continuous_coordinates(system, declarations)`: scalar addresses in tensor
  program parameters or arbitrary Python institution parameters. Source text,
  initializer state and world laws are not silently rewritten. A declaration
  records `id`, `mechanism`, JSON-pointer `path`, `lower`, `upper`, and `quantum`.
- `project_continuous(system, declarations, values)`: returns an executable
  SystemSpec and an exact patch/projection receipt. Clamping, boundary kinks and
  quantization have separate derivative annotations, not an automatic identity
  backward.
- `boundary_coverage(system, events)`: verifies hard tensor replay and reports
  represented numerical communication, conditioned numerical input, opaque
  native consumers and other numerical/non-numerical protocols. Declared graph
  routing and actually observed tensor dependencies are separate facts. IDs and
  text remain routable data without pretending they have numerical derivatives.
- `conditional_backward(trace, programs, trainable=..., terms=...)`: autograd
  through represented multi-node operations and recurrent state, checked against
  conditional central differences. This is a named conditional objective, not an
  undisclosed replacement for a native LossSpec.
- `native_endpoint(checkpoint, system, declarations, loss_spec, world=...,
  code_contexts=...)`: read-only independent extraction of all eight native
  measurements from a completed original-world checkpoint. It verifies exact
  source/model/corpus/seed/system, unchanged initialized world and native epoch
  evidence. Python parameter coordinates additionally require exact recorded
  container inputs/results bound to actual generated-code events.
- `hybrid_gradient(...)`: combines explicitly labelled represented conditional
  derivatives with actual native partial secants for opaque source parameters.
  The latter are numerical intervention measurements, not pathwise backward.
- `native_directional_fidelity(minus, plus, gradient)`: compares a declared
  prediction to fresh native endpoint losses along the *installed* coordinate
  displacement. Undeclared world/design changes fail. Coincident projected
  endpoints are undefined, not a zero derivative. A mismatch returns
  `failed-local-native-fidelity` independently of whether a later proposal wins.
- `endpoint_input_drift(...)`: exposes changed native conditioning/record shapes
  instead of assuming that researcher reactions stayed frozen.
- `save_hybrid_report` / `load_hybrid_report`: durable content receipt and, by
  default, independent semantic re-extraction of every included endpoint. No
  factory, model client or container runs during reload.

The original transition-surrogate and policy-score routes remain available.
This work does not relabel fitted local state models, finite differences,
REINFORCE, conditional tensor backward and pathwise native derivatives as one
estimator. Different routes retain their different estimands and evidence.

## Executable original-native roundtrip

`tests/optimization/test_native_hybrid_v7.py` runs the real six-year native
Simulation, original researchers/retrieval/reviews/publication/funding and real
networkless Docker code execution. Only the corpus/retrieval/HTTP provider is
scripted. HTTP answers depend on actual evolving accepted papers and resources;
fresh endpoint runs create fresh answers, not reused baseline traces.

The fixture composes native review records → arbitrary Python feature producer
→ an addressed institution → a second recurrent memory/attention institution →
actual native decision consumer. Exact hard tensor output counts reproduce the
native accepted-decision LossSpec. Conditional autograd and numerical checks
cross both institution nodes and years. A continuous parameter in the Python
feature source is separately measured by native perturbation, combined with
represented derivatives, projected, and reevaluated in the actual native world.

Four same-seed, small original-native worlds cover baseline, represented
perturbation, opaque parameter perturbation and projected hybrid proposal. This
is diagnostic software QA, not four independent statistical replicates or a new
Qwen result. The test explicitly requires correct conditional autograd AND a
failed local native fidelity check, so a conditional approximation gap cannot
be hidden by proposal improvement. A separate interrupted-year/cold-restart
continuation of the same fixture verifies new recurrent state and complete
native event/scientific-state equivalence to the uninterrupted execution.

Tests additionally cover hard/soft ties, gradients for the new operations,
explicit sampling noise, pre-allocation bounds, invalid numeric domains,
tampered routed inputs/memory, projected bounds/quantization, and forged endpoint
facts even when their outer JSON receipt is recomputed.

One combined local QA attempt hit the production-default 15-second Docker wall
limit during a tiny container. It was an infrastructure failure, not an objective
penalty or a successful result. The new fixture declares a separate bounded
60-second QA executor budget; production sandbox/default and live experiment
budgets are unchanged. No paid API or live Qwen inference is used.
