# V13: free institutional redesign around one conditional-weight step

Status: completed finite development pilot. The fixed budget closes at eight
original-native worlds, 592 fresh Qwen3:8B replies, zero response reuse and zero
world-level technical failures. Independent read-only audit runs twice with
byte-identical JSON and preserves all 129 raw input files.

The actual source is `fdf4d1c16964891e890cabe68d59b2820f462b92`. Five native
researchers, two years, scientific seed 42 and the four-year original corpus are
unchanged. Researcher model weights are fixed, not their institution-dependent
responses. Source authors are external, self-reported Codex specialists; the
inventor is not the researcher Qwen model, and authorship is not authenticated.

## What was optimized

The exact two illustrative engineering losses are `L_T=-A` and
`L_E=-Q+0.5R`. A counts accepted decisions, Q sums original native per-review
integer-score means for accepted decisions, and R counts actual review records.
An unreviewed acceptance contributes zero Q. No quality, fairness, novelty or
promotion veto is added. These proxies are not scientific value.

Each arm follows the frozen sequence: freely authored G0 vocabulary → two IID
conditional design draws → one leave-one-out likelihood-ratio step → one fresh
forward-only draw using the exact same G0 vocabulary and resulting weights →
free G1 source redesign using all three own observations → one forward-only draw.
The last two singletons do not update again. Failed slots would remain null;
none failed here. No observation or budget was replaced to obtain improvement.

## Every native outcome

| Arm and slot | Own loss | A | Q | R | Actual routed tasks | Unreviewed accepted | Fresh replies |
|---|---:|---:|---:|---:|---:|---:|---:|
| Throughput G0a | -7 | 7 | 0 | 0 | 0 | 7 | 73 |
| Throughput G0b | -7 | 7 | 0 | 0 | 0 | 7 | 73 |
| Throughput updated forward | -6 | 6 | 0 | 0 | 0 | 6 | 67 |
| Throughput G1 | -10 | 10 | 0 | 0 | 0 | 10 | 83 |
| Efficiency G0a | -17 | 6 | 20 | 6 | 6 | 0 | 73 |
| Efficiency G0b | -12.5 | 6 | 18.5 | 12 | 12 | 0 | 79 |
| Efficiency updated forward | -10 | 6 | 12 | 4 | 4 | 2 | 71 |
| Efficiency G1 | -18 | 6 | 21 | 6 | 6 | 0 | 73 |

Throughput's complete loss path is `[-7,-7,-6,-10]`; efficiency's is
`[-17,-12.5,-10,-18]`. Each final G1 is its arm's unique observed best. All
earlier observations and the two exact throughput G0 ties remain in the audit.
The best-throughput system cross-scores `(-10,0)` and the best-efficiency system
cross-scores `(-6,-18)` under `(L_T,L_E)`. These reuse development checkpoints;
they are not held-out results, paired controlled interventions or comparable
numeric scales on a single universal objective.

## Conditional update versus free source revision

Throughput G0 uses an explicitly generated hash-based cohort rule to give a
fraction of researchers one-year projects and the others two-year projects.
One Gaussian latent controls the bounded annual-cycle share. Both initial
costs are -7, so the two LOO advantages and gradient are exactly zero. The latent
mean remains 0. The fresh same-distribution forward draws share 0.204317 and
observes -6; it is not a beneficial policy update. Initial shares were 0.601353
and 0.377223. Zero gradient is preserved rather than rerolled.

Throughput G1 replaces that cohort algorithm with universal one-year cycles,
removing the now-unused share parameter and continuous vocabulary. It retains
explicit zero-review dispatch and all-accept selection, producing ten actual
accepted decisions across two years, five in each year, with no reviews. The
researchers' own topic/focus/reason, native retrieval, submissions and resource/
funding routines remain. This is a gameable throughput outcome, not a claim of
scientific benefit or a global optimum over all possible scientific systems.

Efficiency G0 freely authors a native review-allocation office and compatible
universal admission. A categorical factor chooses zero, one or two reviewers
per covered paper, while a Gaussian-latent coordinate controls hash-lottery
coverage. The two initial assignments choose one and two reviews. The sole LR
step changes mean `1.5 → 1.6710855702526985` and categorical logits
`[-1,1,-1] → [-1,1.225,-1.225]`; independent scalar analysis rederives the
gradient mean `-1.710855702526986` and logits `[0,-2.25,2.25]`.
This is a conditional likelihood derivative, not source/LLM/world backpropagation.

The fresh updated-distribution draw chooses one reviewer and coverage 0.509912,
leaving two accepted papers unreviewed. It observes -10, worse than initial
best -17. Thus neither arm's post-update draw beats its initial best. One fresh
outcome does not identify the expected direction or effectiveness of the LR
step, and there is no equal-budget estimator comparison.

Efficiency G1 then replaces the allocation algorithm with full coverage and one
eligible reviewer per submission, ranking reviewers by a unit-shrinkage estimate
of their prior raw scores. It explicitly declares empty factor/continuous lists;
no gradient or control state is silently transported into this new source.
The new actual outcome is Q=21, R=6, loss -18, compared with G0a's Q=20, R=6,
loss -17. This is favorable-reviewer routing under the chosen proxy, not evidence
of better reviewer accuracy, scientific quality or causal improvement.

A separate report-only memory audit verifies all 22 claimed historical review
identities and native-record hashes against exactly the three completed own
request-bound checkpoints (6+12+4 reviews), totaling 69 score points. Reviewer
sums/counts are `20/6`, `18/6`, `15/5` and `16/5` for institutions 1–4. The pooled
prior is `69/22`; forecasts affect task IDs only, never native reviewer scores.
The full source AST was inspected, not executed by that supplementary auditor.
Its file SHA is `02829be7a58d68f5efad78a4e7c416f47a0c8df0a6ce80ea3a3f7bc9cbf6a519`
and content SHA is `339d74deb67e976e22e1b4a7427908ce5d89655feb435274ed521507e3ca9d95`.
This check is not a new validity/promotion gate or OS-level access attestation.

## What the native evidence establishes

The throughput systems have 17 nodes/25 wires and the efficiency systems 16/23.
G0's authored bases add respectively three/two new source bodies relative to the
shared open-native seed while replacing/removing inherited institutions. Both G1 revisions
replace one executable source body but retain their parent graph, wiring,
protocol and process topology. The API permits structural changes; this pilot
does not demonstrate a new topology in G1 or prove algorithmic novelty from a
source hash change.

Across eight worlds the audit verifies 40 actual isolated source executions,
16 complete native research-plan effects, 16 pre-review routing events and
28 actual routed reviews. Captured full original plans plus exact amendments
reconstruct applied-plan hashes and submitter order. Generated outputs join
their source/container events and explicit wires. Routing commands join actual
native submissions, eligibility snapshots, original task identities, archived
integer-parsed reviews and exact response-cache item/attempt/seed/prompt hashes.
No source, container, native world or model is executed by the audit.

The measured model-call times sum to 2094.17 seconds (34.90 minutes): throughput
1069.70 seconds and efficiency 1024.47 seconds. This is not overall project,
source-authoring, QA, audit or end-to-end wall time.

## Interpretation and limits

This finite slice connects free code/protocol/graph generation, a conditional
weight update, original-world feedback and new source revision in one durable
loop. Both result-conditioned G1 revisions improve their observed own metric;
the two intermediate updated-distribution forwards do not. It is therefore not
merely proof that eight simulations can execute, but also not proof of a useful
autonomous institutional inventor, improved designer or successful gradient
method.

The contrasting selected systems expose the importance and gameability of the
chosen objectives: throughput selects annual, unreviewed admission; the reviewed
score/work proxy selects a reviewer-allocation heuristic informed by favorable
past scores. Paper/context confounding, tiny historical counts, one development
seed and adaptive use of all three prior worlds prevent reviewer-ability,
generalization, expected-loss, statistical-superiority and causal science-policy
claims. Whole-world differentiability is neither implemented nor required here.
Researcher-world realism, broader institutional freedoms and better objectives
remain research questions; no scale-up is used to conceal these boundaries.

## Artifacts and exact identity

- [Independent audit JSON](native-nested-search-v13-a1.json): file SHA
  `201263f4667fd1ad962d4e885148e3c518fdc72771a2d02d2c07c68e67c9c96a`, content SHA
  `abb671726c48e797a0af28b3fff27b49c0b2fb6a79c3adcb0bd6bb7602bf34ba`.
- Both read-only audits preserve 129 raw files; inventory SHA
  `f8e385dde54b0de3218e34796f6688ca19155f5a5eb425e5596e7ac984d91408`.
- All 227 replay-critical runtime, driver, protocol, loss and reused helper
  source blobs match the actual source pin.
- [Actual six-panel figure](../../paper/figures/native-nested-search-v13-a1.png)
  and its adjacent SVG/manifest preserve full-precision plotted data. Native
  print size is 5.5×7.8 inches, with all labels at least seven points.
- [Frozen protocol](../protocols/campaigns/native-nested-search-v13.md) and
  [independent audit contract](../components/native-nested-search-independent-audit-v13.md).

Raw worlds, response journals, authoring inboxes, repeated audit and supplemental
memory receipt remain under ignored local outputs, not copied into the repository.
