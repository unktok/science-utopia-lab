# Recorded output compatibility with tensor consumers

A returned component output does not establish that its connected consumer can
read it. The optional diagnostic compares actual recorded output frames with
the current direct tensor consumer's literal payload path and declared shape.
It shares the native adapter's payload conversion, empty-batch reshape and
input validation. It never executes the tensor body, changes source or loss,
or vetoes an explicit submission.

## What is checked

One known immediate edge, a unique producer/consumer, one recorded frame and
a declared tensor binding are required for a comparison. Fan-in, delayed
delivery, absent/multiple frames and ambiguous ownership remain unassessed.
Compatible input is not a statement about matrix operations, other inputs,
record alignment, state, schedules or a complete native trajectory.

The explicit prospective fixture-bank field
`post_edit_tensor_delivery_scope: recorded-direct-tensor-inputs-v1` enables it.
An absent field keeps the prior feedback scope; an unknown value is rejected
before dispatch. The complete request contract binds the diagnostic and native
adapter source hashes. The same bank reconstructs calibration, worker, role
factory, outer replay and cold replay; there is no second budget constant.
No probe or model allowance is increased.

Immediate feedback and the version-specific persistent view retain the
diagnostic across reads. Its document hash binds the consumer snapshot, not
only the producer source. Editing the consumer makes an old observation
explicitly stale, even when the producer artifact is unchanged. This avoids
presenting an older compatibility result as proof for new wiring or contracts.

## Actual retained failure

The61a1753 objective study's first U candidate adds a third feature column but
keeps the two-column consumer. Eight original component probes return. Four
belong to the final producer artifact; their recorded inputs yield:

| Saved fixture year | Observed shape after native conversion | Consumer declaration | Diagnostic |
| --- | --- | --- | --- |
| 1 | 0 by 2 | dynamic rows by 2 | Compatible recorded input |
| 2 | 2 by 3 | dynamic rows by 2 | Incompatible recorded input |
| 3 | 3 by 3 | dynamic rows by 2 | Incompatible recorded input |
| 4 | 2 by 3 | dynamic rows by 2 | Incompatible recorded input |

The empty case is not evidence that a later nonempty input will work. The
other four original probes remain in the report as different-artifact records;
their old returned status is not reassigned to the final code.

Two actual readouts at6574fe2 first replay original authoring under unchanged
scientific61a1753, then perform the separate recorded-output comparison. Both
report and manifest match byte for byte. The closed U/g0 record and its entire
authoring archive remain unchanged while the writer continues other slots.
[Portable evidence and exact limits](../data/native-tensor-delivery-diagnostic-v1/README.md).
This is not a new native-world audit or a diagnosis sent to that original
designer. No repair or optimization benefit is inferred.

## Verification and current use

The scripted calibration-to-outer-replay and persistent-feedback suite passes
86 checks at86e4ea0, including legacy8 and explicit64 budgets with and without
the optional diagnostic. Native/tensor/hybrid regressions pass53 with one
container-access skip. The original six-year world, recurrent derivative,
projection, fresh reaction and cold reload check is then actually run using
the existing no-network/no-host-mount container and passes separately in29.83s,
without model inference or an image download. Counts overlap; they are not
independent experiments.

The first readout test has a collection error from a helper named `test`;
renaming the helper corrects it. The first actual reader then stops on a valid
null finish result. Its correction adds a complete double-export regression,
not a synthetic replacement for the original record. The final16 reader and
input-diagnostic checks pass5.43s. All failed receipts are retained.

The active scientific study remains frozen61a1753, with this diagnostic disabled.
Actual-model readiness for a future enabled scope must be freshly calibrated
before dispatch. Scripted interface success and retrospective detection are
not proof that the designer will fix the error or improve an objective.
