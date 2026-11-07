# Current research status

Updated2026-11-07. This page is a concise current-state summary.
[Purpose](../RESEARCH.md) · [Program map](program-map.md) · [Research index](INDEX.md)

## Actual experiment state

The user-authorized autonomous [submission goal](publication/submission-goal.md)
is active. S1 strong-rule controls are **closed and twice original-source audited**.
The finite8-world writer ran2026-11-07T07:49:17–08:26:40UTC (37m23.326s), PID64117,
at frozen source2aa02c3cb4610cde4797744386da67fe851383b0.
Original five-researcher/two-year world, fixed8B, existing corpus/image;
all8 complete,726 scientist responses,56 institution-code executions,
no designer calls, no failed-slot refills. See the
[prospective protocol](protocols/campaigns/native-benchmark-controls-v2-a1.md).
[Actual results and interpretation](results/native-benchmark-controls-v2-a1.md) ·
[compact audit projection](results/native-benchmark-controls-v2-a1.json).
The two full audits are byte-identical; no models/code executed during audit.
Raw heartbeat: `outputs/native-benchmark-controls-v2-a1/`; writer log:
`outputs/publication-benchmark-v2-verification/control-run.log`.
Initial software checks atc06bc45 pass21 tests with authorized local Docker;
later audit orchestration at2aa02c3 passes5 focused checks (overlapping counts).
The first restricted-shell attempt failed on Docker permission and is preserved,
not labeled a full pass. Frozen-source closure verifies265 files.

The **design-freedom V2 writer is running**: PID72837, started09:02:10UTC,
at fixedb6654adefc42223f9ecc7b4e53c043c879230f68. Plan hash
57292c4f3c743c87c1b3fe8a602ed2ed0362c1de903c2a243eb418843a5e2e25.
Run00 and run01 each pass28 fresh real designer controls and cold replay;
each has26 exact copies, which remain diagnostic. At15:01UTC all9 fresh
reference worlds are complete. Search has
consumed43/120 slots:24 complete,9 generation failures,10 execution failures.
These are all40 slots of run00 plus three run01 G0 slots, not
the full study or three environment replicates. Run01's new real-backend
calibration passes and its throughput code-and-graph G0 is being authored; selected-policy
evaluation remains0. The writer session is live and the frozen checkout is clean.

Run00's G1–G3 do not improve any arm's best-including-initial value. Uniform numeric
throughput records-7/0/-7/0; selective records8.1/2.4000000000000004/8.1/2.4000000000000004. These
lower/higher random proposals are not learning evidence. All eight uniform numeric
slots execute, while all eight LLM numeric slots fail generation. The two G2
failures reject out-of-domain finishes within16 actions; all32 actual posted
frames retain the exact declared domain, with stop completion signals. This
does not remove possible presentation/compliance confounding or demonstrate
an inherent limitation of parameter tuning.
G3 throughput tries source edits outside the numeric domain; selective proposes
thresholds1000000 (upper bound5) and bias1000 (upper bound4), and also attempts
source edits. Both exhaust16 author actions without a valid explicit finish.
These are design-compliance failures, not measured poor scientific losses.
Run01's fixed-graph T/C G0 proposals fail respectively on scalar score indexing
and an empty required decisions output. The latter emits no decision for three
real submissions; rejecting all with explicit IDs remains legal. No scientific
loss is imputed and no host repair changes either proposal.

The [chronological log](logbook/2026-11-07-submission-goal.md) retains the
G0/G1/G2 table, every earlier snapshot and source/receipt/wire/checkpoint hashes.
Read-only cases distinguish real scientist-input changes, realized equivalence,
arithmetic roundoff and distinct ABI/type failures. Object-only payload schemas
do not prove field/rank safety; see the
[readiness review](publication/research-readiness-review-v2.md). Raw floats and
exact selection rules remain unchanged. This live milestone is not a closed
original-source audit, a gain over strong controls, a feedback/method comparison
conclusion or evidence of better science.
The reproduction guide now distinguishes authored-only selection from V2's
explicitly initial-eligible pool. A later metadata-only registry availability
check has no observed remote HTTP result: restricted DNS failed, then automatic
review rejected local layer-digest egress before execution. That optional check
awaits explicit user permission; availability remains unknown, not404. No
workaround, model download/replacement or experiment change is made.
Raw: `outputs/native-design-freedom-v2-a1/`; stdout:
`outputs/publication-benchmark-v2-verification/study-run.log`.
Scientist/designer inference remains serialized; the detached experiment checkout
is not edited. The following separate main changes concern reporting/manuscript.

The design-freedom pipeline is now integrated: nested domains, in-session
validation, uniform numeric baseline, selection/evaluation and finite HTTP budgets.
Sourceea6e12f passed2693 checks/6 optional archive skips in1000.86s;
laterf18d9b5 passed134 physical/domain/legacy checks in137.32s;
finalcbf91cb passed17 study/pre-initialization checks in7.14s (overlapping counts).
The [software receipt](results/native-design-freedom-v2-verification.json) distinguishes
sources and preserved failures. Broad checks were not rerun at the final source.
Original native lifecycle with scripted HTTP/corpus now covers the new selective
loss, non42 controller seed, and evaluation seed31001 at2/4 years.
The [prospective study](protocols/campaigns/native-design-freedom-v2.md) fixes
120 proposal slots,9 fresh references and at most114 selected-policy evaluations.
Every later search run still requires its own fresh calibration; old S1/V1
certificates cannot certify it. It is not a completed scientific comparison.

The earlier finite feedback comparison V1 is **closed and original-source audited**.
It ran05:08:38–06:01:45UTC on2026-11-07 (53m06.77s), at frozen2e375c2,
with fixed Qwen3-8B researchers and the approved local35B designer.
No model experiment remains running from this campaign.

Repository entry points and the six original goals have now been reorganized,
with six exact historical snapshots. The [publication research plan](publication/plan.md)
and [comparison contract](publication/benchmark-contract-v1.md) identify the next
matched studies. The [four-study evidence projection](results/publication-evidence-inventory-v1.json)
is implemented and tested offline. It starts no model/world and establishes no
new improvement, matched-method result or submission readiness.

The [feedback comparison](protocols/campaigns/native-feedback-comparison-v1-a1.md)
completed all eight slots: four measured candidates and four runtime failures,
plus one separate completed shared baseline. All28 real local-designer
technical controls and cold replay pass;26/28 exact-copy matches remain a
diagnostic, not a dispatch veto under execution-readiness-v39. The shared
baseline and candidates retain the original researcher lifecycle. No failed
slot was refilled. [All outcomes and mechanism analysis](results/native-feedback-comparison-v1-a1.md)
and [compact source-bound JSON](results/native-feedback-comparison-v1-a1.json)
are the current evidence, not test fixtures or live partial progress.
The [software receipt](results/feedback-comparison-v1-verification.json) separates
the2619/3 broad check at2494e63 from the114 later targeted checks at2e375c2.
These are software verification, not experimental improvement or a guarantee
that all generated institutions execute. Raw local locator:
`outputs/native-feedback-comparison-v1-a1/`.

The pooled minimum for **both** losses is efficiency-control G0: A7,
Q22.333333333333336/R21, throughput loss-7 and efficiency loss-11.833333333333336.
The shared developer seed has A0/Q0/R24 and losses0/12. The candidate changes
selection to all-accept, not graph/process structure. This initial proposal is
an observed proxy improvement, not feedback-driven iterative gain, a novel
algorithm or better science. No measured G1 improvement or feedback advantage
was demonstrated. The seed is open_native_system, not the untouched original
quota institution: stronger legacy/manual baselines remain necessary.

Separate prospective fixes explain coefficient-derived directions (111 focused
checks at6424bbf) and required-output cardinality (105 atd303136), without
changing the frozen run or its failures. New generation needs fresh calibration.
See [arithmetic context](logbook/2026-11-07-affine-direction-context.md) and
[output context](logbook/2026-11-07-required-output-context.md).

The [short manuscript](../paper/submission.tex) now contains the actual all-trial
table, search paths, source/mechanism interpretation and measured costs.
This closes a small integration comparison, not the full conference study.
The updated working PDF also includes the completed S1 strong-rule comparison,
its print-sized figure, the separately labeled V2 protocol, resources and
responsible interpretation. Its latest11-page rebuild incorporates GPTSwarm,
SocialSystemArena and PolicySim, distinguishing prior graph/social-policy search
from the proposed scientific-world comparison. It also states that editor/domain
compliance can confound a pure expressivity interpretation. All11 pages were
freshly rendered at120dpi and individually visually inspected after fixing float
spacing and an appendix orphan page. No partial/future V2 outcomes are presented
as manuscript results. This remains a working draft, not submission readiness.

Read-only S1 [scientist token accounting](results/native-controls-token-costs-v1.json)
is complete: all726 responses have prompt/completion/total/cached usage, with
719002 prompt tokens (including127250 cached),68576 completion and787578 total.
Two projections are byte-identical, inputs unchanged, no additional inference.
Unknown or invalid usage remains explicit; counters are not FLOPs, GPU time,
energy, money or total-project cost.25 focused checks at1aa0bab and79 integrated
checks at7b4d573 pass in3.63s/17.36s (overlapping scopes). The updated paper's
dependency/resource-table guards pass33 checks at92686a3 in1.10s.

A separate post-dispatch [hardware observation](results/submission-hardware-observed-v2.json)
reports Apple M5 Pro,18 logical CPUs and64GiB memory, not startup/GPU-utilization
attestation. The appendix distinguishes proxy/deployment risks, sandbox limits,
release review and coding assistance from optimization constraints.

Read-only fixed-record acceptance analysis is now implemented, exhaustively
tested on small scripted cases, and applied twice to S1 with byte-identical
outputs. The [tracked result](results/native-controls-selection-relaxation-v1.json)
separates exact audited losses from independent-summation roundoff. It explains
simple loss incentives without treating a frozen-record optimum as a feasible
dynamic-policy bound, an optimizer result or a candidate filter. The focused
28-check scope at0e50262 is software QA, not additional experiment samples.

The reproduction workflow now separates tracked figure/PDF rebuilding,
original-source raw auditing and new inference. A tracked selected-package
[environment observation](results/submission-environment-observed-v2.json) is
explicitly post-dispatch, not a startup attestation or complete environment lock.
43 offline artifact/report checks at08acafc pass. The local35B construction
recipe and separate model-server environment remain unresolved for fresh-machine
reproduction; a local alias/digest alone is insufficient. No weights are shared
or downloaded, and no completed public/anonymous artifact release is claimed.

Closed-study reporting now preserves author-step errors and hashes rather than
only generic generation failure labels. Atfb5cf4c the integrated offline
report/audit-plan/artifact scopes pass58 checks in13.36s. This is not additional
model evidence. The [readiness review](publication/research-readiness-review-v2.md)
also records domain-presentation/compliance as a possible interpretive limitation;
no active prompt, search restriction or failed candidate is changed.

The all-reference evaluation figure pipeline is integrated separately. It plots
every raw seed difference, available-pair counts, means and explicit same-job
markers; missing pairs stay outside the numerical axis. Two/four-year horizons
are never pooled, and no confidence interval or method-superiority claim is
invented. At e4f9207,75 offline report/figure/artifact checks pass in14.03s.
Watermarked synthetic previews were visually inspected; there are no actual
V2 evaluation figures yet. A [selected native-backend inventory](results/submission-backend-artifacts-observed-v2.json)
adds current binary/library hashes, not startup or loaded-library attestation.

The [local/public designer provenance comparison](results/designer-local-public-provenance-v2.json)
confirms the local64k alias shares995 nonparameter descriptors (986 tensors) with
the local base, excluding `from` annotations; config/parameter metadata differ.
The current public same-name tag has a different manifest and zero shared tensor
digests. It is not an exact replacement. The specific public query for the local
base digest returned404. This does not identify a Hugging Face revision, prove
historical download origin or close fresh-machine reproduction. No model weights
are downloaded, rehashed or replaced by this metadata investigation.

While inference runs, a separate analysis feature is completed and integrated:
closed-audit projection of all120 slots, all reference-paired seed differences,
missingness/physical-sharing/horizon separation, costs and behavior receipt counts,
plus full-history print figures.46 checks at3b63ed7 and13 later checks at998f36d
pass with synthetic inputs (overlapping scopes). These are not V2 experiment
results. Synthetic figure previews are visibly watermarked, not manuscript data.

## Earlier V45 evidence (different source and initialization)

| Assigned objective | Historical starting best | Own new outcome |
| --- | ---: | --- |
| Efficiency `-Q+0.5R` | -11.833333333333336 | null: native tensor shape failure |
| Throughput `-A` | -7 | -7: two-year completion, tied |

Both definitions submitted successfully in14 author turns each. There were
two fresh physical world directories: one completed, one partial failure.
Physical costs:110 scientist responses,28 author responses and11 institution-code
execution receipts. Calibration28 and empty role loads4 are separate.

The completed throughput candidate has A7/Q22.666666666666668/R21.
Its retrospective efficiency score is-12.166666666666668, the smallest
observed value in the old+new pooled data. This candidate is eligible for
loss-only future selection; its generating-arm label is not a veto.
Cross-source retrospective ranking is not a same-source controlled comparison,
an efficiency-arm success, held-out gain or real scientific-policy benefit.

[Audited data](results/native-warmstart-v45-a1.json) ·
[Interpretation and raw locators](logbook/2026-11-07-native-warmstart-v45.md)

## Implemented versus demonstrated

- Whole-system source, nodes, wiring and processes are editable. Execution in
  the original researcher world exists; not every generated graph is valid.
- Loss-conditioned ask/tell, own-history revision and shared historical
  initialization exist. Reliable objective-specific autonomous improvement
  remains unproven.
- Conditional gradients, likelihood-ratio estimators and black-box methods
  exist. Whole-world pathwise differentiation and optimizer superiority are
  not established or prerequisites.
- The English pixel/cyberpunk UI renders canonical evidence. It is not yet a
  complete management game or scientific outcome in its own right.
- Earlier external-author V13 improvements are real recorded observations
  with separate provenance. They are not evidence that the local designer
  learned to invent institutions.

## Earlier V45 verification and limitations

Frozen experiment source:
`d49cf0bebdfa9d85eab91012118904dcff9232da`.
Pre-dispatch checks:1682 passed/3 optional skips;28 real calibration controls.
Two independent original-source audits are byte-identical. All28 actual
author replies finish normally, without observed capacity/JSON/transport failure.

The efficiency proposal changed its extractor to four columns while its tensor
consumer still declared two; the host correctly retained a null technical
failure. The separate prospective fix displays literal downstream tensor
contracts beside bounded-profile code edits, without source repair or a veto.
Source d806a430ab095d1237db41dd2dca448e95e7f5b0 passes75 focused checks.
This later source has no fresh production certificate: obtain one before any
new source-bound generation. Do not reuse the d49 certificate.

A successful trajectory does not establish universal robustness. The completed
candidate has an unexercised empty-submission branch that may violate the
native decision-ID contract. No generated source or historical failure was
rewritten by the host.

## Historical records

Full snapshots through V45 are preserved in the
[status ledger](status-history-through-v45.md). Research-wide decisions and
subsequent work belong in the [roadmap](roadmap.md) and [program map](program-map.md),
not thousands of appended live-looking snapshots here.

## Metric-conditioned study execution snapshot

Compatibility entry for older links. The original parameter-study record is in
[the historical ledger](status-history-through-v45.md#metric-conditioned-study-execution-snapshot);
it is separate from free-code/native-institution pilots.
