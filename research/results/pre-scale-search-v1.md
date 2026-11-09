# Closed objective-conditioned native search

November 9, 2026. This closes the pre-scale T/E pilot, not the earlier V2 study
or the broader scientific claims. [Protocol](../protocols/campaigns/pre-scale-search-v1.md),
[complete retained data and rebuilding](../data/pre-scale-search-v1/README.md),
[closure receipt](pre-scale-search-closed-verification-v1.json).

## What ran

Five fixed Qwen3-8B researchers, four native years, the approved local 35B
designer. Loss is fixed per arm: T=−A or E=−Q+0.5R; C=4A−Q+0.1R is diagnostic.
No fairness/merit gate is added. Numerical, generated fixed-graph source,
generated source/graph and uniform proposals each consume two slots per loss
on seed41001. Six fresh references precede proposals. Selection includes the
initial, retains exact ties and uses the earliest eligible row; it freezes
before unused-seed evaluation. Production/calendar/accounting are fixed for
this pilot, not the global representational ceiling.

All16 proposals are submitted:11 complete, five runtime failures. There is no
generation failure, host source repair, refill or imputed failed loss. Selection
freezes07:47:45UTC; evaluation starts07:47:57 and closes11:29:22. All27 physical
evaluations complete across three seeds51001/51011/51017, representing36
logical rows. Two full audits finish11:35:12 and match complete bytes.

| Assigned loss / method | G0 | G1 | Fixed selection |
| --- | ---: | ---: | --- |
| T numerical | −14 | −14 | G0, earliest tie |
| T code / fixed graph | −14 | unavailable | G0 |
| T code and graph | unavailable | unavailable | initial |
| T uniform | 0 | −2 | G1 |
| E numerical | 29.3333 | −22.6667 | G1 |
| E code / fixed graph | unavailable | unavailable | initial |
| E code and graph | 27 | 43.5 | G0 |
| E uniform | 43.5 | 34.6667 | G1 |

Initial losses: T0/E43.5. These are best-loss selections, not novelty screening.
All16 original rows, all references and all96 paired reference comparisons
remain in the report, rather than only the best-looking candidate.

## What changes and what does not

E/numerical's actual G1 request includes G0's observed29.3333 loss. It changes
router threshold1→0, leaving five other coordinates fixed. Native A/Q/R change
from2/6.6667/72 to14/43.6667/42, producing−22.6667. This is an executed
feedback-history improvement on development, not evidence that feedback is
superior to other methods or that the author's rationale is causally correct.

Completed generated code includes always-accept, always-reject with final
score0, and average-review-score thresholding. The third also uses values
outside the numerical box, as allowed for source design. Eight submissions
change source; all16 retain21 mechanisms,29 connections and their schedules.
Thus this pilot exercises algorithm changes but does not demonstrate new
topology, even in the arm permitting it. Comments claiming rejection avoids
already-completed reviewing are not accepted as mechanism explanations.

The five failures are an unwrapped world payload, missing conference/score
decision fields, `score` instead of `final_score`, a float treated as a sequence,
and incomplete paper identity coverage. They remain failed records, not numeric
penalties or retroactively repaired successes. Later non-veto envelope advice
is separate code and was not backported into this experiment.

## Selection-fixed evaluation

Means below cover three seeds each; every score is available3/3. A/Q/R and
individual seeds are retained in the report/CSV and the manuscript table.

| Label | Mean T | Mean E | Mean C |
| --- | ---: | ---: | ---: |
| Ref open seed | 0 | 33.500 | 6.700 |
| Ref reviewed accept-all | −10.667 | −16.889 | 12.978 |
| Ref no-review accept-all | −10.667 | 0 | 42.667 |
| Ref no-review reject-all | 0 | 0 | 0 |
| T numerical | −10.667 | −16.889 | 12.978 |
| T code / fixed graph | −10.667 | −16.889 | 12.978 |
| T code and graph | 0 | 33.500 | 6.700 |
| T uniform | −1.667 | 24.389 | 6.656 |
| E numerical | −10.667 | −17.333 | 12.533 |
| E code / fixed graph | 0 | 33.500 | 6.700 |
| E code and graph | 0 | 17.500 | 3.500 |
| E uniform | −1.667 | 24.389 | 6.656 |

E/numerical versus reviewed accept-all has seed-paired E differences
−1,−2/3,+1/3, mean−4/9. This is not reliable superiority. Their A and R match;
the difference is in endogenous peer-score sums, not verified scientific
quality or isolated information causality. T/numerical, T/fixed code and that
reference have equal observed vectors but distinct policies and separate jobs.
The selected uniform labels do share physical jobs; open seed shares with
selected E/fixed code and T/code-and-graph. Shared labels are not replication.
Q0 without review is a metric convention, not zero true quality. C was not
optimized here; reference order under C is diagnostic, not a C search result.

## Costs and evidence boundaries

49 physical worlds =6 references+16 proposals+27 evaluation jobs, with44 normal
worlds and five partial failures. Add the distinct12-world information study
for61 actual worlds within the70-world pre-scale ceiling, not70 actual trials.
Scientist usage:8025 completed replies,8,453,441 input/723,376 output tokens;
1,416,327 cached prompt tokens are a subset. All failed-world replies count.
Six numeric proposal calls record25,651 input/8461 output;104 staged proposal
calls record2,076,602 input/39,372 output. Readiness is separate:3 numerical
calls and28 editor controls. Numeric caller time201.790s and editor transport
time1533.432s are components, not total project compute. Search→evaluation
takes about7h18m on this local binding; total development/indexing/audit work,
FLOPs, energy, GPU speedups and money are not inferred from token counts.

The report and both PNG/SVG figures rebuild byte-identically twice, including
from retained paths. Costs and all eight Foundry envelopes also rebuild
byte-identically. Original audit, numerical rebuilding and fresh inference are
different levels of reproducibility. No stronger model, new scientist training,
reliable autonomous new-institution advantage or reality-level welfare result
is established. See the [whole-program completion ledger](../pre-scale-completion.md)
for implemented gradient/continuity/verification tracks, whose current-native
connection evidence is scripted QA rather than fresh Qwen superiority.
