# Fresh full-native-cost REINFORCE pilot v5

Completed 2026-11-01. [Preregistered protocol](../protocols/campaigns/fresh-native-policy-gradient-v5.md),
[independently audited result](fresh-native-policy-gradient-v5.json).

## What now ran

Two complete original researcher worlds were freshly executed from clean pinned
`d6e4ef9836cea21a5fc059d2e1998cc08f8b9687`, with fixed Qwen3:8b, five
researchers, two years/world, native seed1301 and a four-year cached corpus.
No historical world costs were training observations. All inference acquired
the same shared HTTP lock as the parallel joint-institution experiment.

The categorical actions were two preexisting complete SystemSpecs: the exact
v3 baseline and its final Qwen-authored selection-source revision. Preregistered
search seed42 happened to draw **[1,1]**. This was recorded durably before native
inference; neither draw was replaced to obtain a balanced comparison. Each
action executed in a separate directory with a fresh response journal.

| Quantity | Observed result |
| --- | --- |
| Fresh physical worlds | 2 |
| Actual responses | 114, 57/world |
| Native accepted decisions | 3/world |
| Native review records | 9/world |
| Negative-acceptance losses | [-3,-3] |
| Initial logits | [0,0] |
| Autograd score gradient | [1.5,-1.5] |
| Updated logits, learning rate0.1 | [-0.15,+0.15] |
| Selection probabilities | [0.5,0.5] -> [0.42555748,0.57444252] |
| Prepare-to-completed-state interval | 654 seconds, including parallel queue wait |

The optimizer differentiates exact categorical log probabilities. With fixed
independent baseline0 its sampled estimator is

`gradient[j] = mean(loss_i * (1[action_i=j] - probability[j]))`.

An independent analytic calculation reproduces Torch autograd and the update
to1e-14. Complete native-world costs include subsequent actual LLM responses;
they are detached inputs to the score estimator, not a fitted numeric world.

## What the audit checks

The read-only audit reopens the durable campaign and replays its update. It
independently re-extracts all six native domain measurements and LossSpec from
portable checkpoints; validates complete native event streams and exact
generated source/image receipts for both years; checks response-journal hashes,
bindings and counts; and verifies the closed-form score/update. All25 raw
files remain byte-identical before/after audit. The experiment worktree remains
clean; there were no audit model calls or reruns. Checkpoint, response journal,
campaign, source/model/corpus/design and transfer hashes are in the JSON result.

Runner preparation and audit helper:
`scripts/run_live_native_policy_v5.py`. The actual native forward and backward
use the existing `scripts/run_native_discrete_policy.py`,
`NativeGradientCampaign` and `NativeDiscretePolicySearch` interfaces.
The existing discrete-policy tests plus three new preparation/measurement/RNG
tests pass: **13 passed** in63.62seconds under concurrent project QA.

## Interpretation and remaining gap

This closes one implementation-to-live-evidence gap: a fresh native execution
can feed exact policy-log-probability autograd and a durable probability update,
rather than only fitting probabilities to an archived cost bank.

It **does not establish optimization benefit**. Both sampled actions are1, so
no fresh contrasting baseline was executed. A nonzero fixed-baseline score
estimate can arise from sampled-action imbalance even if all possible costs
were equal. Therefore gradient magnitude and the probability increase alone
are not evidence of useful comparative information. These two physical worlds
also share one scientific seed; they are not independent held-out replicates.

The finite action list is supplied, not invented by this optimizer. Source,
topology and researcher weights did not change; no new best, convergence,
scientific-quality improvement or whole-world pathwise derivative is claimed.
The objective is the deliberately gameable negative acceptance count with no
hidden quality/fairness veto. Open code/wiring invention is the parallel main
track, not an achievement to attribute to this distribution-gradient pilot.
