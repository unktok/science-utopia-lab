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
select the capability in SystemSpec. The standard production registry installs
the trusted handler without a caller-only registry extension; registration
without the opt-in spec changes nothing.

The amended fidelity budget is seven **fresh** six-year scripted worlds with
the same predeclared controls/temperature selection above, in addition to the
one failed partial attempt. No result from the failed pin is silently relabelled
as this extension. Separately, two compatibility comparisons each use one
continuous six-year reference and one interrupted/cold-resumed society:
(i) at `01992cd`, baseline spec with optional handlers absent versus present
proved default-off exact request/reply identity and scientific-state equivalence;
after builtin registration, the same comparison proves extension idempotence,
not handler absence. Separately, the original `test_original_world_is_an_exact_instance`
compares the original Simulation coordinator (no native registry) against the
production native kernel and checks all request payloads/scientific state exactly;
(ii) the opt-in spec
proves review authorization/dedup and final native state survive replay. These
four logical compatibility worlds and their two interrupted physical attempts
are developer regressions, not additional fidelity endpoints or independent
scientific samples. The original cached corpus, seed and native actors remain.

## Second prospective amendment: production registry and scalar handoff

At clean source `01992cd`, all five planned calibration/unused native worlds
completed. Both unused endpoint checks, the finite-path native comparison and
the strict improvement over the frozen-response predictor passed before a
post-processing type error interrupted the batch: the quadrature accumulator
returned `numpy.float64`, correctly rejected by the strict native coordinate
API. The projected candidate and outside-support worlds were never started;
their native costs are unknown, not penalties. All five completed worlds remain
in `outputs/response-fidelity-v8-qa2/test_seven_original_native_wor0`, not in a
temporary retention directory. That batch is incomplete, not a full QA pass.

Before any rerun, normalize the public finite-path scalar to an ordinary Python
float and install the already-reviewed trusted ingress in the standard native
kernel registry. The latter closes a real integration gap: arbitrary authored
SystemSpecs and cold workers must not require a special test-only host callback
to use this declared capability. It does not change legacy implementations or
default prompt bytes. The next clean pin reruns all seven scripted fidelity
worlds with unchanged controls, loss, temperatures and selection rule, now
without any registry extension argument. This is an additional seven-world
developer regression, not selective resampling or actual-Qwen evidence. The
previous five completed worlds and first partial failure remain separately
accounted. The new command captures a transcript and completed endpoint receipt
under a new explicit output base, never overwriting either previous batch.

## Independent receipt review and no-forward analysis amendment

The seven-world `bfe83c0` batch passed (64.12s), with all raw/checkpoint/operator
files retained. Subsequent independent review found ordinary provenance gaps:
the initial raw numeric adapter checked only part of the SQL binding, could
mistake another task's `overall_score` for a review, did not compare the complete
parse/projection contract across fits, and did not exclude extra unused evidence
keys. These are implementation defects, not research limitations. The hardening
binds exact checkpoint bytes, standard sibling SQL/wire paths, full checkpoint
binding and completed row count; it verifies every wire/reply byte hash and
proves the original phase3 cache identity, derived request seed, and PaperReview
request schema before attributing numeric replies. All calibration evidence keys
must equal exactly the calibration checkpoint hashes. Mechanism/input/columns/
integer parser/domain and indices must remain identical across all fit points.
Invalid tolerances are rejected, and a matching finite delta is separately
labelled from absolute endpoint fidelity (a constant-offset model cannot pass).

No native worlds are rerun for these receipt fixes. Read-only analysis preserves
the original native source pin and saved operator file/content/module hashes,
checks the historically recorded three calibration SQL/wire hashes, refits the
same native endpoints under an explicitly labelled stronger representation, and
saves/reloads the new operator outside old raw. The old native checkpoint format
stores cache count, not a SQL-file SHA: this distinction is retained. For the
four unused/proposed/outside worlds the evidence is actual checkpoint/full
binding/count/task proof plus current immutable raw snapshot, not an invented
historical checkpoint-stored SQL-file hash. Full-directory before/after hashes
cover read-only extraction and durable semantic reload. New forward/model calls
are zero. This amendment never silently relabels the old representation source.

For future runs, `make_response_completion_receipt(endpoint, response_cache,
wire, run_manifest_sha256=...)` lets the existing run owner capture the actual
`CompletedResponseCache.committed_prefix_identity()` together with checkpoint,
SQL/wire hashes and manifest reference at its completion hook. It returns data
without writing or invoking models. `raw_review_projection(...,
completion_receipt=...)` requires exact receipt/prefix/hash agreement when such
a receipt is supplied. Neither API authenticates caller identity or wall-clock
timing: the status explicitly says caller-supplied completion assertion. Existing
v8 endpoints have **no** such completion receipt; the auditor does not call this
hook retrospectively or promote posthoc checksums into historical run seals.

## Scripted implementation result (native source bfe83c0)

All seven original six-year worlds completed, each with four original fixture
researchers and234 fresh scripted researcher/model replies. Production registry
dispatch needs no special callback. Calibration controls `[-.25,0,.25]` produced
native losses `[-72,-96,-96]`; calibration-only RMSE chose temperature0.01 from
the four predeclared candidates. The two unused controls `[-.20,.10]` produced
`[-72,-96]`. Their true finite loss difference is-24. Frozen-response autograd
predicts0 (error24); the fitted response-aware path integral predicts
-23.999976380018477 (error0.0000236199815). Absolute unused-endpoint checks also
pass, and the decomposition assigns the-24 difference to actual response drift.
This is a finite interval check of a developer-scripted response rule, **not** a
proof of native pointwise differentiability or of fidelity to Qwen.

The point gradient at control0 is approximately-3.21e-8, distinct from the finite
path average approximately-80. A gradient-integral-guided projected control
0.1599998425334565 reevaluates to native loss-96: it ties the center, not an
improvement over it. The extra outside-support world at0.6 has native loss-120,
but the representation correctly refuses extrapolation and reports predicted
loss/gradient as null. This favorable outside observation does not expand
calibration support after looking at it. Conditional multi-node/recurrent
backward, native hard execution, original int parsing, semantic reload and
tamper rejection were exercised. No full-native autograd/LLM Jacobian claim is
made. The incomplete source84701f3 partial attempt and source01992cd five-world
batch remain separately accounted, rather than omitted from implementation
history or treated as independent scientific repetitions.
