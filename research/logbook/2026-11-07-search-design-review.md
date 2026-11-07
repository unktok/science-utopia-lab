# Search-design review, not another model campaign

User request: pause and rethink, then do that work thoroughly. Start from
research/INDEX.md, STATUS, charter, program map and existing code. Review work
uses branch track/search-design-review based on86464f6. Main and frozen60ef
experiment artifacts are initially clean. No subagents, new model inference,
generated-code execution, original-world execution, downloads, backend edits,
external services or remote writes are used.

The build-agents skill is read in full. Its established-stack exception applies:
keep the existing Python stack, not eve/provider/framework scaffolding. Inspect
existing interfaces before choosing changes. This influences the decision to
reuse blackbox ask/tell, canonical loss, native oracle, conditional estimators,
artifact reuse and cross-scoring rather than introduce another optimization
framework. Review-only tooling does not alter the native experiment runtime.

## Terminal V44 evidence

The authoritative writer receipt closes2026-11-06T18:23:20.070470Z, start
17:08:25.218649Z, exit0. Queue budget completion is not universal scientific
success:8 slots,6 complete evaluations,1 native technical failure,1 authoring
failure.7 valid finished definitions,6 physical world directories including a
partial failure,578 physical researcher responses,62 designer POSTs. Checkpoint
reuse means logical observations are not automatically independent fresh worlds.

Raw output: outputs/native-authoring-recovery-v44-a4. Original source:
60ef56ca2e32634c72817676b8bcc55bc9fcaa45. Full audit content:
18ba247752ad258b6661091c254ef7f4383ea176eee0146fdd8a82fab9ca3366.
Compact content:fd9f769cec7a368fa5eb8b2d4a682920e41213cba59663788f12468c4718aae7.

Re-execute the existing original-source auditor from that immutable worktree:

```text
scripts/analyze_native_staged_search_v15.py
  --run /Users/shiro/unktok/dev/science-utopia-lab/outputs/native-authoring-recovery-v44-a4
  --expected-source 60ef56ca2e32634c72817676b8bcc55bc9fcaa45
  --output /Users/shiro/unktok/dev/science-utopia-lab/outputs/native-search-design-review-v1-audit-replay.json
```

Use the approved main .venv/bin/python with CUDA_VISIBLE_DEVICES='',
PYTHONHASHSEED=42, HF_HUB_OFFLINE=1 and TRANSFORMERS_OFFLINE=1. Never Apple Python.
Replay75033 exits0. `cmp -s` confirms the43MB old and replayed audits are
byte-identical; both file SHA256 are
127e4a2bf4b1606846a43c2a2658d20eb39de6b464c855656954f495ae13dbc6.
The replay verifies280 raw inputs unchanged and the original runtime source
proof. It performs no model, sandbox or native-world execution.

## Review of optimization, not only final scalar values

G0's valid-review filtering does not change observed all-reject behavior.
G1 adds mean-score>8 acceptance, while exact recorded native feature means range
3 through3.6666666666666665. G2 filters already-reviewed paper features and
violates actual submitted-paper decision coverage. G3 requests a read at its
submit checkpoint; the following recovery prompt hits a host byte limit.
ThroughputG1 only changes source whitespace, G2/G3 have the same selection
source; all four make actual all-accept decisions and have loss-7.

The old auditor already supplies cross-scores. New thin offline script
scripts/review_native_search.py checks the supplied summary content/source/full
audit bindings, recomputes scores with existing evaluate_loss, retains every
failure/tie and reports original-arm versus retrospective-pool choices.
It is NOT a new raw audit, evidence bank, optimizer run, invention or held-out
result. The original protocol's independent histories are not modified.

```text
scripts/review_native_search.py
  --summary /Users/shiro/unktok/dev/science-utopia-lab/outputs/native-authoring-recovery-v44-a4-compact.json
  --expected-source 60ef56ca2e32634c72817676b8bcc55bc9fcaa45
  --expected-full-audit 18ba247752ad258b6661091c254ef7f4383ea176eee0146fdd8a82fab9ca3366
  --output research/results/native-search-design-review-v1.json
```

Existing all-accept trajectories score-11.833333333333336 for efficiency; that
arm's own best is12. The retrospective gap is23.833333333333336, not an observed
improvement by the original arm or global regret. Both objectives choose the
same pool candidate and all four exact ties are retained. No different winners
are manufactured. Historical V13 external-author improvements are recorded
separately; authorship, sources and budgets differ.

Review result content:
75b5c776d2134662cb7005f9e5970464bfe4902dd8965e0910f0f5ec241deefd.
Input compact file SHA256:
6ad2cb046bb155ffe502f52297cca9e2a72a39cd9f827d95d831c5dd374d05dc.

## Exact G3 representation-size diagnostic

Read original binding, reconstruct initial_draft, then14 completed actions with
the original source's build_prompt and transition, passing each archived prompt's
workflow phase. Require exact equality with each archived started prompt and
transition. Reconstruct step14's recovery prompt and its normal conversation,
designer_payload and wire_record, but DO NOT dispatch. Hash all30 generation
JSON files before/after and require equality.

Result:245925 internal prompt bytes versus199047 undispatched wire bytes.
The internal guard is240000. Largest internal fields include a45044-byte literal
workbench that the existing wire renderer subsequently removes,32690-byte current
system,30983-byte own-trial feedback and28251-byte parent system. This is a
host-side representation-limit stop, not a measured model context overflow.
No token-capacity or counterfactual successful-repair claim follows. Saved
diagnostic: research/results/native-search-context-size-review-v1.json.

## Deliverables and verification

- research/search-design-review.md maps all original goals, current evidence,
  reusable interfaces and the finite R0→R1→R2→R3 sequence.
- Decision0029 separates retrospective scoring, prospective common initial data
  and online cross-arm sharing. LLM editing is one proposer, not all optimization.
- STATUS records terminal evidence and no new campaign; old snapshots remain
  explicitly historical. INDEX, program-map and README point to the new review.
  The old optimization.md is explicitly historical, not an implicit-constraint
  default for new studies.
- New review tests pass16/16 in0.34s. Related review/blackbox/loss/native-cost-bank/
  expectation-estimator/adaptive-search tests pass74/74 in22.77s. Log:
  /tmp/science-utopia-search-review-core.log. These are offline software tests,
  not new model-backed validation or evidence of improved optimization.

R0 ends here. R1 repair-context work and R2 connection of existing optimization
interfaces are designed, not implemented by this review. No new long campaign
is launched as a side effect of a successful offline test. All empirical
improvement claims remain bounded by their actual original evidence.
