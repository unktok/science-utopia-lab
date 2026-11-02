# Native Qwen response-gradient v9 audit

- Status: `valid-preserved-partial-failure`
- Source: `a1d7870c619aded1bbcac199084781f8b774357c`
- Audit content SHA-256: `1bc2e04f4dc81e8319714eaf08e464863e3b186515d063dd78c097b7a03028bc`
- Completed physical worlds: 0 / 6
- Fresh physical replies: 26
- Replies in completed endpoints: 0
- Replies in partial null-loss worlds: 26

## Observed development losses

| world | weight | fixed native loss | A | Q | R | replies |
|---|---:|---:|---:|---:|---:|---:|

## Interpretation boundary

The table contains fixed-objective development measurements, including an unfavorable or tied candidate if observed.
The gradient is autograd through a calibration-fitted numeric response representation, not an exact Qwen or native-world Jacobian.
Unused coordinates are fidelity checks, not held-out seeds. No promotion policy or causal scientific-benefit claim is applied.

## Preserved terminal failure

The attempt stopped after the completed prefix. The failed slot has null loss; no missing world or confidence statement was fabricated.

```json
[
  {
    "elapsed_seconds": 174.32770609855652,
    "error": "signal 15",
    "error_type": "PortableStop",
    "loss": null,
    "name": "calibration-0",
    "theta": 0.2
  }
]
```
