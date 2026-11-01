# Native objective/structure v8: independent audit and figure

Status: implemented and synthetic-fixture tested. The actual `a1` technical
preflight abort has a compact audit receipt; no native v8 outcome is published.

## Purpose

The v8 pilot asks whether the same open native structural search behaves
differently under two explicit development losses.  The optimizer changes the
system; it does not change either objective.  The fixed objectives are the
existing `native-joint-v5-throughput` loss, \(L=-A\), and the existing
`native-joint-v5-net-reviewed-utility` loss,
\(L=3.25A-Q+0.05R\).

`scripts/analyze_native_objective_structure_v8.py` is a result-blind,
read-only consumer of a terminal or explicitly incomplete raw directory.  It
does not call a model, simulator, sandbox, or generated source.  Its output
must be outside the raw directory.

The audit separates four contracts:

1. **Optimization loss:** the two frozen LossSpecs and their observed
   development losses.  Every completed checkpoint is cross-scored under both
   losses.
2. **Technical validity:** campaign replay, exact authoring receipts, immutable
   checkpoint and response-cache evidence, and null technical failures.
3. **Held-out metrics:** explicitly not defined or measured in this pilot.
4. **Promotion policy:** explicitly not defined or applied in this pilot.

Thus a low observed loss is neither a held-out result nor permission to promote
a system.

## Fail-closed evidence boundary

The audit requires the frozen two-arm plan, exact source commit, 2 generations
by 2 conditional-IID draws per arm, seed 42, original five-researcher native
world, two-year horizon, four-year corpus, Qwen3-8B settings, and the v8
development experiment binding.  It reopens both adaptive campaigns with a
write-disabled subclass and reconstructs every external manifest request from
the saved history, loss, strategy state, weights, and instructions.

For each completed draw it restores the original portable checkpoints and
independently reconstructs all eight native diagnostics:

- accepted and rejected decisions;
- review records;
- final active authors and author resources;
- institutional-context deliveries;
- accepted unreviewed decisions; and
- accepted peer-score sum.

It then evaluates both frozen LossSpecs from those measurements and requires
the arm's result to equal the saved optimization observation. If a metric used
only by the other objective is unavailable, the completed own-objective world
is retained while that cross-score is `null` with the evaluator's reason.
Invalid generated vocabularies are retained as generation failures with zero
executed draws; the planned two draws are not fabricated. Failed or incomplete
physical worlds retain `loss: null`; they are never converted to an optimizer
penalty. Every SQLite response cache is path-, hash-, and
outcome-count bound, and the entire raw file inventory must be byte-identical
before and after analysis.

## Structural accounting

Each sampled system is compared both with the frozen initial system and with
the exact parent system exposed to its generation.  The report preserves exact
node and edge additions/removals, endpoint-pair rewires, and executable Python
source-hash changes.  It separately records protocol, mechanism configuration,
and schedule changes. Source-body multisets distinguish a mechanism-ID rename
from adding or removing an algorithm body, including wrapped delegates.
Initial-state changes are recorded with hashes and explicitly do not count as a
new algorithm. These are literal differences, not claims about semantic
novelty or institutional effects.

Selection is the minimum finite observed development loss within each arm.
Every exact tie is retained; the earliest tied row is only a deterministic
display representative.  Cross-objective values reuse the same physical
worlds and therefore are not independent replications.

## Figure

`scripts/figures/native_objective_structure_v8.py` consumes only the
hash-bound independent audit.  Its three panels show:

- the real arm-specific development loss paths, leaving technical failures as
  gaps;
- the two selected representatives cross-scored under both raw loss units; and
- exact graph/source differences versus the generation parent.

Matrix color is scaled within each objective only for display; annotated cells
retain the raw values.  The figure states that it provides no held-out,
causal, scientific-value, convergence, or improvement claim.  A report marked
as a scripted fixture cannot be written into `paper/figures`.

`scripts/figures/native_objective_structure_v8_methods.py` separately renders
the result-independent methods flow: frozen objectives, objective-visible
authoring, conditional-IID designs, the fixed original-native world,
independent diagnostics, arm-only adaptive feedback, and later cross-scoring.
Held-out metrics and promotion policy appear beyond a dashed boundary as not
defined in v8.

`scripts/reports/native_objective_structure_v8_paper_slice.py` prepares an
include-ready NeurIPS LaTeX fragment only after an actual audit and both figure
manifests are hash-verified.  It never edits `paper.tex`, and it rejects a
scripted fixture.  Integrating the generated fragment remains a separate,
reviewed publication action.

## Post-run commands

Run only after the raw writer is terminal and the source commit is known:

```bash
.venv/bin/python scripts/analyze_native_objective_structure_v8.py \
  --run /absolute/path/to/raw-v8 \
  --expected-source <40-hex-source-commit> \
  --output /absolute/path/outside-raw/native-objective-structure-v8-audit.json

.venv/bin/python scripts/figures/native_objective_structure_v8.py \
  --report /absolute/path/outside-raw/native-objective-structure-v8-audit.json \
  --output /absolute/path/outside-raw/native-objective-structure-v8

.venv/bin/python scripts/figures/native_objective_structure_v8_methods.py \
  --output /absolute/path/outside-raw/native-objective-structure-v8-methods
```

An explicitly frozen, incomplete attempt may instead be recorded without
inventing terminality or outcomes:

```bash
.venv/bin/python scripts/analyze_native_objective_structure_v8.py \
  --run /absolute/path/to/frozen-incomplete-v8 \
  --expected-source <40-hex-source-commit> --allow-incomplete \
  --compact-attempt-id a1 --aborted-technical-preflight \
  --output research/results/native-objective-structure-v8-a1.json
```

That compact receipt retains the complete raw file path/hash inventory and
authoring/request hashes while omitting bulky generated system payloads. The
abort flag is fail-closed: it requires zero physical worlds and replies,
nonterminal budget accounting, generation failures, and pending requests.

These commands perform no new inference.  Actual-data publication remains a
separate, explicit action after the raw run and audit are frozen.
