# Conditional payload notices identify the archived native type failure

The new static feedback detects the payload-schema mistake in V17 a2 without
changing candidate eligibility or archived outcomes. The original two-objective
measured-feedback goal remains unmet. This result uses no new model calls,
scientific worlds or generated-source execution.

## Archived candidate results

The [original a2 audit](native-closed-loop-v17-a2.json) binds all 141 raw files
to actual source `22617b5a8bd41b8ca45bcad57fcc7a386678c691`. The new analysis
at `b31cf7446b1bbfee9b51a4fca183fae48515d8f5` inspects both candidate documents:

| Archived candidate | Conditional notice |
| --- | --- |
| Throughput G0, exact parent | None |
| Reviewed-production G1, changed `scores` schema | `world.selection` input payload excludes object at `/mechanisms/7/parameters/code_artifact/inputs/scores` |

The second candidate declares `type:array`, while the existing ABI delivers
each record's payload as an object. The schema describes one payload, not the
outer list of records. Its actual native execution previously failed on an
object containing `records` and `values`; that failure and its costs remain
unchanged. This analysis predicts the conditional type mismatch from the
archived document. It does not rerun the world or show that an author repairs it.

## Why this is a warning rather than a gate

An empty input/output record list does not validate any payload and remains
legal. Rejecting every non-object port schema would therefore remove existing
executable designs. The implementation adds information to draft summaries
and validation results, without changing their validity or authored candidate
system. Runtime provenance hashes still identify the new implementation.
It never wraps an array, supplies a missing field or changes an authored value.
State notices similarly describe the condition in which code is invoked and
returns object state; dormant mechanisms are not automatically rejected.

Only explicit top-level `type` declarations in the current version-one code
ABI are covered. Nested arrays in an object and unions permitting objects do
not warn. Implicit/composed schemas, unknown implementations/versions and
future factor draws are not solved by this check. Prompt summaries include
at most eight notices with explicit total and omitted counts. New parameters
are not generically labelled unused: code receives extra parameters through
`context.parameters` and can consume them.

## Trusted instructions were already in the actual SYSTEM messages

All 47 archived designer POSTs contain the trusted authoring protocol, execution
ABI and objective directive in SYSTEM. The original source-matched audit already
verifies those archived wire requests; this analysis records their role coverage.
The hypothesis that these runs lack SYSTEM instructions is contradicted by
the actual requests. This does not establish model compliance or identify the
cause of its invalid field/path proposals. No repeated instruction-placement
probe is needed to test a defect already absent from these messages.

## Verification and source boundary

The two read-only analyses agree byte-for-byte and each verifies all 141 raw
file hashes before and after inspection. The [generated record](native-contract-notices-v18.json)
binds the old actual source, new analysis source, helper/ABI/script hashes,
every candidate input and all 47 original POST envelopes. Its content hash is
`082e2398c48003089bf93ae135d6a775d041f7f38fe285f41794f95719925395`.

At the new source, 206 related SCRIPTED tests pass in 24.94s. They cover
conditional payload failures, legal empty ports, warning-only finishes,
process wrappers, exact pointer escaping, bounded notices, version boundaries,
role attribution, missing POST coverage and concurrent raw changes, alongside
existing author/compiler/audit contracts. JUnit file
`outputs/native-contract-notices-v18/source-b31cf74.xml` has SHA256
`4278147981554eb43c5f93f885f20d1d0b9aa1bfec601ec99a0cfc984f32935f`.
This focused scope overlaps earlier tests and is not a new full-suite result.

Old runtime-bound certificates are correctly rejected before backend access.
The new feedback requires a fresh actual calibration and prospective protocol
before any future production generation. No such inference is authorized by
this [zero-inference protocol](../protocols/campaigns/native-contract-notices-v18.md).
The separate external-Codex designer choice is still unanswered and unlaunched.
No scientific improvement, reliable autonomous redesign or completed native
feedback loop is claimed here.
