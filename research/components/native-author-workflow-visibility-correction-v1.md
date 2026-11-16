# Correct the author workflow's literal-document visibility mismatch

This is a prospective software repair, not a repaired scientific observation,
a new loss, proof of useful invention or an active experiment change.
[Sealed diagnosis/regressions](../results/native-author-workflow-visibility-correction-v1.json).

## Exact failure

V45 sends compact JSON and includes a whole document when it fits65536 UTF-8
bytes. Its inherited V44 workflow independently measured spaced JSON against
the same numeric cap. V45 corrected the displayed inclusion flag afterward,
but not the already computed phase. Thus a fully supplied document could
silently lose the implementation checkpoint after three successful inspections.

| Actual document | Compact/supplied bytes | Legacy/spaced bytes | Old checkpoint after3 reads |
| --- | ---: | ---: | --- |
| U zero parent | 61892 | 65479 | Implementation |
| C terminal parent | 62755 | 66342 | General, despite full document |
| U after literal feature write | 62032 | 65619 | General, despite full document |

The source write increases encoded document size by140 bytes and crosses the
legacy boundary without crossing the actual inclusion boundary. These are
complete original native SystemSpecs, not artificially small replacement worlds.

Inspection of33 completed actual backend calls across the first U/C and second
U author sessions finds14 affected general-phase calls. This proves the phase
inconsistency, not what the model would have written or what loss a correction
would produce. The14-call C and U sessions finish at a reserved submit checkpoint;
do not interpret that alone as a freely chosen strategic early stop.

The exact loss arithmetic/measurement definitions are present in all33 saved
wires, including that content utility uses an external fixed content panel and
does not use institution-written final_score. Recorded prompt counts32070–37382
leave the reserved8192 output tokens within65536; all inspected replies end in
stop. Counts are diagnostics, not proof of backend comprehension/no truncation.
The diagnosed bug is not missing metric text or corrupted returned read bytes.

## Prospective fix and boundaries

V45 computes whether it really supplies the whole document **before** calling
workflow, and passes that source-owned boolean into both phase selection and
the displayed flag. V44's default serializer/behavior is preserved when no
override is supplied. Truthy model values cannot select this internal override.
No body is shortened, string repaired, cap raised or institution made operative
by the host. The existing16-call limit, three-call submission reserve, allowed
implementation actions/explicit retention and archive retrieval remain unchanged.
This restores the declared technical workflow, not a new novelty/fitness gate.

The prospective contract now names
`matched-bounded-author-64k-v2-literal-visibility`, its exact literal byte cap and
the visibility rule. Old source-bound model certificates cannot authorize it.

## Verification actually done

- At025c83ca, original31754 reproduces2 failures/1 pass using the real terminal
  and post-write documents before the fix. The failing JUnit remains retained.
- At29f1c936, original18460 passes13 boundary cases. Original45740 passes83
  related cases, skips1 unavailable optional V43 archive and deselects1 historical
  case through the explicit selector. None of the three mandatory current
  native fixtures is optional/skipped.
- At9eae6cb6, original62286 passes84 with the same skip/deselection after the
  prospective contract is named.
- At195739f6, original22641 passes87 with the same skip/deselection. Three
  added cases run the actual staged generator, saved backend-wire construction,
  original-format journals, cold author replay and transport audit over each
  complete real document. The model replies are SCRIPTED; no real model/image,
  generated code or native simulation is executed. Real sandbox image identities
  in the fixture documents remain unchanged, not weakened to fit a mock.

Coverage includes exact65536/65537 UTF-8 boundaries, non-ASCII bytes, body omission,
legacy defaults, read reset after a real edit and reserved submission phases.
This is not full native/public/real-backend proof of the corrected source.
Fresh source/model/backend-bound readiness and the appropriate idle-window
integration proof remain necessary before any new corrected real campaign.

## Interpretation of the ongoing experiment

Scientific705b5259 and its three continuation sources remain pinned/unchanged.
It still uses context-v1; no old loss, candidate, status, raw text or failed slot
is rewritten/refilled. Valid measured native outcomes stay valid observations.
But the old author pipeline is not a clean isolated objective/method comparison:
parent/edited document size also changed its allowed-tool schedule. Do not infer
intrinsic designer inability, clean free-versus-numeric superiority/absence of
superiority, or useful benefit of the fix. Keep it as a source-specific
exploratory result with this interface limitation explicitly reported.

[Fixture provenance/data](../../tests/fixtures/native_author_context_boundary_v1/README.md),
[JUnit records](../data/native-author-workflow-visibility-v1/README.md),
[initial12 actual outcomes and next own-feedback wire](../results/native-priority-initial-half-and-first-own-feedback-wire-v1.json),
[publication decision requirements](../publication/native-priority-visibility-correction-plan-v1.md).
