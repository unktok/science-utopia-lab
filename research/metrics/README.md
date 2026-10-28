# Evaluation metrics

Evaluation metrics characterize a frozen candidate on held-out seeds or stress
scenarios. They are analogous to accuracy, calibration, robustness, or subgroup
analysis reported after optimizing a training loss.

Current measurable signals include participation, review burden, topic-label
spread, funding inputs, activity counts, and reliability diagnostics. Their
existence does not automatically make them optimization objectives or vetoes.

If a metric is used to tune or select a candidate, record it as an effective
loss or selection criterion for that campaign and allocate new held-out evidence
for final evaluation.

[`semantic-instrumentation-v1.md`](semantic-instrumentation-v1.md) is an earlier
measurement layer: versioned claim/evidence/verification/replication/correction
events and synthetic shadow diagnostics. It is explicitly neither a LossSpec
nor a held-out metric, and cannot select or veto candidates.

[`prospective-semantic-recorder-v1.md`](prospective-semantic-recorder-v1.md)
adds a default-disabled producer boundary for a future simulator: explicit
typed event append, run/system/model fingerprint binding, hash-chain integrity,
and fail-closed checkpoint/resume. It does not infer semantics from existing
paper/review text, wire itself into the current runner, or expose recorded
events to optimization.
