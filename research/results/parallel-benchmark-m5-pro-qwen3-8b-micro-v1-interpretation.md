# M5 Pro / Qwen3-8B parallel microbenchmark v1

The short endpoint benchmark found essentially no aggregate throughput scaling
from four logical workers on the current single local Ollama endpoint.

| Workers | Mean makespan | Speedup | Parallel efficiency | Generated tok/s | Mean request latency | Latency multiplier | Errors / retries |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 7.688 s | 1.000x | 1.000 | 47.356 | 0.961 s | 1.000x | 0 / 0 |
| 2 | 7.621 s | 1.009x | 0.504 | 47.767 | 1.775 s | 1.847x | 0 / 0 |
| 4 | 7.567 s | 1.016x | 0.254 | 48.105 | 3.004 s | 3.126x | 0 / 0 |

The measurement used three repetitions with rotated order. Every worker count
processed the same four logical runs and eight timed structured-output requests
per repetition. There were no request failures or retries. The Ollama process
peaked at about 11.6 GB RSS for every setting, and no trial increased swap use.
The host already had about 3.8 GB of swap in use, which cannot be attributed to
this benchmark.

The literal fastest mean makespan was workers=4, but the difference from
workers=1 was only 1.6%, while average request latency more than tripled. The
engineering inference is that this single Ollama/Qwen3-8B endpoint is effectively
serializing the tested workload. Therefore a four-worker campaign should not be
budgeted as a fourfold speedup on this setup.

This is endpoint evidence, not the final full-simulator decision. The next
capacity check is a commit-pinned harness smoke comparison using identical runs
and fresh registries for workers 1, 2, and 4. A smoke run has historically taken
tens of minutes, so that check was intentionally not started as part of this
few-minute benchmark. Independent model replicas or a backend with continuous
batching remain the more plausible route to material multi-run throughput.

Machine-readable summary:
[`parallel-benchmark-m5-pro-qwen3-8b-micro-v1.json`](parallel-benchmark-m5-pro-qwen3-8b-micro-v1.json).

The ignored raw report hashes are fixed in that summary. These results describe
execution capacity only; they are not an optimization loss, scientific metric,
or policy constraint.
