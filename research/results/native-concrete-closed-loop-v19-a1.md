# Two objective native feedback loops complete with unchanged institutions

At frozen source `6b53841b89618bd9ce6ebed3e52b43c3b22c9fe1`, the fixed local
Qwen3-8B author completes two generations for each objective in the original
researcher world. Each G1 receives its own G0 measured loss and observation ID,
explicitly submits a candidate, and obtains another native measurement.
All four submitted systems equal their parent. The operational loop works;
useful institutional invention, objective-dependent redesign and improvement
are not demonstrated.

| Objective minimized | G0 loss | G1 loss | Calls G0 / G1 | Submitted system |
| --- | --- | --- | --- | --- |
| Accepted decisions, `-A` | -1 | -1 | 4 / 8 | Exact parent in both generations |
| Reviewed production and review cost, `-Q+0.5R` | 8 | 8 | 4 / 7 | Exact parent in both generations |

Every world measures `A=1, Q=4, R=24`. Cross-scoring each checkpoint gives -1
and 8 under the two pinned LossSpecs. Values from different objectives are not
on a common goodness scale. They are engineering proxies, not scientific value.

## Literal actions and measured feedback

Throughput G0 inspects, replaces selection source with identical text,
reinspects and explicitly finishes. G1 receives the exact G0 loss -1 and
`observation-native-adaptive-547b073d757dde84c7a331d7`. Three edits carrying an
unexpected top-level `provenance` field are rejected without changing the draft.
The model then explicitly finishes the parent, which is evaluated at -1.

Reviewed-production G0's source edit carries an unexpected top-level `rationale`
and is rejected. It explicitly finishes the unchanged parent and measures 8.
G1 receives that exact loss and
`observation-native-adaptive-e7b26e4e9b5aba3cbb086cd9`, encounters three more
rejected rationale-bearing edits, then explicitly finishes and measures 8.
The host does not strip the extra fields, repair a source, choose a candidate
or insert a baseline after failure.

There are eight attempted edits: one accepted no-op and seven rejected tool
actions. Read-only comparison of every literal edit operand, including rejected
ones, finds the exact parent value in all eight. There is no hidden changed
source in a rejected envelope. All submitted candidates have zero source,
parameter, node, edge, protocol, schedule or process changes; the original
19-node/27-wire system remains intact. This does not establish that the model
understands why retention occurred. A finish rationale asserting minimization
is not a measured comparison or an optimum proof.

The new source distinguishes concrete system effects from optional search
distributions and advertises the existing finish contract on the last call.
Every actual generation finishes before call 16, so final-call-only guidance
is not exercised by this pilot. Its equivalence is SCRIPTED-tested, not shown
to cause success. Changes in source, prompts and derived seeds preclude a
controlled causal comparison with the older failed revisions.

## Original world and resource accounting

The experiment keeps five balanced researchers, one conference, two simulated
years, development seed 42 and the real 103107-paper 2016–2019 corpus. Both
author and researchers use the pinned Qwen3-8B model; no weights are trained.
The loss definitions, initial system and runtime image are unchanged. Retention
and worse outcomes remain legal; no hidden fairness/quality/novelty gate applies.

The original writer runs 2026-11-04T06:23:30.423834Z–06:55:03.798379Z:
31m33.37s wall time, exit 0.

- Four slots and four completed original-world evaluations; no generation or
  native runtime failure, distinct from the seven rejected tool actions.
- 23 designer intents, POSTs and known replies; zero unknown interruptions.
  Designer adapter time 605.12s, including nested HTTP time 597.34s. Recorded
  prompt/output tokens are 296104/2772 across all 23 replies.
- 368 fresh scientist replies/wire requests and 1204.53s scientist adapter time.
- 32 sandboxed inherited-code executions; zero newly authored source bodies
  executed. Physical response caches and observation/checkpoint IDs are unique
  across the four runs, not copied from older baseline studies.

The separately budgeted 13 instructed interface controls pass in 230.68 adapter
seconds and cold-replay before production. Certificate content hash is
`54e7a890bcab0ab5df8392eb09d16b52b2b38f85f728f453d47b88fb434b3739`.
Those controls do not execute a scientific world or generated source. Their
costs and the parallel test runtime are not added to the writer's wall time.

## Verification and remaining boundaries

Two runs of the matching frozen read-only analyzer agree byte-for-byte. They
verify 128 unchanged raw files and 247 matching runtime/driver/helper/protocol
files, including the analyzer. Compact audit content hash:
`c475653bbad16411a26eb865bc604c331d78fa6c03d8fcbd52c278dd4de8e7f1`;
full audit content hash:
`9b23720fd39e08b33f56972dc814a660bd1e5fca8cc7876189dec78546f2e1e7`;
raw inventory digest:
`ceb3b11230973a261b0aca7515f8647284e66fa776cf9afa98df899fc4910edf`.
The [generated audit](native-concrete-closed-loop-v19-a1.json) retains exact
tool/transport, history, change, checkpoint, execution and cost bindings.

The actual source's full SCRIPTED suite passes 2559 tests with six skips in
1191.39s; overlapping focused scopes are not added. The
[completion audit](native-concrete-closed-loop-v19-verification.json) binds
requirements to evidence for both arms, not just the analyzer's any-arm flag.
V17 failures and V18 diagnostics remain unchanged and separately scoped.

The final portable publication/policy/authoring check passes26 tests in1.20s,
without new inference or native execution. A SCRIPTED projection check keeps
a worse measurement in the observed path while tracking the best separately;
this is a software policy check, not an actual worse-world V19 observation.
Final rehashing confirms the128 V19 files and160/141/146 older V17 files remain
unchanged. These focused counts overlap and are not added to the full suite.

This is a four-world, one-development-seed operational demonstration, not
reliability over arbitrary programs, held-out science, useful invention,
designer learning or method superiority. The known staged versus one-shot
omitted-logit documentation caveat remains outside the exercised paths. The
external-Codex designer condition is still unapproved and unlaunched. No
science-world scale-up, paper/PDF refresh or game change is part of this run.
