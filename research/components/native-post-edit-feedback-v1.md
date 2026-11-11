# Code execution feedback during institution design

The optional editor adapter tests literal model-authored code after an edit and
returns the result before the next designer call. This closes the development
gap between seeing an interface description and trying code against actual
recorded researcher-world inputs. Native losses still require full worlds.

## Execution and design freedom

`NativePostEditFeedback` declares its complete contract in the optimization
request before calibration or generation. It uses the source-bound developer
[fixture bank](../data/native-component-fixtures-v1/README.md): the open-seed
reference at seed61001, years1–4, separately for `world.selection` and
`native-feature-extractor`. Other reference fixtures remain in the retained
bank but are not dispatched by this adapter. These inputs are not independent
worlds or new trajectories under the candidate policy.

The existing literal `edit`, `write_file`, `edit_fields` and `splice` actions
remain unchanged. After a changed eligible artifact, the host runs the fixed
four-context suite through the existing pinned no-network Docker executor,
with15 seconds per call. At most eight probe attempts are available per session;
the suite is skipped if its complete budget is unavailable. Later edits remain
literal and untested. New nodes and interfaces, incomplete intermediate
artifacts and ambiguous duplicate nodes are reported as untested, not forbidden.

Errors do not undo edits, veto explicit finish, require baseline outputs, add
novelty requirements or change the optimization loss. Any repair must be another
literal model-authored action. Passing a reference input is not proof of full
world validity, especially after changing upstream interfaces or state flow.

## Durable feedback and replay

The component lab records exact code and input before execution and retains
full results or errors. The completed editor step archives those exact records.
The active prompt contains compact status, result/error hashes, a marked error
excerpt of at most1024 characters, and a pointer to the exact step archive.
Large output bodies are not silently replaced in the archive or repeated in
every prompt. An unresolved probe stops subsequent model calls; it is not a
recoverable semantic error or evidence that a remote container was cancelled.

Cold replay executes neither model nor code. It verifies the frozen bank,
source, image, budget, literal edit, ordered suite, exact terminal records,
saved next prompt and final definition. The bounded worker also rejects
unaccounted JSON journals. A fresh execution-readiness certificate must declare
the identical contract before model construction; a legacy certificate cannot
silently authorize the new mode.

## Verification and remaining experiment

Scripted checks exercise failure feedback followed by an explicitly authored
repair, finish with still-failing code, budget exhaustion, malformed intermediate
graphs, pending execution, archive tampering, large Unicode outputs and the real
bounded conversation shape. They also check that diagnostic provenance is not
inserted into the sampled scientific `SystemSpec`. This is not a new full
scientist-payload experiment or evidence of successful real-model self-debugging.

The bounded conversation test caught the feedback note displacing the final
action-phase marker; moving the note before that marker restores the existing
decoder contract. The failed test receipt remains retained. The live30-world
fixed-candidate evaluation stays unchanged at sourcef1f8ddf. Actual local35B
readiness and a finite self-debugging assay must run at the new clean source,
after the active scientist run releases local inference resources.

[Clean-source regression](../results/native-post-edit-feedback-verification-v1.json)
at56e2331 passes195/195 checks in199.90 seconds, including original native
Simulation with scripted researcher HTTP/corpus and actual Docker, full
scientist-payload clock/identity guards, old editor/readiness and new feedback
paths. The first run's178 pass/17 Docker-permission failures are retained; the
second run changes access permission, not source or tests. These are software
checks, not195 scientific observations.
