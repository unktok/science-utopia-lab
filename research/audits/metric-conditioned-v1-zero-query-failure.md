# Metric-Conditioned v1 zero-query failure audit

Date: 2026-10-28  
Frozen source commit: `9f9868d5bac631f6c7c373229d7807a26695a62f`  
Affected campaign: `metric-conditioned-participation-review-v1` revision
`7afdb8f9bfd5`

## Decision

The frozen v1 campaign is paused after exhausting the declared two-attempt
budget for one logical run. Do not edit its worktree, reset its registry, mark
the run complete, or substitute another seed.

Resume the scientific design as protocol version v1.1 from a new clean,
commit-pinned source after:

1. repairing and testing the valid zero-query simulation path;
2. implementing the previously specified content-addressed artifact-adoption
   boundary; and
3. initializing fresh registries from that one source commit.

The eight completed v1 trajectories remain immutable engineering evidence.
They are not optimization observations in v1.1 and are not pooled across
source versions. V1.1 may reuse only artifacts produced by its own pinned
source through the audited adoption API.

## Failure evidence

Logical run:
`opt-metric-conditioned-participation-review-v1-7afdb8f9bfd5-longitudinal-optimization-d61de1ee4e74b-s607`

- design / seed: `d61de1ee4e74b` / `607`
- attempt 1: failed in year 4 after 2,962.19 seconds
- attempt 2: resumed the year-3 checkpoint and failed after 156.44 seconds
- attempt-2 scheduler: `scheduler-d92fd773e050`
- effective command SHA-256:
  `d77b532ad97319a07519ac7ed304476599d2615c5dcce07d907e38a7ed0b1e3a`
- final registry state: eight complete, one terminal failed
- held-out rows: zero

Both attempts failed at `utopia/data/rag.py:489` while multiplying query and
document embeddings. Attempt 2 makes the cause explicit:

- phase 1 selected zero active authors;
- phase 2 constructed zero submission queries;
- `SentenceTransformer.encode([])` returned shape `[0]`;
- the implementation incorrectly attempted a matrix multiplication against
  document embeddings of shape `[40134, 384]`.

Zero active authors is a scientifically meaningful outcome for this
low-funding/high-cost candidate, not invalid simulation input. The correct
behavior is an empty retrieval batch and continuation with zero new
submissions while preserving any resubmission path.

## Repair boundary

The repair returns an explicit `(0, 0)` retrieval result before any embedding
or index access when the query list is empty. It does not alter non-empty
retrieval, prompts, sampling, LossSpecs, seeds, search-space parameters, or
held-out metrics. Unit coverage exercises all three retrieval modes; the
full-text, portable-checkpoint, optimization, system, and replay suites are
also required to pass before the new protocol is frozen.

Even though the change is branch-local, the v1 protocol states that repairing
code creates a new source commit and study version. Consequently, the repair
is not installed into the frozen v1 worktree and the v1 registry is retained
as-is.
