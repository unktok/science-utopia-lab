# Automatic corrected-study data exports after original closure

The [continuation](../../scripts/finish_native_corrected_choice_data_v1.py)
waits for the original normal paired readouts, then runs either
[complete loss-path data](../../scripts/reports/native_corrected_choice_figures_v1.py)
or [signed-content data](../../scripts/reports/native_corrected_choice_content_v1.py)
twice. Each output must match its independent counterpart exactly. The former
retains all six four-step paths and both frozen endpoint scopes; the latter
retains all27 reference/attempt rows, including every unavailable outcome.
No null becomes zero utility and no program is reselected.

Output and actual child paths must be fresh/external before source reads or
waiting. Reader, scientific and preceding-reader checkouts must be clean,
commit-pinned and unchanged; the exact original plan/readout header hashes
and preceding closure paths are checked. A stopped upstream stage, timeout,
changed source/selection, nonzero child, partial/mismatching files or unexpected
render output stops only this continuation. It never restarts science or retries
a failed export. Waiting is finite (24hours), each export at most1800seconds.

These processes explicitly do not request rendering. They create no new model
calls, generated-source executions, native worlds, proposals, repaired code or
losses. Successful data export would not establish a new figure/PDF visual
review, unused-condition evaluation or publication readiness.

## Actual dispatch and limits

At cleanfb87f6af,91 overlapping SCRIPTED continuation/guard/child/shape and
existing pure trajectory/content checks pass in5.82seconds. The
[JUnit](../data/corrected-choice-data-continuations-v1/pytest.xml) is retained
after the original test process exits, not91 scientific experiments.

Two original processes start from a separate cleanfb87f6af worktree:
loss-paths69103/PID36585 and signed-content40520/PID36607. Both have emitted
their waiting message and have been observed live. Their exact sealed
[loss-paths header](../data/corrected-choice-data-continuations-v1/loss-paths-started.json)
and [content header](../data/corrected-choice-data-continuations-v1/signed-content-started.json)
are retained with a [dispatch receipt](../results/native-corrected-choice-data-continuations-v1.json).
This records a verified wait, not completed exports; check actual handles and
external `ended.json` files before updating that status.

The original scientific writer/supervisor and five earlier paired analysis
processes are unchanged. The new readers wait on their original source57b35144
readout chain. Main/feature development cannot change the detached reader HEAD.
After normal exports, inspect actual trajectories/content/effects/costs before
choosing further research. Do not automatically scale a flat search.
