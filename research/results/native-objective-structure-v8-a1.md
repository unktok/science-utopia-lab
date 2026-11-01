# Native objective/structure v8 — attempt a1 audit

Attempt `a1` is a frozen, aborted technical-preflight attempt. It is **not** a
completed optimization run and contains no native simulation outcome.

## Audited accounting

- Frozen source: `425ec10396b17df85efdff20bb063b20c33886e5`.
- Planned native-world budget: 8; committed draws: 0; completed worlds: 0.
- Physical world directories, response caches, and researcher-model replies: 0.
- Both objective arms recorded one generation-0 vocabulary failure. Each has
  `ValueError: design patch schema/parent/operations mismatch`, a null loss,
  zero draws, and zero observations.
- Each arm's generation-1 request was still awaiting external consumption when
  the attempt was frozen. It is preserved as pending rather than treated as a
  result.
- The audit itself made no model calls and executed no generated source.

The postmortem found that JavaScript serialization normalized an integral
floating-point value from `1.0` to `1`. Because the generated patch embeds and
binds the parent system exactly, this changed its parent fingerprint from the
authored value beginning `88912a72` to the host value beginning `af6228`.
The host compiler correctly rejected the mismatch before a native world or
researcher-model request could start.

## Interpretation boundary

The two generation failures are failed vocabulary-compilation events, not four
fabricated failed draws. There is no numerical objective observation, selected
system, cross-objective comparison, held-out result, or improvement claim.
Consequently, `a1` must not appear in an objective loss path as a penalty or as
an empirical zero.

A later attempt may be created through an explicit pre-inference protocol
amendment while preserving this attempt. Because `a1` produced zero native
outcomes, such an amendment cannot be conditioned on simulation outcomes. It
must retain the same frozen objective definitions and the original maximum of
eight actual worlds for the new attempt, and it must not overwrite these raw
requests, responses, or source manifests.

## Evidence binding

The compact machine receipt is
[`native-objective-structure-v8-a1.json`](native-objective-structure-v8-a1.json).
It binds all 16 immutable raw files by path and SHA-256:

- raw inventory: `57e9b23e744edfe8523e1594d89636c59db1b8661e6098848a98b60f2758ac37`
- compact receipt: `ed69a1d68809daf2e7b9923d8a502c52112b3ba410844912cc438303ab389ad8`

The raw output remains outside this repository at
`/Users/shiro/unktok/dev/science-utopia-lab-experiments/native-objective-structure-v8-a1/outputs/native-objective-structure-v8`.
The compact receipt deliberately omits large generated manifests and system
payloads; their exact files remain covered by the raw inventory hashes.
