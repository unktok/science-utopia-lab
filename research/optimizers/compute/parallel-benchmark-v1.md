# Parallel benchmark protocol v1

## Question

On one Apple M5 Pro host with 64 GB unified memory and one Ollama/Qwen3-8B
endpoint, what happens when the bounded campaign scheduler allows 1, 2, or 4
independent logical runs to make requests concurrently?

This is an engineering-capacity question. It is not a loss, a held-out science
metric, or a policy constraint. The benchmark reports observations and does not
automatically admit or reject a scientific system.

## What is measured

The fixed request suite is replayed with the same number of logical runs and
requests at every worker count. The runner records:

- total makespan and speedup relative to workers=1;
- aggregate generated-token and request throughput;
- per-run and per-request latency;
- request failures and retries;
- sampled host memory, swap use, and Ollama-process RSS;
- model identity, Ollama version and loaded-model state;
- the allowlisted client-side `OLLAMA_*` settings that can affect scheduling;
- source commit, dirty state, machine identity, and protocol hash.

The committed short protocol uses four logical runs with two structured-output
requests each, repeated three times with rotated worker-count order. It is a
serving microbenchmark, not a shortened Science Utopia simulation. It isolates
whether a single Ollama endpoint gains aggregate throughput from concurrency
without spending hours on a full campaign.

## Three evidence stages

1. **Synthetic runner test.** Fixed sleeps must show bounded 1/2/4 overlap and
   a valid report. This verifies the measurement machinery, not Ollama.
2. **Live endpoint microbenchmark.** Run the committed fixed request suite.
   This measures server concurrency, latency inflation, errors, and memory
   pressure in minutes.
3. **Representative harness smoke benchmark.** Before a long campaign, create
   fresh, commit-pinned registries for each worker count and run the same smoke
   fidelity and logical-run count through `utopia.optimization.harness`. Compare
   manifest integrity, output hashes where determinism is expected, attempt
   failures, makespan, and the resource fields above.

Stage 2 can identify an obviously serialized, unstable, or memory-pressured
workers=4 configuration. It cannot establish end-to-end campaign speed by
itself because simulator request shape, cache copies, and request bursts differ.

## Commands

Validate and show the exact request budget without contacting Ollama:

```bash
.venv/bin/python -m utopia.optimization.parallel_benchmark \
  --protocol research/protocols/templates/parallel-benchmark-v1.json \
  --dry-run
```

Run the short live benchmark. Raw reports stay under ignored `outputs/`:

```bash
.venv/bin/python -m utopia.optimization.parallel_benchmark \
  --protocol research/protocols/templates/parallel-benchmark-v1.json \
  --json-output outputs/benchmarks/local-m5-pro-qwen3-8b-micro-v1.json \
  --markdown-output outputs/benchmarks/local-m5-pro-qwen3-8b-micro-v1.generated.md
```

Validate the JSON against
[`schemas/parallel-benchmark-report-v1.schema.json`](schemas/parallel-benchmark-report-v1.schema.json).
If the evidence becomes part of a research decision, commit only a compact,
reviewed result and artifact manifest; keep request-level raw output outside
Git.

## Interpretation

The report identifies the fastest tested configuration with zero request
errors, but this is deliberately not an automatic adoption gate. Inspect all of
the following together:

- speedup and parallel efficiency;
- inflation of per-request and per-run latency;
- any retry or error;
- swap growth, compression, and peak Ollama RSS;
- end-to-end harness smoke results and output integrity.

The protocol uses three repetitions; the runner rotates worker-count order
across repetitions to expose thermal/order effects. Include stage 3 before a
multi-day campaign decision. Record
`OLLAMA_NUM_PARALLEL` explicitly when controlling the server; absence in the
client environment is recorded as unknown rather than treated as a default.

## Safety and comparability

- Do not benchmark in a worktree running a real campaign.
- Do not change the model, quantization, prompt suite, generation cap, backend,
  or Ollama scheduling settings between worker counts.
- Do not mix results from different protocol hashes.
- Warm model loading is excluded by loading the model before timed trials; the
  report still records server-reported load time per request.
- The bounded harness still requires a warm shared RAG cache and per-run private
  mutable caches. This microbenchmark does not weaken those requirements.
