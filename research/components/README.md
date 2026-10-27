# System components

This directory is the forward location for independently replaceable science
system mechanisms such as evaluation, publication, funding, governance, and the
canonical event/replay interface.

The primary abstraction is the complete typed mechanism graph (`SystemSpec`),
not any one component API. Components may be present, absent, repeated, or
connected differently when allowed by their contracts.

The canonical event/replay sidecar and an Evaluation System API vertical slice
are integrated in `main`. The latter demonstrates one possible component
boundary; it does not yet alter simulator decisions or constitute the
whole-system abstraction.
