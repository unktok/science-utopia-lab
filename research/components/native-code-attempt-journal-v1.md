# Exact inputs for unsuccessful native code calls

The native code recorder now writes a separate durable intent before delegating
to the existing container executor. It retains the exact artifact, input context
and source/system/run binding when code raises, not only when it returns a valid
result. This supports a future designer self-test loop without repairing model
code or turning a partial component test into a native scientific loss.

## Journal and replay

`code-contexts.jsonl` keeps its existing successful-bundle schema and bytes.
The prospective `code-contexts.jsonl.attempts.jsonl` contains hashed intent and
returned/raised events. Each append is flushed and fsynced. A recording failure
before delegation stops the call. The nonce uses OS randomness, not the native
world's seeded Python random stream. No attempt ID is supplied to scientists.

Cold replay checks journal hashes, exact bindings, event lineage, and a bijection
between returned events and validated legacy execution bundles. Raised calls
retain their original error and exact input; pending calls stay pending. Neither
means a timed-out container completed or was successfully cancelled. Missing
terminal events are never reconstructed from a legacy bundle. Input artifacts
and contexts for unsuccessful calls remain data, not certified valid contracts.

The physical audit projects returned/raised/pending counts when the new journal
exists. Historical absence is unknown, not zero. Completed-source receipts and
actual native checkpoints remain necessary for successful scientific runs.
Extra diagnostic recording does not impose a new policy merit constraint.

## Scope

The live fixed-candidate evaluation stays at frozenf1f8ddf and does not use this
change. The historical671436a failures still lack the triggering failed-call
input records; they are not retroactively filled. This journal alone does not
give the model a self-test tool, execute a new candidate, or establish that code
generation or optimization improved. Tool integration and an independently
declared finite authoring protocol remain next work.
