# Final-v11-control proposal: two fresh native evaluations

The previously unevaluated final v11 corrected-control proposal now has two
fresh original-native outcomes. Both worlds complete. Their utility losses are
**1.05 and 0.55**, with **180 fresh Qwen responses** and no world-level technical
failure. This closes the missing forward-evaluation step, not a claim that the
control-variate estimator improved expected loss or reduced variance.

The [independent audit](native-control-followup-v12-a1.json) reaudits the archived
v11 parent from its clean historical source, reconstructs the final proposal and
both saved draws, reextracts native checkpoint measurements, and verifies every
physical response/code receipt. Repeated independent audits are byte-identical;
all **32 followup raw files** and the immutable v11 parent remain unchanged.
The auditor starts no model, simulator, generated source or container.

## What was evaluated

- New experiment source: `ecab4b45c3ec19458aab1e492213518c855cf2f4`.
- Parent experiment: v11 at `acf3a2e4b995f8a04f4b0b56011a7051fe73a112`.
- Parent re-audit source: clean historical
  `77e3b9e72b9ca584a8fdbad847895f55fe7cb9ea`.
- Original five authors, two native years, world seed42, four-year real corpus,
  fixed Qwen3:8B and exact existing utility `LossSpec`:
  `L = 3.25 A - Q + 0.05 R`.
- `A` counts actual accepted review-history decisions; `Q` is the sum of their
  original integer-parsed per-paper reviewer means; `R` counts actual reviews.
- Frozen final conditional proposal: continuous mean
  `-0.1150163404137367`; mean/minimum aggregation logits
  `[-0.06055868973308312, 0.06055868973308312]`.
- Draw seed43, world seed42, two draws maximum, no response reuse or resampling.
  No further optimizer update, new institutional source/topology invention,
  hidden fairness/quality/novelty veto or promotion policy is applied.

All214 parent runtime file paths are accounted for. Actual forward-world files
retain the v11 bytes. The one explicitly reviewed exception is the opt-in
singleton black-box optimizer extension, unused in this two-draw forward-only
followup; it is not silently described as byte-identical optimizer source.

## All observed outcomes

| Draw | Recorded aggregation | Cutoff | A | Q | R | Loss | Fresh replies | Measured model-call seconds |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | minimum-evidence | 3.5495080324 | 0 | 0 | 21 | 1.05 | 91 | 339.2590 |
| 1 | mean-evidence | 3.0804881948 | 2 | 7 | 21 | 0.55 | 89 | 319.3661 |

The recorded Gaussian latents are `0.13221368002505807` and
`-1.2637707408750682`; these are not the bounded cutoff values. Both worlds
retain five active authors. There are16 recorded sandbox calls, eight per world,
bound to their original source/image/context/result and committed native events.

The sum of native `llm_call_stats.elapsed_seconds` is **658.6251 seconds
(10.98 minutes)**. This is measured time inside model calls, not total experiment
wall time: parent audits, guards, checkpoints, sandbox execution and orchestration
are outside this counter.

## Interpretation and limits

The final corrected-control proposal can be sampled and executed in the original
researcher world without changing its source/graph/coordinate meanings. Its two
new native losses are now observed rather than left as a saved update. The
conditional sampler, proposal compatibility and actual forward outcomes are
independently tied together.

These two outcomes do **not** estimate a reliable expected loss or identify a
causal effect of the control-variate update. Historical v11 samples are parent
provenance/calibration, not a concurrent causal comparison group. No held-out
evaluation, superiority, variance reduction, useful institutional invention or
scientific value is established. Original v11 evidence is neither appended to
nor rewritten by this separate followup.

## Bound evidence

- Independent report content SHA256:
  `039ce8f7bbbd4a7186534849a010e6c983af74398fab8247dcb68746f5516b6a`.
- Followup raw inventory SHA256:
  `f5cf7069aac0472f52d2dadb7d83f5c769262d47a6d90c326d637de13c2c7736`.
- Final raw evidence content SHA256:
  `5d77f9555fe4aba1c97cedb0b37e45ade30224ea40acd7d2305e73bcf7a3b011`.
- Immutable parent audit file SHA256:
  `98bc7c3e4b2aa32fcedbe1f413c7311a2a71e5034824bb427f21eef8ea5f677d`.
- Immutable parent audit content SHA256:
  `0d75a366dc32b8f75dab96ca32d7daa90a91c6e98db140df28bbbc21d6547426`.
- Raw locator:
  `/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-control-followup-v12-a1`.

The machine-readable report retains exact draw/observation/run identities,
full final weights/definition, all native checkpoint and code receipts, response
counts, source proofs and per-file raw hashes.
