# Complete author-action summaries, separate from effects and gain

[Implementation](../../scripts/reports/native_author_step_summary_v1.py) provides
two read-only analysis functions, not a new generator, optimizer or candidate gate.

- `summarize_steps(steps)` counts the complete chronological completed prefix,
  malformed/unparsed actions, attempted edits, configuration calls, successful
  literal document changes and repeated observations. Nonconsecutive reads count
  as repeats only with the same known document, address/selection/descriptor and
  literal returned value. Unknown document freshness is not unchanged freshness.
- `read_session(directory)` verifies the actual plain binding/intents, sealed
  completed receipts, original prefix/hash chains and optional terminal result.
  A started call without a committed receipt stays unknown. It is not silently
  counted as a response or synthesized on disk. Session binding is checked on
  every completed step, not just terminal links. A saved finish and a missing
  terminal file remain two distinct observations.

The functions never construct a model, execute/replay candidate code, repair,
resume, submit, resample, measure scientific loss or change what is legal.
File/hash checks do **not** replace original source-bound deterministic cold
replay, transport verification, calibrated readiness or native effect analysis.
All role/calibration/probe POST counts must still come from their own complete
cost journals:19 author steps do not mean19 total designer POSTs.

## Verified present evidence

At source457c5901,20 SCRIPTED tests pass. At79d48104,22 pass, adding unknown
freshness and resealed cross-session step cases. These are pure metadata checks,
not native/Docker/SDK integration or outer CLI proof. Both original JUnit files
are retained in [data](../data/native-author-step-summary-v1/README.md).

The current reader also runs against the two **actual completed** first free
sessions from frozen scientific705b5259. U has5 actions,3 reads of one unchanged
source and2 duplicate reads. C has14 actions,12 reads,11 in the same agenda-source
class and10 duplicate reads. Both explicitly finish without attempting edits.
Totals are19 completed steps,15 reads,12 duplicate read observations,0 edit
attempts and0 literal document changes. This agrees with the earlier literal
submission/outcome receipts. It is a two-session prefix, not all8 free proposals.

These observations distinguish unexercised design freedom from broken returned
read data or a lost successful edit on these traces. They do not establish why
the designer behaves this way, rule out all bugs/context/model effects, prove
the parent optimal, justify a compulsory-edit policy or demonstrate invention.

## Use after the current study closes

Read all8 original proposal-session directories via their exact campaign
request hashes, retaining generation/transport failures and partial histories.
Join by compound method/history/objective/generation identity, not suggestion
ID alone. Compare author actions and literal submitted graph deltas with the
already frozen all-slot original-source readout, observed native input/choice
classes, assigned losses/reference contrasts and full costs. Keep these layers
separate: edits can be inert or harmful, and an unchanged parent can be legal.
Never drop nulls, select only apparent improvements or call repeated observed
paths independent populations. A [companion post-closure exporter](native-priority-author-outcomes-v1.md)
is now implemented/software-tested; the actual all8-session analysis has not run.

[Sealed software/actual-session retention and seventh original outcome](../results/native-author-step-summary-retention-v1.json),
[first free C full-provider-request trace](../results/native-priority-sixth-own-outcome-and-read-loop-prefix-v1.json),
[current status](../STATUS.md).
