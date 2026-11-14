# Prospective capacity-only inspected CPU sharing, not relabeled old readiness

Observed hardware has18 physical/logical CPU cores and64GiB unified memory.
Aggregate383%/455% CPU represents fewer than five occupied cores, not whole-
machine saturation. The earlier250% admission ceiling is a conservative policy,
not an empirical capacity failure. Old resource rejections remain failed.

For this finite two-frame capacity diagnostic ONLY, declare a separate profile:
at least18 physical cores; at most600% aggregate CPU (six core equivalents);
at least38GiB free+inactive memory; no loaded Ollama model, unclassified Python
or model engine; two compatible observations30s apart, at most120s before run.
Inspected CPU-only jobs may continue. Their exact commands or narrowly named
CPU worker families, source-file hashes and RSS limits must be declared in a
sealed allowance file before observation. Stdin coordinators require PID and
start-time identity. This is scoped observation, not a GPU profiler, proof of
future inactivity, process isolation or an exclusive hardware/model lease.

The two calls retain v2's exact derived64k payloads,8192 output,10/900s HTTP,
2100s whole worker, one empty load plus two chat POSTs maximum, no retry,
truncation, action execution or scientific world. Shared CPU load can affect
latency; report actual calls, counts and timing as shared-host observations,
never a dedicated speed benchmark. A timeout/unknown still stops the worker
without another dispatch. No other process is paused, killed or modified.

The new resource record/schema/contract is not an old250% pass and does not
authorize the scientific14-world comparison. That stays at its testeda5be8d31
source, with actual request-bound calibration and separately declared fresh
resource conditions still required. No world, loss, seed, model weight or
scientific admission rule changes. Native/cold software proof is preserved;
v3 changes only capacity diagnostics/orchestration, not utopia runtime code.
