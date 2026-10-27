# Compute and parallelization plan

Date: 2026-10-26
Updated: 2026-10-27

## Measured local baseline

The first paired system comparison is the planning baseline:

- machine: Apple M5 Pro, 64 GB unified memory
- model/backend: Qwen3-8B / Ollama / Metal
- workload: 10 complete four-year runs, two designs by five paired seeds
- elapsed wall time: 51,854.5 seconds (14.40 hours)
- LLM elapsed time: 51,740.8 seconds (99.78% of wall time)
- prompts: 3,310
- prompt tokens: 3,535,303
- completion tokens: 1,978,849
- effective completion throughput: 38.24 completion tokens/second

The cache is already warm, so GPU inference is the dominant remaining runtime.
At the same fidelity, one design evaluated over five seeds costs about 7.20 hours,
and eight designs cost about 57.6 hours when executed serially.

The later confirmation campaign was slower and is the conservative planning
baseline for the next campaign:

- baseline design, five seeds: 31,839.1 seconds (8.84 hours)
- candidate design, five seeds: 29,314.1 seconds (8.14 hours)
- total: 61,153.2 seconds (16.99 hours), or 1.70 hours per run

Until a representative benchmark supersedes it, use
`serial hours = 1.70 × designs × seeds`. The two completed ten-run campaigns
together consumed 31.39 hours of wall time.

| Designs | Seeds per design | Runs | Conservative serial estimate |
|---:|---:|---:|---:|
| 5 | 5 | 25 | 42.5 h (1.8 d) |
| 8 | 3 | 24 | 40.8 h (1.7 d) |
| 8 | 5 | 40 | 68.0 h (2.8 d) |
| 16 | 5 | 80 | 136.0 h (5.7 d) |

Four workers would reduce 40 runs to about 17 hours only under ideal scaling.
The local Ollama/Metal endpoint has not established that scaling; benchmark
`workers=1,2,4` on the same representative workload and report aggregate
throughput, per-run latency, failures, and peak memory before scheduling the
optimization campaign.

## Throughput-to-runtime conversion

The following is a planning calculation, not a hardware guarantee. It assumes
the same output-length distribution and uses the measured effective completion
throughput. The ranges include a roughly 20% operational allowance.

| Effective aggregate completion throughput | Speedup over local | 2 designs x 5 seeds | 8 designs x 5 seeds |
|---:|---:|---:|---:|
| 38 tok/s | 1.0x | 14.4 h | 57.6 h |
| 80 tok/s | 2.1x | 6.9-8.3 h | 27.5-33.0 h |
| 150 tok/s | 3.9x | 3.7-4.4 h | 14.7-17.6 h |
| 300 tok/s | 7.8x | 1.8-2.2 h | 7.3-8.8 h |
| 600 tok/s | 15.7x | 0.9-1.1 h | 3.7-4.4 h |

Qwen's published Qwen3-8B benchmark on one NVIDIA H20 reports 81.73 total
tokens/s for BF16 and about 144-150 tokens/s for AWQ/FP8 at batch size one for
the shortest input condition. That benchmark counts prompt and generated tokens
together and uses a different workload, so it is evidence for a plausible tier,
not a direct prediction for ScienceUtopia.

Sources:

- Qwen3-8B model card: <https://huggingface.co/Qwen/Qwen3-8B>
- Qwen3 speed benchmark: <https://github.com/QwenLM/Qwen3/blob/main/docs/source/getting_started/speed_benchmark.md>
- vLLM benchmark CLI: <https://docs.vllm.ai/en/latest/benchmarking/cli/>

## Hardware request tiers

Qwen3-8B has 8.2 billion parameters. Its BF16 weights alone are approximately
16.4 GB. Qwen's batch-one benchmark observed about 15.9 GB at minimal input and
16.8 GB with a 6,144-token input under Transformers. Therefore 24 GB is a useful
minimum for one worker, while 32/48/80 GB gives safer KV-cache and batching
headroom.

| Tier | Example GPU | VRAM | Conservative planning target | Expected 8-design wall time |
|---|---|---:|---:|---:|
| useful minimum | RTX 4090 or A10-class | 24 GB | 60-100 effective completion tok/s | 22-37 h |
| preferred workstation | RTX 5090 | 32 GB | 90-160 tok/s | 14-25 h |
| preferred server | L40S / RTX 6000 Ada | 48 GB | 100-200 tok/s | 11-22 h |
| fast server | A100 80 GB / H100 80 GB | 80 GB | 120-300 tok/s | 7-18 h |
| multi-GPU throughput | 2-4 suitable GPUs, one replica per GPU | 2-4x device VRAM | 300-900 aggregate tok/s | 2.5-7.5 h |

These ranges are deliberately broad. GPU generation, power limit, backend,
precision, prompt length, batching, and sampling all matter. More VRAM mainly
buys concurrency and KV-cache capacity; it does not by itself guarantee faster
single-request decoding. NVIDIA lists 32 GB for RTX 5090, 48 GB for L40S, and
80 GB for H100 SXM.

Sources:

- RTX 5090 specifications: <https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/>
- L40S specifications: <https://www.nvidia.com/en-sg/data-center/l40s/>
- H100 specifications: <https://www.nvidia.com/en-gb/data-center/h100/>

Recommended host request:

- Linux x86_64 with SSH access and permission to run containers
- one NVIDIA GPU with at least 24 GB VRAM; 32-48 GB preferred
- 64 GB host RAM minimum
- 100 GB free NVMe storage minimum
- current NVIDIA driver/CUDA stack compatible with vLLM or SGLang
- uninterrupted allocation for 24 hours for a single fast GPU, or 8-12 hours
  for a multi-GPU throughput test

Before committing a campaign, replay a fixed representative ScienceUtopia
request set and record output throughput, TTFT, failures, model revision,
precision, backend, and sampling configuration. `vllm bench serve` can provide
the standard serving metrics, but the acceptance test is the project workload.

Changing Ollama/Metal to vLLM or SGLang/CUDA, or changing quantization, creates
a new producer configuration. Do not mix it into an existing campaign. Freeze
the backend and model revision for the whole campaign and run a calibration
comparison before interpreting institutional effects.

## Parallel experiment and development layout

Long-running experiments and code development must use separate git worktrees.
The experiment worktree is pinned to a clean source commit and receives no code
changes while a campaign is running.

```text
frozen experiment worktree
  optimizer / simulator runs only

development worktrees
  canonical event and replay contract
  game viewer
  Evaluation System API
  mechanism graph / science-system structure
```

Use independent model replicas per GPU and distribute seeds or designs across
them. For an 8B model that fits on one GPU, data-parallel campaign workers are
normally preferable to splitting one inference request across multiple GPUs.
Bounded parallel workers and isolated per-run outputs are implemented on the
`track/parallel-harness` branch. They remain outside `main` pending interruption
safety review and a `workers=1,2,4` benchmark. A shared endpoint and cache still
mean that worker count is not the same as inference throughput; no multi-GPU or
four-worker speedup is claimed yet.

The first shared development boundary is a read-only canonical event envelope
and a deterministic one-year replay fixture. After that boundary is frozen:

1. Game UI consumes event JSON only and can be built without GPU or LLM calls.
2. Evaluation System API is developed behind a legacy adapter and tested in
   shadow mode before it changes simulator decisions.
3. Science-system structure starts as a finite typed mechanism graph with a
   legacy graph compiler, rather than unconstrained generated code.

Agents working on these tracks must not edit the frozen experiment worktree.
Shared integration files are changed only by the coordinating agent after the
track-specific tests pass.
