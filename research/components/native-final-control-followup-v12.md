# Forward-only native evaluation of the final v11 control proposal

This implementation closes one narrowly identified missing execution: v11 saved
its final corrected-control distribution after its last native batch, so that
distribution had not itself been used for a subsequent native evaluation. This
is not a replacement for the v12 objective-conditioned free-redesign track.

## New experiment, immutable parent

`scripts/run_native_control_followup_v12.py` writes only a NEW output root with
schema `scienceutopia.native-control-followup.v12`. It does not append to the
old campaign, change its protocol, or rewrite any of its 129 raw files.

The parent is the exact completed v11 independent audit:

- Native experiment source: `acf3a2e4b995f8a04f4b0b56011a7051fe73a112`.
- Audit-file SHA256: `98bc7c3e4b2aa32fcedbe1f413c7311a2a71e5034824bb427f21eef8ea5f677d`.
- Audit-content SHA256: `0d75a366dc32b8f75dab96ca32d7daa90a91c6e98db140df28bbbc21d6547426`.
- Final latent mean: `[-0.1150163404137367]`.
- Final `review-aggregation` logits:
  `[-0.06055868973308312, 0.06055868973308312]`.

Before a new forward, the driver verifies the pinned audit bytes, repeats the
existing read-only v11 source/native/update audit in a separate clean OLD
`--parent-audit-source` worktree, and checks its complete result. The approved
Python subprocess uses `-B` (no bytecode writes), starts no model/container and
normalizes JSON object keys before exact archived-report comparison. The old
audit-source worktree must retain every original `utopia/` source byte; a new
optimizer is not imported into the old source-bound replay.
The exact original parent SystemSpec and final generated definition are taken
from that audit. Only the saved final distribution means/logits are overlaid.
The conservative v11 compatibility fingerprint must remain identical, covering
source, ports, wires, factors, coordinate identity/bounds/scales and all other
base state. Thus there is no guessed surrogate/coordinate transport.

The new factory's source commit is recorded separately; source identity with
v11 is not falsely claimed. All native forward runtime blobs must nevertheless
be byte-identical. There is exactly one explicit, source-pinned optimizer
exception: `native_adaptive_search.py` at reviewed commit `16f4d60`, SHA256
`8cd0d96f60e90b1e8d1395d641cc602e4e5040116bd5eb1900b49399e7c57b69`,
adds an opt-in singleton black-box path for the separate main v12 campaign.
That path is unused by this default two-draw, no-update followup. All other
`utopia/` blobs must match v11 and unknown optimizer modifications are rejected.
Both old/new file hashes and the exception scope are recorded explicitly.
The actual fixed model digest, corpus digest, two-year horizon,
four-year corpus window, runtime hash-seed binding and container image also must
match the parent's frozen world. Native replies are newly generated; no old
response prefix is injected.

## Exactly two fresh draws, no additional update

There are at most TWO fresh native attempts, from the final conditional design
distribution. The scientific world seed stays `42`; the explicitly new design
RNG stream is `43`. `GeneratedMixedDesign` retains its exact categorical and
Gaussian latent sampling, latent coordinates, bounded transforms, assignments,
factor traces, sampling RNG seed and conditional latent log probabilities.
The new version digest includes schema, parent audit content, final weights,
new RNG stream and full definition. Proposal indexes start at four and version
IDs differ from the four parent score draws.

The original five-author, two-year, fixed-Qwen3:8B simulation uses the same
native utility LossSpec, `L = 3.25 A - Q + 0.05 R`. `Q` still comes from the
original reviewer-record measurements, not institution-authored final scores.
No quality/fairness/promotion veto is added.

Both draws are sealed before execution, and each native observation is saved
before the next starts. A clean, source-pinned experiment worktree and exclusive
output writer lock are required. On cold resume, the plan, distribution, source,
latent draws, likelihoods and earlier native checkpoints are revalidated;
completed observations are not rerun. The unchanged native factory/checkpoint
mechanism resumes an interrupted world. Any technical failure is retained with
null loss, stops the remaining batch, and is never filtered or rerolled. All
equal outcomes and ties are retained. Parent raw/audit inventories are checked
around each new forward and at shutdown.

No `update`/`tell` is called. No new gradient, fitted surrogate or adaptive
parameter selection follows these two outcomes. This is post-update native
execution, NOT a controlled causal improvement comparison, variance-reduction
test, held-out seed replication, free-topology invention experiment or estimate
of the full expected loss. Two samples can be uninformative; improvement is not
a completion requirement.

## Run contract

From a clean, frozen source, with the approved uv-managed project Python:

```sh
env PYTHONHASHSEED=42 CUDA_VISIBLE_DEVICES='' HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  /Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python \
  scripts/run_native_control_followup_v12.py \
  --parent-run /ABS/immutable-native-open-estimators-v11-a1 \
  --parent-audit /ABS/research/results/native-open-estimators-v11-a1.json \
  --parent-audit-source /ABS/OLD-clean-v11-audit-source \
  --output /ABS/NEW-native-control-followup-v12-a1 \
  --data-cache /ABS/.cache/utopia \
  --inference-lock /ABS/native-parallel-v3-inference.lock
```

Root serializes actual inference with the other six v12 free-redesign worlds;
the combined prospective budget is eight, not ten. The implementation specialist
does not initiate real Qwen calls. New `plan.json`, `state.json` and
`evidence.json` are raw evidence, not Git-tracked research results. An independent
v12 audit must re-extract each native loss and verify source/code/wire/reply
receipts before results are exported to the English UI or manuscript.

## Software verification

`tests/optimization/test_native_control_followup_v12.py` checks deterministic
fresh-stream sampling and likelihoods, immutable batch/parent guards, source
binding, null technical failures, no reroll/no third world, output overlap and
exclusive writer rejection. Its original six-year scripted-HTTP native test
executes actual Simulation phases and isolated institutional code for two
worlds, cold-stops after the first committed draw, resumes the remaining draw,
and verifies that a completed restart performs zero additional forwards. Fake
HTTP/corpus are software QA, never actual-Qwen/scientific evidence. Actual
followup execution/results are a separate root-owned experiment and report.
