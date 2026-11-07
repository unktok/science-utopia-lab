# Objective-feedback comparison: implementation and finite local pilot

User2026-11-07: proceed thoroughly with the publication research plan.
Start from clean33f41e0 in a separate `research/loss-feedback-control-v1`
development worktree. No prior experimental checkout/output is edited.

## Implementation

Add an optional technical-only proposal policy to the existing native adaptive
campaign, not another simulator/optimizer. Preserve default binding/request
bytes. Keep true observations/losses internally; expose a cost-independent
allowlisted view with fixed initial parent and chronology, including all own
authored designs and technical states. Remove outcome-derived hashes and
optimizer reports from that view. Actual bounded prompts and every virtual
archive use that same input, not a read-through to the private original state.
Reject unsupported mixed/score/history-bank control configurations.

Initial focused check:17 pass/1 failure. The failure was the new test attempting
to parse a >65536-character archive after one intentionally bounded read, not a
partial scientific result or a production truncation. Correct the test to read
explicit chunks and verify exact reconstruction. The revised context/control
suite passes18 tests; comparison-driver/control scope passes16 tests. These
overlap and are not an additive test total. No model/world call in these tests.

Add a finite common-source driver and prospective protocol: two objectives,
two proposal policies, two generations, at most eight candidate slots plus one
shared baseline world. No historical warm start, hidden refill, inferred finish,
merit veto or changed objective. The comparison is adaptive feedback+parent
selection versus fixed-parent technical-only proposals, not scalar scores alone.

Local backend metadata GET confirms the existing server responds and no model
is resident at04:45UTC. This is not calibration or evidence of generation.

## Verification and actual dispatch

Pending committed-source regression, real-backend execution-readiness calibration
and cold replay. No actual comparison result exists at this entry's first commit.
Keep later source/test identities and outcomes explicit below.
