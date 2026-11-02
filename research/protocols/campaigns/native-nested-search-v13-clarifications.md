# V13 wording clarifications, no experimental amendment

2026-11-02, during execution, following independent source/document review.
The source-pinned prospective protocol remains byte-unchanged. These are
clarifications of its already implemented contracts, not a loss, budget,
proposal, world or source-code change informed by outcomes.

- If **G0 is valid** but its update is unavailable, the scheduled updated-proposal
  draw uses unchanged G0 weights. If **G0 itself is invalid**, no such vocabulary
  exists: the next slot is explicitly unavailable/consumed with zero native
  worlds, not replaced by a baseline or fabricated distribution. This is
  `native_nested_search.py`'s frozen `_compile` behavior.
- IID means conditional **design sampling**, not independent scientific seeds
  or response replications. All worlds still reset the fixed development seed42.
- The continuous latent is an **unbounded Gaussian**, mapped through a fixed
  sigmoid to declared bounded design coordinates, not a truncated Gaussian.
- Complete plan provenance preserves the **pre-amendment upstream plan**;
  that upstream producer is not restricted to the original research routine.
  Source/wire/event/state joins and pure hash-consistent reconstruction do not
  reexecute source or establish scientific correctness.
- A scheduled post-update evaluation may itself fail. In that case the updated
  proposal remains unevaluated, with null loss and no replacement. A completed
  followup is not guaranteed by scheduling it.

The manuscript and component notes adopt this more precise wording. No new
native attempt, score, hidden validity rule or retrospective successful claim
is introduced.
