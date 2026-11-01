# Scoped native institutional graph authoring v5

This is a syntax/compiler improvement for the **original researcher world**,
not a smaller replacement world or a new positive invention result. The two
failed v4 Qwen campaigns remain failed and unchanged. Native, freshly executed
objective observations must be reported separately from these software tests.

## What changes

`utopia.optimization.native_region_ir` exposes `boundary_contract`,
`region_ir_schema`, `lower_region_ir`, and `compile_region_ir`. A designer emits
`{rationale,nodes,exports}`. The node array is the designer's execution order.
Each node declares a local ID, arbitrary Python `step(context)`, JSON memory
schema, parameters, named inputs and named outputs. Output channels, artifact
types and payload schemas are explicit; new internal protocol schemas are legal.
Each input explicitly names its sources and its payload schema. There is no
algorithm catalog, prescribed rule or minimum count beyond one node.

Source references are `boundary:<alias>` and `node:<local-id>:<output-port>`.
For example, `boundary:world` addresses the actual recorded upstream world
output, while `node:commons:dossier` explicitly wires an earlier authored
node's `dossier` output. Every native exit must have an explicit `exports`
entry pointing to compatible authored output ports. The compiler does not fill
missing wires, invent algorithms, rewrite Python, invent identities, or supply
objective measurements.

The compiler mechanically namespaces local node IDs, so a local spelling such
as `world.review` cannot overwrite the retained host institution. Integer phases
are distributed strictly inside the native cut while preserving the selected
node order. Input channel/artifact type follows the explicitly selected source;
merging incompatible source types fails. Object-property order is normalized,
making a saved/sorted JSON manifest reconstruct the identical SystemSpec.
Input/output port IDs on one node still must be distinct because the native
SystemSpec currently uses a shared per-node port-ID namespace. This incidental
limitation is reported rather than repaired through a source transformation.

## Durable objective-conditioned proposer

`NativeRegionIRProposer(model, executor, removed_nodes, context_provider,
receipts, instructions='', max_attempts=3, max_tokens=4096)` has the controller
callback signature `(parent, history, index, loss_spec) -> patch`. It includes
the exact LossSpec, previous actual losses/measurements, actual native cut,
and explicitly lossy input examples in the prompt. Exact full native records,
not those prompt projections, drive isolated chronological probes.
The initial de-novo draft withholds original host source. Later revisions see
the exact executed generated incumbent's Python, ports, parameters, connections
and schedules alongside its feedback. The source-visibility policy is bound in
durable receipts; this is feedback-conditioned revision rather than independent
code regeneration conditioned only on numerical scores.
The last at most two generated candidates are also shown with their proposal
indices, exact regions and actual losses, including candidates that failed to
beat the incumbent. Older-source omission is explicit and source bytes are
never truncated. This preserves best-incumbent controller semantics without
discarding actionable feedback about worse-but-valid previous designs.

The first cut can replace `world.selection`; a later revision automatically
replaces all IDs of the incumbent `native_design_region`. Therefore new names,
node counts, intermediate protocols and wiring remain editable in every
iteration. Publication boundary identity/coverage and control-year validation
remain active even after the original `world.selection` ID no longer exists.
These are executable-domain validity checks, not quality, fairness, quota or
participation vetoes.

Each bounded draft persists its exact prompt/binding and generated IR before
container execution. Receipts bind the parent, full history, explicit loss,
runtime image, original native context bundles, format, settings and previous
receipt hash. Resume reuses the saved generated draft, reconstructs the same
patch, and refuses changed/tampered bindings. A process interruption during
probing does not consume another model query. Technical failures keep null
loss; passing a frozen-input probe is explicitly **not native evaluation**.

## Verification and remaining limits

Focused scripted tests cover free Python/new protocols, explicit graph
lowering, retained-host-name hygiene, missing/unknown/mistyped wires, durable
resume and repair chains, interruption recovery, and a second actual native
scripted-world revision whose invalid paper identities must be repaired.
These QA sources are developer-written fixtures, never evidence of Qwen's
ability to invent useful institutions.

The region still requires an annual zero-delay DAG cut with recorded Python
contexts for every removed node. Up to six authored nodes and bounded edges
are supported by the underlying compiler. Cross-year graph edges, arbitrary
new host domain consumers, whole-world pathwise differentiation and useful
automatic recursive improvement are not established by this change.
