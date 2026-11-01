# Joint native design: two explicit engineering objectives v5

These two losses condition the **designer**; the optimized object is the actual
institutional Python/protocol/graph SystemSpec, not the objective itself.
Both use the unchanged native researcher world. There is no implicit quality,
fairness, participation or promotion veto.

- Throughput: `L = -A`, actual accepted review-history decisions.
- Net reviewed utility: `L = 3.25*A - Q + 0.05*R`, where `Q` is the sum of
  within-decision arithmetic means of **raw reviewer overall_score** over
  accepted decisions, and `R` is all actual review records, rejected or accepted.

The institution-written final score is deliberately excluded from `Q`. An
unreviewed acceptance contributes zero `Q` and still incurs acceptance cost.
A missing/nonfinite score in an existing accepted review makes `Q` unavailable;
it is not silently zero-imputed or converted into an optimization penalty.
Count loss remains available independently. Empty worlds have all three values
zero and are legal observations. The 3.25 and 0.05 coefficients are illustrative
declared publication/review costs, not calibrated social welfare or science
quality. Review scores are fixed-LLM outputs, not verified epistemic value.

These are not merely opposite signs of acceptance count: two accepted decisions
with raw means 3 and 5 tie on throughput but yield utility losses 0.30 and -1.70
with one review each. Reject-all, all-accept, and unchanged behavior are legal;
technical interface validity does not impose a merit threshold.

`scripts/audit_native_objective_v5.py` reconstructs eight measurements directly
from completed portable checkpoints without importing the simulator measurement
adapter. It checks native event restoration, exact campaign patch/incumbent
lineage, external checkpoint hashes, executed code/image receipts, source/model/
corpus/seed bindings and read-only response journal content. It cross-scores
every candidate under the supplied comparison losses. Cross-scoring and any
explicit common-baseline adoption reuse physical worlds; they are not new
independent replicates or held-out evaluation. No new inference is performed by
the auditor.

Public reuse API: `checkpoint_measurements(path, run_id, fingerprint)`. The caller
**must first verify the external archived checkpoint SHA256**. Portable reading
validates the envelope, not a cryptographic file hash. The API independently
requires the final year and completed phase before returning measurements.
