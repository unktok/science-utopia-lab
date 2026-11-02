# Finite free-vocabulary and conditional-weight nesting v13

This is an opt-in controller over the existing original research world. It does
not alter historical campaigns, world laws, researcher weights or old evidence.
The supplied exact LossSpec is the optimization target; technical validity and
report-only measurements do not become hidden promotion constraints.

## Fixed arm lifecycle

| Stage | External author | Scheduled native slots | Update |
|---|---|---:|---|
| `initial-batch` | free G0 definition | 2 IID | exactly one conditional LOO likelihood-ratio update |
| `updated-proposal` | none | 1 fresh | forward only from exact G0 vocabulary and saved resulting weights |
| `redesign` | free G1 definition | 1 fresh | forward only; explicitly declared new initial weights |

Two arms therefore have an eight-slot maximum, not a success-conditioned retry
budget. Source/graph compilation failures consume their scheduled slots with
null loss and no worlds. Native failures remain null, never a penalty and never
dropped from the estimator. Invalid initial costs or a failed estimator leave
the exact distribution unchanged. If G0 cannot compile, the updated-proposal
slot is retained as unavailable, not replaced with a baseline experiment. The
scheduled G1 request can respond to those failures. An empty factor/coordinate
definition is legal and has no likelihood parameters to update. Retaining an
institution is legal; new names or hashes do not establish useful invention.

## Likelihood and vocabulary identity

`GeneratedMixedDesign` supplies existing arbitrary graph/source base patches,
conditional factor edit choices and bounded Gaussian-latent continuous design
coordinates. G0 uses two IID conditional draws. The estimator is

`g = ((L0-L1) grad log q(d0) + (L1-L0) grad log q(d1)) / 2`.

The leave-one-out baseline excludes each draw's own loss. Equal costs yield
zero advantages. The configured step is `weights_after = weights_before - .1g`.
This differentiates a declared conditional likelihood, not the arbitrary source
inventor, fixed LLM, native world, its discrete behavior or scientific value.
No variance reduction, useful invention, causal benefit or method superiority
follows from a working update or a new outcome.

The next singleton preserves G0's exact definition and vocabulary version,
loads its recorded updated weights and independently samples a new latent/factor
draw. Its request-derived draw namespace is distinct, including when the graph
and factor assignment are unchanged: fresh native calls cannot collide with
prior native run IDs. Its likelihood is computed under the updated weights.

G1 receives every own prior observation, the saved update and null failures.
Its parent is the earliest complete minimum-loss own observation; all exact
ties are exposed and preserved. G1 may change source, mechanisms, protocols,
ports, wires, schedules, processes, factor supports or coordinate meanings. It
starts from its complete explicit definition, without silently transporting G0
weights, gradient state or fitted controls into incompatible semantics. An
external author may explicitly re-express compatible learned weights, but the
host never guesses such a mapping. Author metadata is self-reported, not
provider-authenticated; own-history instructions are not OS-level access control.

## Durable trace and replay contract

Module: `utopia/optimization/native_nested_search.py`.
Driver: `scripts/run_native_nested_search_v13.py`.

Arm state schema `scienceutopia.native-nested-search.v13` contains `binding`,
`records` and `pending`. Each record has:

```
stage, generation, request, request_sha256, definition, version_sha256,
draw_version_sha256, generation_error, draws, observations, report,
generated, compiled
```

Requests contain the exact LossSpec, world/source/model/corpus/seed binding,
parent system, based-on observation, all incumbent tie IDs, full preceding own
records, observations, stage RNG seed and global within-arm proposal index.
Reports directly expose `weights_before`, `weights_after`, `gradient`, `status`
and `losses`. Forward-only reports always have null gradient, unchanged weights
and an explicit no-update reason. Technical-estimator failures preserve their
error and unchanged weights, not a manufactured update.

Every cold restore deterministically reconstructs requests, versions, draws,
conditional likelihoods and estimator reports. Successful observations are
bound to actual original-native checkpoint hashes, full SystemSpecs, completed
horizons, event hashes and declared source/model/corpus/seeds. The optimizer
checks receipts and measurements; independent reporting must separately derive
measurements from checkpoint domain state. After four consumed slots, further
advance is rejected.

The driver emits `scienceutopia.native-nested-search-pilot.v13`, with arms mapped
by exact LossSpec ID. It fixes five authors, two years, scientific seed 42,
four-year real corpus and fixed Qwen3:8B via the existing factory. Clean pinned
source and exclusive pilot writer/inference locks precede execution. External
ManifestInbox waits preserve exact requests, consume no native slots and never
invent institution code. Only root's frozen integrated source may launch the
actual pilot. Raw outputs and caches remain outside Git.

## Software verification scope

The unit fixtures cover two-draw analytical LOO estimation, saved-update fresh
sampling and likelihood, changed G1 coordinate meaning/reset, all ties, empty
parameter lists, invalid/null slots, failed estimators, exact external inbox
waiting, cold stops, budget exhaustion and tamper rejection. A separate test
runs four complete original six-year worlds with SCRIPTED HTTP replies and
networkless generated-code Docker execution. These are software QA, not actual
Qwen observations, scientific value or empirical invention evidence. The actual
two-year pilot, source freeze, protocol and independent audit are separate.
