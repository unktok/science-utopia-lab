# ADR 0008: Measure endpoint throughput before parallel campaigns

Date: 2026-10-27
Status: accepted

## Context

The campaign harness supports four safe worker processes, but all workers on the
local machine share one Ollama/Qwen3-8B/Metal endpoint. Scheduler concurrency is
not necessarily inference concurrency.

A fixed short benchmark measured only 1.016x aggregate speedup at four workers,
while mean request latency increased 3.13x. All requests completed without
errors, retries, or new swap use.

## Decision

- Use `workers=1` for conservative local campaign runtime estimates.
- Treat `workers=2` and `workers=4` as operational capabilities, not speedups.
- Before a long campaign, benchmark the exact endpoint, model, quantization,
  context, and representative request workload.
- For material parallel throughput, prefer independent model replicas or a
  server that demonstrates useful continuous batching.
- Run a commit-pinned full-simulator smoke comparison before making the final
  local campaign scheduling choice.

## Consequences

The prior ideal four-worker estimates remain mathematical lower bounds, not
plans for this Mac. A loaned multi-GPU machine must be measured rather than
assigned a speedup from GPU count alone.
