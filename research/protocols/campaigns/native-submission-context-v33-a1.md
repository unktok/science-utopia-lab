# Fix the native submission-context shadowing before further free search

## Actual cause and scope

Read-only actual-wire comparison of the V30 original parent and V31 a2's two
unconsumed-parameter instances finds97 requests each,94 exactly equal and three
different year2 submission payloads (zero-based indices49/50/52). The only
differences are nine automatically stamped review_time values rendered inside
ArchivedPaper reprs. Diagnostic-only substitution makes all97 payloads equal;
this is not a production normalizer or a rewrite of any saved evidence.

get_paper_submission_prompt overwrites its caller-supplied previous_papers
citation-preview argument with the researcher's private archive list in year2+.
It sorts that list in place, then a separate citation-preview block interpolates
the ArchivedPaper objects. This both loses supplied previews and unintentionally
prints full internal records, including execution-clock metadata, as citations.
The earlier original-world paired tests fixed time.time, so did not test this
independent-clock nuisance. Preserve their original scope and all actual logs.

## Minimal source fix, not arbitrary timestamp scrubbing

Use a separate locally sorted own_previous_papers list for the existing bounded
title/year/conference/status/score history summary. Preserve the caller's
previous_papers argument for its original citation-preview section. Do not sort
the tracker-owned list in place, stringify private objects as publication
previews, regex-strip authored scientific strings, overwrite any raw review
clock, couple clocks across actual worlds or copy old model responses into a
fresh run. Raw review histories/justifications/timestamps remain stored intact.

This deliberately changes the affected year2+ presentation: the unintended
duplicate private-object citation block is removed and actually supplied
publication previews are no longer discarded. It is NOT a claim that all old
prompt bytes/scientific context are unchanged or a cosmetic whitespace fix.
Existing own-paper summaries, native research/review/publication/funding
activities, model weights/personas/settings, schemas, corpus and world state
remain present. Intentionally authored timing strings and citation previews
stay literal. Do not interpret cross-source loss differences as policy effects.

SCRIPTED regressions must first reproduce the actual clock dependence and
argument/list mutation before the fix. Test single/list/forced-list submission,
preserved caller previews and scholarly timing strings, raw-state immutability,
and existing unaffected golden templates. Extend the original19-node/27-wire/
five-researcher/two-year paired native-physics/pinned-Docker regression to use
different host clocks in addition to different graph/audit identities. Compare
all85 complete scientist request payloads including seeds, while raw review
timestamps/events remain different. These are simulated-model/corpus engineering
checks, not additional actual Qwen measurements or institution inventions.

## Preserve V32 and continue only at a fresh verified source

Follow [the V32 native-production hold](native-contract-layout-v32-a2-native-stop-addendum.md).
Frozen6f1e02d/tree/tag and its already-running finite max24 controls remain
unchanged and preserve their actual status/cost, with zero V32 native worlds.
Copy-task success cannot override this separate native-renderer defect.

Inherit V32's named-port schema explanation and non-veto original-adapter consumer
notices. Keep unrestricted Python/parameters/nodes/wires/processes and all
existing acceptance decisions; no scientific policy, ready candidate, source
repair, hidden retry, fallback, novelty/quality veto or objective change is added.

After focused/source checks freeze a fresh clean V33 source/tree/tag. Only after
the V32 readiness process is authoritative terminal, run a fresh independent
max24-control actual readiness/cold replay with the same predeclared V30 own-
result request23257442607ab578c2843116dac0c3e490c042f685f2c34dcd96562ef4b9b265
and V26 provider. No old certificate/call is reused or refunded. All24 exact
targets, separate role evidence and a fresh post-readiness GET /api/ps for the
same model/digest/context40960 must pass before native production. Failed,
unknown or stale evidence stops production without replacement.

If passed, run the same two-objective/two-generation/four-attempt original-world
pilot:19 nodes/27 wires/five balanced researchers/one conference/two years/seed42,
-A and -Q+.5R, designer thinking/T.6/context40960/output8192/max8 calls per
generation, no donor history in G0 and only its own actual feedback in G1.
Preserve every null failure/partial reply/physical cost. After termination obtain
two matching unmodified original-source audits. Actual different functional
model-authored systems, multiple native measurements and own-result-informed
proposal/re-evaluation remain required; readiness/retention/inert labels/tests
alone cannot complete the unchanged original goal. Scientific improvement is
reported separately and is not guaranteed.
