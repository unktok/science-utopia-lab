# Wrapped activity adoption validation v7

`native_migration.native_execution_nodes(spec)` exposes actual executable
contracts, including the single delegate of each `native.process.activity.v1`
wrapper. It checks canonical nested fields, reserved ports, wrapper/delegate
transport compatibility and completion/control types. It never imports or
executes authored source or fills missing semantic wires.

Migration program validation now traverses these contracts for free Python,
tensor programs and LLM schemas. A wrapped-only Python design contributes its
exact image digest to the existing executor-resolution path. An image change
therefore rebuilds the preview executor before adoption; portable cold bootstrap
does not retain an old-image executor. All direct and wrapped code must share
the one declared pinned image.

Reconciliation validates the chosen nested delegate memory and every retained
queued code/tensor/control input before a receipt is committed. Code schemas
are safety-checked before JSON-Schema evaluation. Tensor memory names, shapes,
finite values, transport paths and queued numeric input shapes are checked
without running the program. Process invocation counters must be nonnegative
integers. Wrapped code retains the actual input ABI's universal empty first-call
state; this does not synthesize initialized memory or relax output validation.
Existing top-level code migration state validation remains strict.

`validate_native_execution_checkpoint(spec, graph)` is a reusable pure validation
API. Portable bootstrap calls it on the current graph, including post-adoption
years, rather than assuming the old migration target graph validates later
memories/queues. Incompatible pending messages require an explicit discard with
reason; their old bytes remain in the migration receipt. Invalid source, state,
queue or image fails before the existing society is changed.

Verification distinguishes graph/image-resolution unit fixtures from actual
native software QA. The latter adds a wrapped-only Python institution at the
real year-1 saved boundary, commits adoption, cold-restarts from the ORIGINAL
founding design and completes all six original scientific years. Ten real
isolated calls in years2–6 preserve nested state and deliver actual messages to
subsequent researcher prompts. Only HTTP/corpus are scripted. This is not live
LLM invention, scientific benefit, or a new native domain law.
