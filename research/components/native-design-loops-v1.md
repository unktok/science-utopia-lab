# Native code/protocol/wiring design loops v1

## What is mutable

`utopia/system/design_patch.py` applies bounded JSON-Patch-style transactions
to a parent-fingerprint-bound SystemSpec. Operations can add/remove/replace
mechanisms, their Python source or LLM instructions, arbitrary JSON rules and
memory schemas, ports/artifact types, edges, delays and schedules. A new
producer and consumer can introduce a protocol together; temporary intermediate
incompatibility is allowed, final graph/code-port conformance is not skipped.
This is an edit interface, not a finite algorithm or institution menu.

Unknown native capabilities remain runtime integration work. A valid SystemSpec
does not automatically make any proposed research/funding process executable.
The old annual frame and phase prerequisites have not vanished.

## Outer black-box loop

`NativeDesignCampaign` records baseline and adaptive Suggestion/Observation
objects; commits a pending proposal before native execution; and retains
completed observations before the next result-conditioned proposal. The factory
owns real Simulation construction, completed-response cache and completed-year
resume. A resumed pending candidate is not regenerated. One writer owns a
campaign directory. Restart validates parent lineage, patch/candidate identity,
design differences, loss hash and rederived loss from saved measurements.

`LLMNativeDesignProposer` asks a model for the same general patch and returns
actual structural errors for bounded repairs. Source/protocol/wiring can be
changed in one proposal. A structural success is not a runtime success or
scientific discovery; runtime failures and invalid proposals are retained with
no fabricated loss. Model credentials and host execution are not exposed.

`LocalQwenNativeFactory` uses the actual original corpus, original phases and
five independent balanced university researchers, not a fixture science world.
Fresh suggestions have separate outputs/caches; pending suggestions restore the
same paths. Source/model/corpus/fidelity are bound separately from the design.
Callers of the general factory interface remain responsible for honoring the
declared environment contract, not merely labelling arbitrary worlds alike.

## Native-loss gradient route

`NativeScoreFunctionSearch` binds explicitly declared continuous JSON parameter
paths to bounded logistic transforms of Gaussian variables. It estimates

`gradient_mean E_z[LossSpec(native_execution(SystemSpec(z)))]`

from actual native executions, using detached observed costs and derivatives
of proposal log probabilities. A leave-one-out baseline does not depend on its
own draw. All samples must complete before an update; dropping failed samples
would silently change the objective, so a batch with a technical failure is
recorded but not updated. No artificial failure penalty is inserted.

This is **not** autograd through native LLM/retrieval/domain transitions. It
currently changes explicitly bound continuous design parameters, not arbitrary
program text through backpropagation. Joint discrete source/graph proposals
remain on the black-box route; both cross the same native evaluator and
LossSpec. Gradient estimates can be noisy and need no finite-difference match
to a single discontinuous realized trajectory. The calculus unit test checks
the log-probability estimator; separate integration tests derive costs from
full native domain runs. General method background:
[Schulman et al., Stochastic Computation Graphs](https://arxiv.org/abs/1506.05254).

`NativeGradientCampaign` journals pending draws, each returned observation and
the update. Resume does not repeat already committed draws; pure estimator
replay validates the saved update history. This still requires the native
factory's response/year caches for an interrupted in-flight draw.

## Commands

From a clean, commit-pinned experiment worktree, with fixed PYTHONHASHSEED,
local Ollama/Docker and the original data cache:

```sh
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=1301 /path/to/venv/bin/python \
  scripts/run_native_design_loop.py --output outputs/native-design \
  --data-cache /path/to/cache --budget 2 --proposer example \
  --loss research/objectives/losses/native-accepted-count-engineering-v1.json
```

The example is developer-authored: it jointly inserts a deliberation producer,
replaces selection with an isolated consumer, and introduces their protocol/
wiring. Its threshold depends on the previous observed loss. It is deliberately
limited to one adaptive proposal. `--proposer llm` instead requests new patches
from Qwen and may fail; no claim of successful LLM discovery is implied.

For a prepared SystemSpec and JSON list of `{path,lower,upper}` bindings:

```sh
CUDA_VISIBLE_DEVICES='' PYTHONHASHSEED=1301 /path/to/venv/bin/python \
  scripts/run_native_gradient_loop.py --output outputs/native-gradient \
  --data-cache /path/to/cache --system system.json --bindings bindings.json \
  --samples 2 --batches 1 \
  --loss research/objectives/losses/native-accepted-count-engineering-v1.json
```

The count loss is a declared gameable engineering target, not scientific value.
It allows all-accept. Changing the LossSpec creates a new campaign identity.

## Replay, game and recursive improvement boundaries

`native_design_view()` exports loss/design/patch lineage and fingerprints;
`native_design_replay()` converts a matching native checkpoint into replay-view
v2. No browser-side scientific transitions are invented. The new city source
adapter, playable live installation and rendering of every new artifact/role
are not implemented by these exports.

External objective-conditioned search is not yet an endogenous science society
redesigning itself. Decision 0026 defines the proposal-port, version/migration,
branch-evaluation and recursive-designer stages still needed. There is no host
self-modification, mutable objective oracle or automatic policy deployment.
