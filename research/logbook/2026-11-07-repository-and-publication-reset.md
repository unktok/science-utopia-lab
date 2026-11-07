# Repository → research goals → publication-oriented work

User request2026-11-07: maintain the repository, review the whole purpose, then
decide and start work toward a top-conference research paper. This is not a
request to silently launch another local-author debugging campaign.

## 1. Repository maintenance

Work begins from clean main5ae3c5c, in a separate
`chore/research-publication-reset` worktree. No raw output, model, branch,
historical protocol/result or frozen experiment checkout is removed.

The old README, RESEARCH, INDEX, STATUS, roadmap and program-map are preserved
byte-for-byte in same-directory `*history-through-v45.md` snapshots. A tracked
[manifest](../results/repository-docs-reset-v1.json) records old commit and hashes.
Relative links retain the same parent. Current entrances are rewritten:
README375→72 lines(before the new publication link), INDEX507→55,
STATUS2619→80 before the short publication update. Historical counts describe
that initial rewrite, not permanent line limits.

Add a repository map and a stdlib-only offline checker for active inline-link
targets and snapshot hashes. Initial12 documents/181 local links/6 snapshots
pass;7 dedicated tests pass. Contributor setup now makes the required pip
version check explicit, and development docs distinguish the current Phaser/
Vite UI from the legacy buildless viewer. No dependency or server is installed.

## 2. Original purpose and scope

[RESEARCH](../../RESEARCH.md), [program map](../program-map.md) and
[roadmap](../roadmap.md) are rewritten around the original six goals: whole-system
objective-conditioned optimization; non-template institutions; graph/process
freedom; useful gradients/estimators; continuing/recursive improvement; and the
same-world game/evidence interface. The original researcher world is contained,
not replaced with a simpler numeric world. Full differentiability is optional.
Keep technical validity, loss, evaluation and optional adoption policy separate.

The first paper need not claim every long-term goal. Its organizing question is
how objectives, design freedom and search methods change discovered institutions
and their consequences, not whether a particular local editor can submit JSON.
Earlier external-author positive results, recent local-author failures, tied
outcomes and conditional-gradient limitations remain explicit.

## 3. Publication planning and concrete implementation

Read official NeurIPS reviewer guidance, ICLR2027 CFP, ICML2027 official page,
the original ScienceUtopia abstract/HTML, and primary related-work descriptions.
Record links and access date in the [publication plan](../publication/plan.md)
and [initial literature note](../publication/related-work.md). This is scoping,
not a full-text exhaustive novelty review. ICLR2027's paper deadline has passed;
ICML2027's submission deadline is not yet announced on its official page.
NeurIPS/ICML are provisional fit judgments, not acceptance predictions or a
commitment to invented future dates.

Define a [matched-comparison contract](../publication/benchmark-contract-v1.md)
for objective/freedom/proposer axes. Flag no-feedback leakage via loss-selected
parents, candidate order and strategy state; technical errors remain separate
from scientific loss feedback. The illustrative8 candidate slots+1 baseline
are a future minimal-pilot design, NOT a frozen or executed campaign.

Implement the first research-analysis task:
`scripts/reports/publication_evidence.py`, with a source/schema/content-bound
four-study catalog. Actual V10/V12/V13/V45 files produce a reproducible
[inventory](../results/publication-evidence-inventory-v1.json). It retains all
own paths, nulls, best ties, historical references, cross-scores, author notes
and per-case physical costs without inventing a pooled matched-method ranking.
Historical numerical observations do not silently acquire the later report's
execution-source identity. Duplicate case IDs/file aliases, stale hashes,
source swaps, nonfinite/bool losses, duplicate JSON keys and overwrites fail.

The inventory is not a new raw audit, benchmark run or complete project census.
New code imports no simulator/provider, executes no generated source and makes
no model/world call. The existing long TeX draft is labeled historical; a
[claim-centered outline](../../paper/submission-outline.md) identifies the next
rewrite rather than silently changing published-looking numbers or PDFs.

## Verification

The final offline documentation check passes16 active documents,146 local
inline targets and6 exact historical snapshots. This is not a remote-URL or
anchor validator. The selected repository/publication/native-review/V45-summary/
driver suite first passes52 tests with3 explicit optional archive skips.
Providing the existing read-only V44 audit then passes all55 tests in1.99s,
without inference or a native-world execution. The original audit is checked
unchanged by the archive fixtures. `git diff --check` also passes.

Local untracked QA logs and JUnit reports are retained under
`outputs/repository-publication-reset-v1/` in the main checkout; the second run
is `pytest-with-archive.log` / `pytest-with-archive.xml`. The new inventory is
also tested byte-value-equivalent to regeneration from its pinned four inputs.
These selected checks are not a new full source-bound runtime integration audit.

## Next work

Implement the loss-feedback-blinded proposal comparison on the existing native
campaign boundary, test information leakage, freeze a finite common-source
protocol and obtain its actual backend calibration before dispatch. Then run a
small comparison, not a scale-up. Free-versus-parameter and independent selected-
system evaluation follow under separately declared budgets. Positive results
are not required to finish a budget, and hidden scientific vetoes are not added.
