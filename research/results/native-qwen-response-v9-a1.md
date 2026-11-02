# Native Qwen response-gradient v9 audit

- Status: `valid-preserved-partial-failure`
- Source: `d5b08d64193c32bf05dec95e54ba53d2f1b8cab9`
- Audit content SHA-256: `6f6a27ed21f740e247b792f9974df48ea0ecbd02120421f185bf4e8f8713800e`
- Completed physical worlds: 2 / 6
- Fresh physical replies: 202
- Replies in completed endpoints: 169
- Replies in partial null-loss worlds: 33

## Observed development losses

| world | weight | fixed native loss | A | Q | R | replies |
|---|---:|---:|---:|---:|---:|---:|
| calibration-0 | 0.2 | 0.9 | 0 | 0 | 18 | 84 |
| calibration-1 | 0.5 | 0.9 | 0 | 0 | 18 | 85 |

## Interpretation boundary

The table contains fixed-objective development measurements, including an unfavorable or tied candidate if observed.
The gradient is autograd through a calibration-fitted numeric response representation, not an exact Qwen or native-world Jacobian.
Unused coordinates are fidelity checks, not held-out seeds. No promotion policy or causal scientific-benefit claim is applied.

## Independent-Qwen prefix diagnostic

- Status: `observed-uncontrolled-prefix-separate-from-terminal-failure`
- Comparator detail: `uncontrolled actual pre-intervention/prompt drift: normalized_final_review_payloads_sha256, preintervention_physical_reply_count, preintervention_request_response_sequence_sha256, preintervention_world_observation_sha256`

The completed independent worlds changed before the declared rubric intervention, so this prefix cannot identify a controlled response fit.
This stochastic prefix drift is separate from the recorded terminal stop and is not a negative response-fidelity, optimization, or scientific result.

## Preserved terminal failure

The attempt stopped after the completed prefix. The failed slot has null loss; no missing world or confidence statement was fabricated.

```json
[
  {
    "elapsed_seconds": 199.80216193199158,
    "error": "signal 15",
    "error_type": "PortableStop",
    "loss": null,
    "name": "calibration-2",
    "theta": 0.8
  }
]
```
