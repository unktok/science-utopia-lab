# Fixed submissions compared on unused seeds

The separate evaluation finishes all30 physical worlds and both independent
audits. The selected numerical T policy ties reviewed accept-all on all three
seeds. The numerical E policy has a small mixed difference against that rule,
but loses to the one-reviewer accept-all reference on every tested seed.
No code-and-graph policy was available to evaluate. These are results for the
fixed available policies after a stopped search, not a ranking of search methods.

## Observed outcomes

T is minus accepted decision count. E is minus the sum of original mean review
scores on accepted decisions plus0.5 times actual review count. Lower is better.
Q is an endogenous review-based proxy, not independently verified quality.

| Policy | Mean A | Mean Q | Mean R | Mean T | Mean E |
| --- | ---: | ---: | ---: | ---: | ---: |
| Initial open seed | 0.667 | 2.667 | 65 | -0.667 | 29.833 |
| Legacy | 5.333 | 18.778 | 53 | -5.333 | 7.722 |
| Reviewed accept all | 10.333 | 33 | 31 | -10.333 | -17.500 |
| No review accept all | 10.333 | 0 | 0 | -10.333 | 0 |
| One reviewer accept all | 10.333 | 33.333 | 10.333 | -10.333 | -28.167 |
| Two reviewers accept all | 10.333 | 32.833 | 20.667 | -10.333 | -22.500 |
| T numerical selection | 10.333 | 33 | 31 | -10.333 | -17.500 |
| E numerical selection | 10.333 | 33.667 | 31 | -10.333 | -18.167 |
| T fixed graph selection | 0.667 | 2.667 | 65 | -0.667 | 29.833 |
| E fixed graph selection | 10.333 | 33 | 31 | -10.333 | -17.500 |
| T code and graph | unavailable | unavailable | unavailable | unavailable | unavailable |
| E code and graph | unavailable | unavailable | unavailable | unavailable | unavailable |

All accept-all references and the numerical selections have A=6,8,17 on seeds
62001,62011,62017 respectively. The E numerical selection's paired E difference
from reviewed accept-all is +0.667,-0.667,-2.000; its mean advantage is0.667
loss units, not a demonstrated stable benefit. Against one-reviewer accept-all
the same differences are +8.667,+7.000,+14.333, all worse. The E fixed-graph
selection exactly matches reviewed accept-all's A/Q/R on all three seeds.
The T fixed-graph selection matches the initial policy's measured A/Q/R;
permission to write code did not yield an effective new algorithm in that slot.

These equality statements concern observed metrics, not source equivalence or
identical complete researcher trajectories. The physical jobs remain distinct:
there are30 observed label/seed rows and30 physical worlds, not shared-world
replications. Six unavailable rows stay explicit. The unoptimized selective
cross-score in the figure is descriptive, not another optimized arm.

The [common-score figure](../../paper/figures/native-fixed-evaluation-v1/selection-fixed-common-scores.png)
shows every observed seed and both unavailable arms. The
[stopped search paths](../../paper/figures/native-fixed-evaluation-v1/stopped-search-paths.png)
retain all12 original slots, including failures and the final unsubmitted slot.
Both actual figures were visually inspected with no observed clipping/overlap.

## Interpretation and next research question

The available selected policies improve substantially over the initial weak
threshold institution but do not beat the newly authorized simple controls.
For E, the one-reviewer control has less actual review work and a slightly
different recorded Q. This is not a retrospective saving of already performed
reviews, nor evidence of better scientific truth. At equal A and R, differences
in Q alone do not identify the cause of changed review observations.

Neither more evaluation seeds nor plotting code can create a missing working
structural candidate. The separate code-tested development loop now tests a
model's ability to edit literal code after optional execution feedback; its
frozen inputs exclude these evaluation scores. It addresses feasibility, not
the entire publication importance gap. An important main study still needs a
consequential information/action/timing opportunity and strong controls with
the same authority. The current results do not justify making graph changes
mandatory, adding an undeclared objective constraint or declaring publication
readiness.

## Execution and reproducibility

The fixed evaluation runs11:25:10--16:00:06UTC,16496.75seconds (about4h35m).
Its4590 completed scientist responses report4,923,237input and426,066output
tokens. Cached input784,809 is a subset, not additional input. All30 explicit
scientist loads complete but their token usage remains unknown; designer
generation calls are0. These are provider counts and observed campaign wall
time, not project FLOPs, energy or total monetary cost.

Two original-source cold audits and two cost projections match exactly. The
first report source stops on a positional join between arm-grouped attempts
and chronological worlds. Corrected source a434cf8 joins unique arm/generation
identities;67 related checks pass and two full report exports agree. Regression
tests also expose and fix dictionary-order differences after saving/loading
JSON: report display/CSV order is explicit. No raw data, policy, score, failed
record or scientific source is repaired. The original stopped report stays
stopped. The [portable data instructions](../data/native-fixed-evaluation-v1/README.md)
separate numerical rebuilding from full raw verification. Two independent
actual retained-data rebuilds now reproduce all six outputs byte for byte;
[their verification](native-fixed-evaluation-portable-verification-v1.json)
records37 clean-source checks and no new model, world or authored-code execution.
