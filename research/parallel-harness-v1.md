# Bounded Parallel Harness v1

The optimization harness can launch independent simulation runs concurrently
against one shared Ollama endpoint:

    python -m utopia.optimization.harness \
      --study research/specs/example.json run --workers 2

The default remains workers=1. In that mode commands, shared cache behavior,
combined attempt-N.log output, registry states, retries, and returned counts
remain sequentially compatible with the prior harness.

## Scheduling boundary

Only the harness is parallel. The simulator, scientific configuration, model
requests, metrics, and study specifications are unchanged.

One parent scheduler owns the SQLite connection and starts at most N child run
processes. A host-local file lease prevents two parent schedulers from operating
the same registry. Each claim is also a conditional SQLite transaction, so a
planned or failed run can create at most one next attempt.

Every attempt records:

- scheduler id and parent PID
- configured worker limit and assigned slot
- subprocess PID
- effective command hash
- stdout and stderr paths
- canonical run output root
- private cache root

The status and report commands expose this scheduler provenance.

## Output and failure isolation

Parallel attempts write separate attempt-N.stdout.log and
attempt-N.stderr.log files under their run-specific registry log directory.
The existing attempt-N.log records the command and scheduler routing.

Science outputs remain separated by the existing safe run id:

    OUTPUT_ROOT/checkpoints/RUN_ID
    OUTPUT_ROOT/docs/RUN_ID
    OUTPUT_ROOT/logs/RUN_ID

A non-zero process or invalid manifest fails only that run. Other active and
queued runs continue. Ctrl-C terminates active children, marks their attempts
failed, and records an interrupted scheduler. A hard-killed parent leaves
running rows; the next invocation recovers them as failed attempts and retries
from their existing checkpoints when attempts remain.

## Shared Ollama and cache safety

workers greater than one currently requires:

- api_backend=ollama
- one model and endpoint shared by every command
- a warm shared RAG cache containing documents and embedding artifacts

Warm the cache with workers=1 before parallel execution. A cold parallel launch
fails before claiming any run. Treat the warm source as quiescent while a
parallel campaign seeds private caches; do not run a separate cache-warming
process against it concurrently.

Each run receives a private cache root seeded from the shared warm cache.
Read-mostly RAG artifacts use hard links where the filesystem permits it;
their writers use atomic replacement. Mutable keyword and novelty embedding
caches are copied, because they have whole-file writers and must never share an
inode between concurrent runs. Retries reuse the same private cache.

The warm check proves that some RAG artifacts exist, not that every requested
fidelity identity is present. A missing identity may be rebuilt inside each
private cache safely, but loses the intended startup benefit.

## Capacity interpretation

The worker limit bounds run subprocesses, not individual inference requests.
With batch_size B and workers N, the Ollama server may see up to roughly N times
B queued requests. Ollama or the GPU may serialize them, so workers=2 is not a
promise of twofold speed. Benchmark 1, 2, and then 4 workers while recording
wall time, token throughput, memory pressure, failures, and output stability.

Worker count is provenance because server-side scheduling can change latency
and may change generated output on backends that are not fully deterministic.
Do not mix worker counts inside a comparison campaign without treating the
scheduler setting as part of its execution context.
