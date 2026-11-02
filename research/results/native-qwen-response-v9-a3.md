# Native Qwen response-gradient v9 audit

- Status: `complete`
- Source: `fb2d1b6f07aadba39148bd5871dac2fd0595b618`
- Audit content SHA-256: `92d6a9b630d9bcd44e379ec48833aed2de71490b85907068fed740361826abbf`
- Completed common-prefix-coupled logical worlds: 6 / 6
- Fresh physical replies: 186
- Logical responses: 504
- Replayed prefix responses: 318
- Replies in completed endpoints: 504
- Replies in partial null-loss worlds: 0

## Observed development losses

| world | weight | fixed native loss | A | Q | R | logical | fresh | replayed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| calibration-0 | 0.2 | 0.9 | 0 | 0 | 18 | 84 | 31 | 53 |
| calibration-1 | 0.5 | 0.9 | 0 | 0 | 18 | 84 | 31 | 53 |
| calibration-2 | 0.8 | 0.816666667 | 1 | 3.3333333333333335 | 18 | 84 | 31 | 53 |
| unused-0 | 0.35 | 0.9 | 0 | 0 | 18 | 84 | 31 | 53 |
| unused-1 | 0.65 | 0.9 | 0 | 0 | 18 | 84 | 31 | 53 |
| gradient-candidate | 0.5 | 0.9 | 0 | 0 | 18 | 84 | 31 | 53 |

## Interpretation boundary

The table contains fixed-objective development measurements, including an unfavorable or tied candidate if observed.
The gradient is autograd through a calibration-fitted numeric response representation, not an exact Qwen or native-world Jacobian.
Unused coordinates are fidelity checks, not held-out seeds. No promotion policy or causal scientific-benefit claim is applied.

## Actual common-prefix coupling

- Unique anchor-origin calls: `53`
- Prepared manifest: `37145b8c9a8df9cb0f8a8bbc2012312d22a4a8aa69538d8fba9a0cfb908a0f3d`

The six development worlds execute the full native forward process but share one exact actual-Qwen prefix.
Replayed prefix responses are logical cache entries, not new model calls or independent world replications. Anchor-origin calls are counted once outside the a3 fresh-call total.

## Frozen update outcome

- Candidate weight: `0.5`
- Candidate minus center native loss: `0.0`
- Observed status: `tied`
- Proposal ordering: content-bound and calibration-only; historical creation time is not independently authenticated.
