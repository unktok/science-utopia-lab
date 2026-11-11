# Fixed-content measurement feasibility and retrospective readout

## Question and scope

Determine whether the existing policy-blind instrument can actually rate the
entire previously staged accepted-content set, and what variation that fixed
opinion has before choosing another prospective optimization objective. This
is a retrospective development readout, not another optimization experiment,
an independent quality oracle or a contribution sufficient for milestone R2.

The original62388a7 closed data contain44 complete native worlds, five excluded
partial worlds,263 accepted decisions and76 unique exact title/abstract/topics
records. The already retained staging file binds its original-source checkpoint
readout to the existing full audit. Its file hash is
`498e84d713ab9ba4e23636a98618d58e9e97ab8741c6350c0f0e44f590bca419`.
No new world or candidate is generated. No rejected content is silently added,
and a comparison of these accepted sets does not identify rejected-paper quality.

## Instrument and finite budget

Use the existing fixed rubric and the same local Qwen3-8B digest as the native
researchers, but a separate blind request. Supply only full title, abstract and
topics, with no paper ID, author, policy, acceptance label, original review or
search score. Do not truncate inputs. Retain every raw UTF8 request, raw HTTP
response, literal score/rationale, status, time and known/unknown token count.

There are exactly76 content-hash-ordered items and three deterministic critic
seeds each: at most228 physical POSTs, with no refill, semantic retry, source
repair, score salvage or missing-score imputation. The instrument contract
fixes40960 context,512 output tokens,temperature0.6,connect10/read120 seconds
and the existing1–5 rubric. Equal content/rubric/model/critic reuses one physical
response across decision occurrences; three seeds of one model are not three
independent scientific judges. Centered utility remains the already documented
`score - 3`, not a threshold chosen after seeing ratings.

The first three items in hash order, with their complete three-critic panels,
are a finite real-backend interface check (at most9 POSTs). All must have literal
valid final ratings before dispatching the remaining items. Any1–5 value passes
this technical check; no desired rating or separation is required. Their ratings
remain part of the76-content readout without re-dispatch. This is not a new
source-repair or scientific merit gate on an institutional candidate.

Wait for the current93076b4 experiment, its independent08f671b audit/cost chain
and the separately frozen8bb712f report chain to close normally. The observer
uses the same original inference lock and a new clean commit-pinned worktree;
it cannot overlap the current native writer, restart a stopped experiment or
change any current objective, candidate or selection. Unknown inference
completion stops the entire observer run before the next POST. Known invalid
answers remain missing; a failed initial interface check stops the later batch.

## Analysis and claim boundary

Retain all76 contents and all228 potential critic positions, including failures.
Report literal rating distribution, complete-panel availability, physical cost,
content-level disagreement and, where all required content ratings are present,
the corresponding accepted-decision sums and centered utility by original world.
Do not zero-fill an unavailable world sum or count reused content as new ratings.
Keep44 completed native worlds distinct from76 contents and263 decisions.

The readout neither reselects historical policies nor enters the live T/E
designer feedback. It is not held-out generalization, optimizer replication,
proof of reward hacking, improvement in scientific truth, or a publication-ready
main result. If ratings have no useful variation, record that rather than
filtering content or changing the rubric to manufacture separation. A later
objective-conditioned search needs its own explicit loss, controls, budgets and
evaluation split; this protocol authorizes none implicitly.
