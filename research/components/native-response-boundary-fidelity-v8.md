# Response-boundary refinement of the original native world v8

## Plan fixed before native QA

This is implementation QA, explicitly `scripted-fixture-not-native-results`.
It does not run Qwen, enlarge the population/seed study, replace the original
forward world, or modify any frozen source/output. The original six-year
Simulation, researcher classes, review parser, publication and funding remain.
The existing fixture has four original researchers; responses/retrieval are
scripted and source-pinned for reproducibility. Generated institution code runs
only in the existing networkless pinned Docker executor.

Budget: seven six-year native worlds, one fixture seed42. Calibration controls
are `[-0.25,0,0.25]`; the two unused verification controls are `[-0.20,0.10]`.
One additional world reevaluates a gradient-projected design, and one uses0.6
to test out-of-calibration rejection. No replacement world is drawn after a
failure. Temperatures `[1,0.2,0.05,0.01]` are compared **only on calibration
native losses**, then frozen before either unused endpoint is inspected.

The fixed scripted researcher answers depend on the actual institution signal
in HTTP inputs and on evolving native society. Importantly, the original review
parser calls `int(raw_score)`. That operation is retained in the native forward;
continuous-looking numeric replies must not be silently substituted for actual
integer review records.

## Representation and falsifiable estimands

Let theta be declared real institution coordinates, Z(theta) the numeric opaque
inputs actually observed by the institution graph, H its hard represented
objective, S_T its soft represented objective, and L the actual native LossSpec.
Fit a **local response operator**, not another annual world-state surrogate:

    R_hat(theta) = R_center + (theta-theta_center) J_hat
    Z_hat(theta) = P_T(R_hat(theta))
    d S_T / d theta = partial_theta S_T + partial_Z S_T d P_T / d R J_hat

R is either the observed post-parser numeric boundary or an explicitly verified
raw numeric reply boundary. P is then either identity or the native positive
integer truncation, with a separate soft staircase representation. Existing
generated tensor rules, tensor-to-tensor edges, and recurrent memories remain
in the differentiated execution. Python/text/native responses are not assigned
an invented autograd Jacobian. J_hat is learned from native interventions and
is neither an exact LLM derivative nor a score-function estimator.

The raw-review adapter is deliberately strict: each actual HTTP/SQL review
reply in a year must have the **same numeric value**, raw reply count must equal
the actual review counts, and original `int()` must reproduce every native
review-feature score. Heterogeneous replies without a known row correspondence
are unsupported; no averaging, padding or arbitrary deduplication is allowed.
The more general post-parser boundary fit remains available without this
uniform-cohort adapter. Numeric rows are joined by exact semantic record IDs;
shape/record/routing changes are exposed, not massaged into a fixed-size world.

Exact endpoint accounting separates four terms:

    delta L = direct-soft change + response-drift-soft change
              + change(H-S_T) + change(L-H)

Each cross-endpoint replay is a conditional computation, not a new native
counterfactual execution. At integer/discrete transitions a finite endpoint
secant is not a point Jacobian. A path integral of the fitted representation's
autograd predicts a **finite loss change** and is checked against both the
representation's own endpoint difference and unused native endpoints. Point
gradients, finite-radius checks, calibration error and unknown native paths
remain separate. No support extrapolation or zero imputation is permitted.

## Evidence and verification

To be completed with the fixed QA receipts, including all seven values, exact
source and endpoint hashes, training-only temperature selection, unused-point
errors, native directional comparison, raw/post-parser drift, failure records,
projection and read-only semantic reload. A positive scripted check is not
evidence of fidelity to actual Qwen or of beneficial scientific institutions.

## Pre-rerun amendment: real review information ingress

The first physical QA attempt at source `84701f3` stopped during year1 of the
first calibration world. The institution signal was present in actual research
direction HTTP inputs, but absent from the original review HTTP prompt. The
fixed scripted transport asserted its actual input rather than consulting the
institution parameter secretly. Therefore no review reply, completed native
world, loss or fidelity pass is claimed from that attempt. Its original pytest
temporary directory was:
`/private/var/folders/ry/w663wy7n4j52rjwfmd7rxbl40000gn/T/pytest-of-shiro/pytest-756/test_seven_original_native_wor0`.
It was subsequently removed by pytest's shared temporary-directory retention
while other tests ran. The source pin and reported failing assertion survive,
but raw immutability/replay for this partial attempt cannot be verified. This
is an explicit evidence-retention failure, not a successful or independently
audited native result. The new QA uses an explicitly named worktree `outputs`
base directory, outside shared pytest retention.

Before rerunning any fidelity world, add the explicit SystemSpec capability
`native.world.review-context-delivery.v1` →
`native.phase.review.with-delivered-context.v1`. A typed causal authorization
contains only exact messages actually delivered by the original context
receiver, addressed to actual actors. The review adapter cross-checks message
identity, body, actor, period and original input lineage against durable native
actor context. It appends only the authorized records to the original review
prompt, calls the original review stage/parser, records actual prompt hashes,
and restores the original method even if review fails. It neither invents a
teacher reply nor changes the original integer parser. The receiver preflights
the entire batch before mutation, rejects duplicate/future deliveries, and
retains typed authorization state across cold restarts. The host must explicitly
register the capability; registration without the opt-in spec changes nothing.

The amended fidelity budget is seven **fresh** six-year scripted worlds with
the same predeclared controls/temperature selection above, in addition to the
one failed partial attempt. No result from the failed pin is silently relabelled
as this extension. Separately, two compatibility comparisons each use one
continuous six-year reference and one interrupted/cold-resumed society:
(i) baseline spec with registry absent versus present proves default-off exact
request/reply identity and scientific-state equivalence; (ii) the opt-in spec
proves review authorization/dedup and final native state survive replay. These
four logical compatibility worlds and their two interrupted physical attempts
are developer regressions, not additional fidelity endpoints or independent
scientific samples. The original cached corpus, seed and native actors remain.
