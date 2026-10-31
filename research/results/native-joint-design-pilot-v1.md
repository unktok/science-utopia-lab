# Native joint design pilot v1 — executable loop, no improvement

Status: complete engineering development probe, **not** a policy improvement.
Protocol: [frozen pilot](../protocols/campaigns/native-joint-design-pilot-v1.md).
Machine-readable evidence: [result JSON](native-joint-design-pilot-v1.json).

## What actually ran

Clean source `7c91af2e82fedd8ac449457ba5e2d0aed1c6947c`, local Qwen3:8b
digest `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41`,
one worker, explicit non-thinking, 768 output tokens, seed 1301, five balanced
university researchers in five institutions and four native years per candidate.
The original SciEvo corpus/retrieval was used, not QA fixture papers or numeric
replacement dynamics. Ordered-document SHA-256:
`ee4ca9325e5a61a61edc052346f24e94071b631c622193562308ebd054b28fb2`.
Source/model/corpus identities are bound in both checkpoints and reply journals.

First the original-world graph ran. After its actual observed loss, the
developer-authored proposer computed threshold `4 + (-4)/10 = 3.6` and emitted
one joint transaction:

- add `deliberation-assembly`, a Python implementation consuming actual native
  submissions and review scores;
- introduce the `native-deliberation` artifact protocol, producer/consumer
  ports, and two new edges;
- replace native `world.selection` with an isolated Python consumer of that
  protocol; retain native research, retrieval, review, publication and funding;
- schedule the producer at phase 125 before selection at phase 140.

This is not just assigning another name to the existing selection function.
The executed source/image receipts identify both implementations: each ran four
times in the candidate world. The new protocol is consumed to form decisions
for real submitted paper IDs and those decisions enter native publication.
The second suggestion is bound to the first actual observation. This proposer
was written by us, **not invented by Qwen**; Qwen supplied native researcher
decisions/reviews/applications. The separate LLM source/graph proposer was not
exercised by this pilot.

## Observed result

Declared loss is **negative accepted-decision count**, a deliberately gameable
engineering target. Lower is better; all-accept is legal. This is not scientific
quality, and no fairness/promotion veto was introduced.

| Diagnostic | Original graph | Joint source/protocol/wiring candidate |
|---|---:|---:|
| loss | -4 | -2 |
| accepted decision rounds | 4 | 2 |
| rejected decision rounds | 8 | 14 |
| review records | 36 | 48 |
| distinct paper IDs | 8 | 8 |
| final active authors | 5 | 5 |
| final author resources | 720 | 720 |
| completed model responses | 145 | 157 |
| model retries / failures | 0 / 0 | 0 / 0 |

The candidate is worse on the declared loss, so the incumbent remains the
original graph. We did not change the threshold after seeing this result,
switch the objective, add a hidden veto, or substitute a successful trajectory.
Counts include decision rounds/resubmissions, not necessarily unique accepted
papers. One development seed and one adaptive proposal establish no stable
ranking, optimizer superiority or science-policy conclusion.

The native design loop took **1,077.93 seconds (17.97 minutes)** after factory
preflight. Across both runs there were 302 completed model responses, 280,449
prompt tokens and 26,702 completion tokens. Model-call elapsed time summed to
1,035.92 seconds; these settings are not a speedup estimate for older campaigns.

## Independent read-only verification

`scripts/audit_native_design_loop.py` independently:

1. reopens the campaign and validates patch/candidate/parent/observation lineage;
2. restores each completed native kernel and matches its design and event hash;
3. rederives all six native measurements from saved domain histories/agents/
   events, then recomputes the caller's loss and matches the recorded result;
4. matches executed source/image receipts to the proposed code artifacts;
5. matches source/model/corpus/seed identities across checkpoint and response
   journal, verifies every saved response hash and completed-response count;
6. converts both checkpoints to canonical replay, projects years 1–4, and
   validates native replay-view exports with canonical/web hashes;
7. confirms that the campaign state hash did not change during the audit.

Checkpoint, response-cache and event hashes are in the compact JSON. The audit
verifies journal integrity, **not an independent full HTTP wire trace**; this
factory did not save the earlier integration probe's separate wire log. Native
event counts are 52 and 56; canonical event counts are 123 and 147. Replay data
is presentation-pending, not a released city source or a playable live change.

Reproduce the audit without model calls:

```sh
.venv/bin/python scripts/audit_native_design_loop.py \
  --run /Users/shiro/unktok/dev/science-utopia-lab-experiments/native-joint-design-v1/outputs/native-joint-design-v1/run \
  --loss research/objectives/losses/native-accepted-count-engineering-v1.json
```

Raw outputs/caches remain ignored and retained in that clean experiment
worktree. The result's execution source remains `7c91af2`; later development
adds an endogenous proposal bridge and a replay metadata correction. Those
later features pass deterministic QA but were not retrospectively part of this
live run. Focused regression including the bridge: 634 passed, three skipped.

## What this does and does not complete

It completes one real native cycle of **execute → observe declared loss → edit
source/protocol/wiring → execute → retain the better observed incumbent**.
It does not complete successful LLM institution invention, full native-world
autograd, continuous same-society migration, new experimental science activity,
live player intervention or recursive improvement of the designer. See the
[original-goal capability/gap map](../milestones/2026-10-31-native-design-breadth.md).
