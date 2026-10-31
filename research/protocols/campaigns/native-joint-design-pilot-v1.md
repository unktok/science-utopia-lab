# Native joint source/protocol/wiring pilot v1

Status: frozen before live execution; engineering development only.

Run clean pinned source in a separate worktree. Execute two candidate systems
using `scripts/run_native_design_loop.py --proposer example --budget 2`, four
years, five researchers in independent institutions, seed 1301, local qwen3:8b,
explicit non-thinking, 768 output tokens, one worker and original SciEvo corpus.
Record actual source/model/corpus hashes and candidate lineage. No held-out
claim, no optimizer superiority or objective endorsement.

The explicit loss is negative native accepted-decision count, versioned under
`objectives/losses/native-accepted-count-engineering-v1.json`. All-accept is
legal. This exercises native design/evaluation mechanics, not epistemic quality.
Do not add fairness/promotion thresholds or reinterpret failure as a low score.

First evaluate the legacy-instance graph. The developer example then receives
its actual observation and computes threshold `clip(4 + previous_loss/10,1,7)`.
It jointly adds a Python deliberation producer, a new typed protocol and a
Python selection consumer plus their edges/schedules. Existing research,
retrieval, peer review, publication, funding and history remain native. This
is not LLM invention; the separate LLM proposer interface needs its own evidence.

Gates: both executions terminal and retained; returned loss independently
recomputed from the real native paper histories; source/protocol/wiring changes
present in the executed candidate; second suggestion bound to first observation;
pending/completed state reopens without mutation; checkpoint/replay bindings
match; no replacement numeric world. Improvement is not required to pass the
engineering gate. If a technical failure occurs, record it, retain null loss
and never substitute a hand-picked successful trajectory.

Native score-function gradients are separately QA-tested and runnable but are
not part of this two-candidate live black-box probe. Full native autograd,
endogenous recursive redesign, general scientific-activity modeling and live
game interventions remain open.
