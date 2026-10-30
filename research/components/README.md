# System components

This directory is the forward location for independently replaceable science
system mechanisms such as evaluation, publication, funding, governance, and the
canonical event/replay interface.

The primary abstraction is the complete typed mechanism graph (`SystemSpec`),
not any one component API. Components may be present, absent, repeated, or
connected differently when allowed by their contracts.

The canonical event/replay sidecar, an Evaluation System API vertical slice,
and the first deterministic whole-graph runtime are integrated foundations.
The evaluation API demonstrates one possible component boundary; it is not the
root abstraction. The generic runtime is documented in
[`mechanism-graph-runtime-v1.md`](mechanism-graph-runtime-v1.md). The first
joint structural space over evaluation, publication, funding, government, and
communication is documented in
[`whole-system-structural-blackbox-v1.md`](whole-system-structural-blackbox-v1.md).
