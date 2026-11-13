# Selection-fixed evaluation of known incumbents and own submissions

The [development K/O rule](../publication/optimization-incumbent-vs-generated-output-v1.md)
must also remain visible in unused-world evaluation. The existing joint bank
already covers the selected K program: it is either one of its eight common
references or that history's original earliest-tied own selection. Additional
simulation is unnecessary. Other tied own programs are **not** thereby evaluated.

The separate [read-only module](../../scripts/reports/native_joint_incumbent_evaluation_v1.py)
does not change the joint runner, its physical jobs, original own-only choices,
losses, budgets, active studies or original audit scopes.

## Freeze before evaluating

The `freeze` CLI takes the prepared joint plan and two matching closed reports
from each of the three development studies. Reconstruct each development K/O
history with the existing strict reader. Require the exact original audit/plan
bindings, numeric reused bank and all original own-selection IDs/losses/ties.
For each of eight histories freeze two aliases:

| Readout | Selection uses | Target already in joint bank |
| --- | --- | --- |
| Known incumbent K | Lowest development loss among references and completed own proposals | Earliest tied reference, otherwise original earliest tied own selection |
| Own submission O | Original best completed own proposal | Original own-selection label, including its unavailable state |

References are eligible for K regardless of whether own proposals succeed,
fail, tie, improve or worsen the loss. This is an explicit optimization readout,
not a new merit/validity gate or a replacement of the historical own-only choice.
The aliases contain exact development values, provenance and all tied IDs.
The code reads no evaluation outcomes when constructing them. In the actual
workflow, retain this frozen file before dispatch; a manually supplied plan
alone is not independent evidence of when the file was created.

## Copy outcomes, never select again

The `report` CLI requires the frozen aliases, original matching joint report
pair and the same three matching development report pairs. Reconstruct and
compare the development-only aliases exactly, then copy the already measured
T/U scores and physical-job identities for every seed. Preserve all16 alias
labels per seed, both versions of the eight original contrasts and own-minus-K
differences. The original O contrasts must remain equal to the joint report.

An own policy can outperform the incumbent on an unused world. A frozen
incumbent's evaluation can fail while another policy completes. Neither case
permits switching targets, filling losses or selecting a different tied program.
An unavailable O remains unavailable even when K is a measured reference.
Shared aliases are not independent worlds or optimizer histories.

The freeze bundle contains `aliases.json` and its manifest. The report bundle
contains the same aliases, sealed report, score/contrast/own-minus-K CSVs and
manifest. Inputs and clean analysis source are hashed and checked unchanged.
This consumes previously closed projections, not a new raw audit or scientific
evaluation. Unit/export verification and actual scientific evaluation remain
separate; no evaluation seed is chosen and no model call is added here.

## Completed software readout verification

At clean6bf47ffd, all four actual `freeze`/`report` CLI calls exit0. The two
freeze bundles match on two files and the report bundles on six. Frozen alias
bytes remain identical across stages and O contrasts equal the original joint
contrasts. The input joint report is the prior18-world SCRIPTED native fixture;
its companion development reports are synthetic interface projections, not
recovered original author histories. No native world is rerun by this check.
The [retained software example](../data/native-joint-incumbent-preparation-v1/README.md)
and [verification](../results/native-joint-incumbent-preparation-verification-v1.json)
retain32 alias rows/32 contrasts/two missing O rows pointing into six existing
physical jobs, not extra independent worlds. The expanded47 checks pass57.26s;
seven later retention/consumer checks pass1.44s. These overlapping test scopes
are not independent scientific evidence or actual unused-world evaluation.
