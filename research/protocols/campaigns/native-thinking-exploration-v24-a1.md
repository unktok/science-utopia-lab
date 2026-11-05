# Reasoning enabled local institution design and implementation

## Full goal and current evidence

Keep the full active goal: actual different LLM-authored executable scientific
systems, multiple original-world evaluations under the chosen loss, own measured
feedback to later proposals and another original-world measurement. Improvement
is not guaranteed. Plans, retained parents, static validity and exhausted budgets
alone do not meet this goal.

V23 a1 remains live during preparation. Its first plan correctly interprets
the loss sign, but early editor replies alternate plans and unchanged parameter
reads. Do not presume its final outcome. Two remaining engineering hypotheses
are untested: planning is the first advertised editor action, and staged
institutional design has used non-thinking temperature0.2 with2048 output tokens.
Neither is established as the sole cause of stagnation or an inherent8B limit.

## Same model and world with a different author inference workflow

Keep fixed local Qwen3-8B weights for all roles. Only the staged institutional
designer requests `think:true`, temperature0.6, top-p0.95, top-k20, min-p0 and
32768 context. Researcher inference and user-owned server configuration are
unchanged. The [official model card](https://huggingface.co/Qwen/Qwen3-8B)
describes thinking for reasoning/coding and these sampling recommendations.
[Ollama documentation](https://docs.ollama.com/capabilities/thinking) separates
`message.thinking`from final`message.content`. Documentation is not proof that
our pinned backend produces compatible final actions; verify it freshly.

Omit backend`format`up front for the staged reasoning transport. Let the native
thinking parser separate reasoning and final content without an intervening
JSON grammar. The host still requires exactly one JSON final action under the
same full schema, without fence/tag stripping, repair or error-triggered format
fallback. Bind absence of`format`in the exact wire/certificate/audit. The legacy
one-shot request retains backend JSON mode.

Preserve raw response bodies, including any separate reasoning field. Only final
content is parsed as the literal JSON action. Do not salvage a candidate from
reasoning text, strip tags, repair JSON/source or invent a thinking/final token
split. Retain the backend's reported total evaluation tokens. Truncation, empty
final content, malformed output and unknown interruption remain charged failures.

Advertise the same editor actions in implementation-first order: edit, splice,
inspect, configure, validate, finish, plan. The host accepts the unchanged full
action schema; planning/replanning, reads, exact retention and worse outcomes
remain legal. This is presentation order, not a new intervention/novelty gate.
The first call still advertises the source-free plan and the last call finish.
No source, institution, threshold, policy, wiring choice or repair is supplied.
Keep V23's exact numeric objective view, full archived LossSpecs and own feedback.

## Separate finite readiness and native pilot

No V24 model call is allowed while V23 is live. Close its authoritative writer,
inspect actual work and obtain two matching original-source/raw audits, including
explicit incomplete-budget scope if stopped under its adaptive addendum. If V23
already meets the full goal, skip this debugging pilot.

Otherwise freeze this source/protocol cleanly and require a fresh14-control
actual readiness run at the new staged settings: reasoning requested,8192
output-token cap, temperature0.6 and identical explicit sampling options.
Expected literal controls and strict equality are unchanged. Cold replay must
bind those exact request bytes/settings/model/backend/runtime. A failed, unknown,
stale or truncated result stops production with no hidden retry or fallback.
Require at least one nonempty separate`message.thinking`field across these
same controls, without an extra probe. All14 exact final actions with zero
observed reasoning fields do not establish the requested mode and must fail
readiness. This is technical mode evidence, not correctness of the reasoning
or a candidate merit rule; not every control is required to emit that field.
The one-shot legacy wire remains non-thinking0.2/2048; its certificate is distinct.

Only on complete readiness authorize four native slots, two generations each
for the unchanged full `-A` and `-Q+0.5R` LossSpecs. Each generation gets eight
total author calls INCLUDING its planner,8192 output tokens per call, at most
32 author POSTs total. More reasoning/output capacity and fewer calls are a
separately declared engineering budget, not an equal-budget comparison with
prior revisions. No isolated probe, hidden native evaluation or replacement
candidate is permitted. The existing300-second HTTP timeout remains; a timed-out
reply is not assumed stopped remotely or refunded.

Keep five original balanced researchers, one conference, two simulated years,
development seed42, real103107-paper2016–2019 corpus, pinned sandbox image and
original19-node/27-wire parent. No paid/external provider, model training,
scientific-world simplification, scale-up or new merit constraint is introduced.
Each arm sees only its own fresh results. Prior failures/costs remain separate.

Keep exact UTF-8 wires, source/model/backend/image binding, model-authored plans
and literal edits, actual native code/effects, own-result identities, writer
launch/exit and physical work. After termination run two matching frozen-source
read-only audits. Report every retention, invalid action, null, unused slot and
worse loss. If different executable institutions and the measured feedback
search remain unshown, keep the full goal active and investigate the next cause
under a separate prospective revision; do not redefine completion around this
interface change or its tests.
