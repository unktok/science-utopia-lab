# Source audit supporting, but not expanding, the conditional production envelope

November14, while the separately frozen open-author study is running. Read-only
inspection; no new world, model call, loss, admission rule or active-source edit.
The inspected utopia files have no differences from scientific sourcefe4281f4.

## Why this matters for the research question

The hand control reaches20 accepted decision occurrences on development61001.
Under five serial authors, minimum duration2, horizon4, two outputs per project,
no extra producers and at most one acceptance per output, the conditional
production envelope is20. More optimization does not necessarily beat that
value. This remains a conditional argument, not a global optimality certificate
or a new rule rejecting otherwise legal generated institutions.

The declared T counts accepted review-history occurrences, not unique content,
and U uses the same accepted occurrences with a separately fixed opinion.
The actual implementation, rather than a convenient interpretation of paper
counts, must therefore be checked before drawing an upper-bound conclusion.

## Checked paths in the actual original world

| Path | Direct source evidence | Scope of inference |
| --- | --- | --- |
| Measurement | native_world._measure_domain iterates every paper's review_history and counts accept decisions | The metric is an occurrence count; do not silently replace it with distinct papers |
| Catalog assignment | validate_catalog_assignment requires an actual active idle native author, the exact displayed expertise entry, start=current year and end=current+duration-1 | This command does not allow backdating, shortening a catalog duration or replacing ongoing work |
| New submission | Simulation._process_submission_response slices to n_needed and rejects any ID already in PaperTracker; _create_submission requires the current maturity year | These ordinary submissions cannot freely duplicate an already tracked paper or ignore maturity |
| Resubmission | _resubmit_papers_batch selects papers whose current status is reject; _process_resubmission_response checks membership; _record_resubmission keeps one submitted_ids set per year | The ordinary resubmission path does not offer accepted papers as eligible resubmissions |
| Custom decision batch | NativeScienceKernel._apply_decisions checks exact current real-paper coverage and unique IDs for non-native decisions | An arbitrary institutional batch cannot simply emit the same accepted ID multiple times |
| Native selection | Conference.make_acceptance_decisions returns unless status is UNDER_REVIEW, then clears submitted_papers after making decisions | Reinvoking this selection method alone is not proof of a new accepted paper or a new publication commit |
| Publication tracking | PaperTracker.add_or_update_paper requires an empty first-submission history before its decision, while genuine resubmission decisions append history | Repeated histories require checking the actual type/state path; code assumptions cannot replace a native trace |
| Extra custom actors | native_open_domain._create_actor writes custom domain actors/state; it does not add a native author to Simulation.ecosystem | A new office actor is not automatically a new native paper producer |
| Declared workflow law | require_workflow_candidate retains exactly-once protected production/publication effects, fixes native plan/paper origins, disallows extra native.researcher.work.v15 and arbitrary native.project grants | Those are this finite study's disclosed world-law boundaries, not the full framework's expression ceiling |

## What is deliberately not concluded

This audit does not exhaustively prove every allowed composed program and
native callback preserves all premises. In particular, do not infer universal
program equivalence or a global T optimum from class names, a subset of source
checks, or one successful test. The native-only decision shortcut is different
from the custom-batch coverage check. Author-index multiplicities, collaboration,
other legitimate callback/state paths and the exact original initialization
must not be elided from a stronger theorem. Code/dependency inspection is not
a fresh counterfactual world or a demonstration of an exploitable loophole.

Keep20 labeled conditional in the paper. Do not impose a new distinct-paper
metric, novelty requirement, fairness constraint or post-hoc candidate exclusion.
For the running open study, report literal code/wiring, actual consumed effects,
both original losses, comparison against both controls and missingness. A tie
may reflect limited explored headroom, ineffective edits or insufficient search;
this source audit alone does not identify which explanation caused an outcome.
