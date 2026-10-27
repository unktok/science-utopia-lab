# First result-dependent closed-loop engineering campaign

**Campaign:** `first-closed-loop-engineering`
**Revision:** `9a10029807d5`
**Protocol tag:** `protocol/first-closed-loop-engineering-v1.1`
**Outcome:** engineering loop complete; no science-policy ranking authorized

## What completed

The persistent controller proposed two independent fixed-topology `SystemSpec`
instances, ran each on seeds 503, 509, and 521, aggregated the declared
engineering `LossSpec`, and returned both observations through `tell`. It then
generated a third candidate conditional on the lower-loss initial observation,
ran the same three optimization seeds, observed the result, and stopped at the
frozen budget of three suggestions.

All nine Qwen3-8B runs completed on their first harness attempt. All nine native
integrity reports and funding-application trace summaries passed. The registry
contains no held-out seed. Restarting the controller with `status`, `init`, and
`status` left the snapshot, state, registry, loss reports, and rendered status
unchanged.

## Engineering result

| Suggestion | Phase | Design | Parent | Aggregate loss |
|---|---|---|---|---:|
| `s48505e482ecaac6c` | initial | `d0cff50cb65e7` | — | 0.673378704 |
| `s5aad19dd3da73bc8` | initial | `d818522bc230e` | — | 0.421178513 |
| `s78f27eb6410b8954` | adaptive | `d7e65ef19ae3e` | `o27437d6a43b8379b` | 0.421178513 |

Lower is better for this loss. The adaptive suggestion names
`o27437d6a43b8379b`, the lower-loss initial observation, as its explicit parent.
This is the required result-dependent transition; it is not a replay of a
precomputed third point.

The adaptive candidate tied its parent exactly on every seed-level loss input,
despite changing acceptance rate, funding-slot fraction, and resubmission cost.
The controller therefore retains the earlier initial observation as incumbent
under its first-at-minimum tie behavior. No adaptive improvement is claimed.

## What the tie teaches us

The exact tie is evidence about the engineering objective, not evidence that the
two systems are equivalent. At one-year smoke fidelity, the selected loss only
sees active-researcher fraction and review burden. Distinct system parameters
can therefore collapse to the same observed signal. This is useful for the next
research design: a production objective needs a better-justified measurement
model, and optimizer comparisons should report objective resolution and ties,
not only a winning candidate.

## Claim boundary

This campaign proves that the software can complete a commit-pinned,
restart-safe, result-dependent black-box optimization loop over executable
whole-system objects. The current adapter still exposes only eight parameters
inside a fixed legacy mechanism topology. The loss is an engineering continuity
signal, not a validated measure of truth, novelty, scientific progress, public
benefit, fairness, or national science-policy quality. Held-out seeds 523, 541,
and 547 remain untouched.

The next campaign should be preregistered only after the research objective,
held-out evaluation metrics, and expanded system design space are justified.
It should not reuse the untouched seeds for tuning.
