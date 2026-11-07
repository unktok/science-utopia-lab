# Prospective required-output explanation correction

During V1, efficiency-loss G0 completes source authoring but its native execution
raises`GraphRuntimeError: 'world.selection' did not emit required output 'decisions'`.
Inspect the exact existing `_validate_result`: a required output must emit at
least one envelope on each invocation. An empty list is legal only on an
optional output. The author-facing ABI lists the`required` flag but did not
explain its cardinality; a non-veto schema notice also said empty lists remained
legal without this qualification. This is an incomplete/misleading explanation,
not a newly introduced scientific criterion or a demonstrated sole cause of
the model's generated-code mistake.

In a separate feature worktree, clarify that unchanged runtime rule in the
shared literal code contract and the notice. No runtime check, port flag,
decision, source, score or active protocol is modified. The rule is generic,
not a supplied review policy. Optional empty outputs remain legal; satisfying
cardinality does not establish receiver-protocol validity. Direct runtime and
bounded planning-frame tests prevent future prose/runtime mismatch.

The ongoing comparison remains at2e375c2 for all8 slots. No failure is repaired
or replaced. This later source needs fresh calibration before future generation;
passing software tests is not proof that a model will follow the clarified ABI.
