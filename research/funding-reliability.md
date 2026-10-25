# Funding proposal reliability gate

## Purpose

Funding proposal generation is simulator infrastructure, not an optimization
objective. A design must not appear better because malformed model output
silently removes applications or because one institutional condition induces
more retries than another. This gate determines whether a completed run is
admissible for cross-design comparison; it never contributes positive utility.

The measurement-complete v1 baseline exposed the need for this boundary. Its
five runs conserved every application target, but 134 of 260 generation
attempts were semantically invalid and 6 of 132 targets ended in terminal
drops. Transport errors were zero.

## Root cause and repair

The funding prompt always showed the example `relevant_projects: [0, 2, 1]`,
even when a researcher had zero, one, or two past papers. With zero papers it
also instructed the model to choose an integer between 0 and −1. In seed 113,
8 of 10 researchers had no papers, yet each could target up to three funding
programs. The retry loop repeatedly presented the same contradictory example.

Trace schema v2 makes the repair explicit:

1. The example contains only indices that exist for that researcher.
2. With no papers, the prompt states that an expertise-based application is
   allowed but `relevant_projects` must be empty.
3. Optional invalid references are removed deterministically and recorded as a
   `valid_sanitized` generation outcome. The proposal itself is not discarded.
4. When papers do exist and more than half the supplied indices are invalid,
   the response remains semantically invalid and is retried.
5. Structural errors, request errors, retry exhaustion, explicit non-submission,
   and application conservation retain their previous distinct states.

Sanitization is counted rather than hidden. This prevents an apparent fix that
merely renames hallucinations as successes.

## Versioned v2 policy

`research/specs/study-v2-smoke.json` declares policy
`funding-pipeline-reliability` version `1.0.0`:

| Check | Gate |
|---|---:|
| Minimum selected targets | 10 |
| Semantic-invalid attempts / generation attempts | ≤ 0.10 |
| Sanitized-reference attempts / generation attempts | ≤ 0.10 |
| Request-error attempts / generation attempts | ≤ 0.05 |
| Terminal drops / selected targets | 0 |

These are provisional engineering tolerances, not claims about good science.
Zero terminal drops is strict because a drop changes the application set and
can be confounded with the institutional design. The nonzero attempt-rate
tolerances allow occasional model-format noise while forcing it to remain a
small fraction of the simulated process. The minimum support prevents a clean
but tiny run from certifying the interface.

The policy ID, version, complete content hash, rates, reasons and disposition
are written into the aggregate report. A failure or insufficient support gives
the run disposition `quarantine` and closes design-level
`authorized_for_ranking`. The simulator run may still be technically complete
and useful for diagnostics. Reliability cannot compensate for a failed hard
constraint, and scientific objectives cannot compensate for failed reliability.

## Version boundary

Revision `1cc1b68161` and its trace-v1 artifacts remain unchanged historical
evidence. They do not contain the sanitization counter and must not be silently
reinterpreted under policy 1.0.0. Corrected cross-design comparisons use the
new `evaluation-v2` study revision, trace schema v2, and a clean source commit.

## Acceptance evidence

Before running institutional candidates:

1. deterministic fixtures must cover zero-paper prompts, bounded examples,
   sanitization, retained semantic retry, terminal drop and quarantine;
2. the funding and optimization suites must pass;
3. a Qwen3-8B probe with at least 10 mixed zero-paper/two-paper targets must
   pass the declared policy;
4. the first full baseline v2 run must pass conservation, objective evaluation
   and the reliability gate before the remaining candidate runs are authorized.
