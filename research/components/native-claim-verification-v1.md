# Native empirical claims, independent verification and correction

This opt-in component extends the original research world; it is not a second,
simplified world. Its first task is intentionally narrow: verify an institution's
asserted count of actual accept/reject decisions or individual review records
over an explicitly completed native interval.

`utopia/system/native_claim_verification.py` supplies an independent consumer.
`attach_claim_verifier` connects any producer of `native-world-count-claim-v1`
artifacts to that consumer, then connects its verdict to the actual researchers'
institutional context. The producer can be sandboxed Python, an LLM institution,
or another graph mechanism. It supplies an assertion, not executable verifier
code or its own truth flag. Removing/changing the delivery edge is an ordinary
institutional intervention; registration alone does not run the verifier.

The verifier reads the actual simulation's paper archive and review histories,
not a candidate-supplied observation or declared measurement. It records the
literal assertion, computed count, evidence hash and boolean consistency result.
A correction has a new claim ID, names its predecessor and must concern the same
metric and interval. Both records remain; the successor binds the predecessor's
verdict hash. Malformed batches fail before state changes. Retained verification
state is recomputed against actual records, so a seeded `matches=true` flag
cannot bypass checking. Claims about future periods and unsupported quantities
are rejected, not assigned invented scientific scores.

The scripted integration test uses the original six-year `Simulation`, real
networkless Docker code execution, and scripted corpus/model responses. A code
producer asserts an intentionally incorrect count in year1, corrects it in year2,
and actual research-direction inputs receive the false verdict in year2 and
both records in year3. This is **software/effect-path evidence**, not a live-Qwen
experiment, automatic invention or evidence that researchers use it well.

Limits matter: these are internally verifiable empirical claims about the
simulated society, not tests of the truth of its retrieved papers, experimental
replication, an external discovery benchmark or a new optimization objective.
No quality/novelty/promotion veto or default scientific phase is added. The
mechanism/measurement boundary remains explicit; a candidate may author new
activities, but cannot establish an external truth merely by naming an artifact.

Tests: `tests/system/test_native_claim_verification.py`. Initial focused run:
19 passed, including one original-world/Docker integration. Earlier failed
assertion checks concerned the test's nested text-part decoding, not fabricated
successful transport or changed live experiment observations.
