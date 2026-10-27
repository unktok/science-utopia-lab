# Research campaign workflow

Software development and scientific evidence use related but different
lifecycles. A passing feature test does not make a research result, and an
interesting run does not retroactively define a valid protocol.

## Before execution

1. Define the mutable `SystemSpec` subspace.
2. Freeze a versioned `LossSpec` for optimization seeds.
3. Define technical `ValiditySpec` checks.
4. Reserve disjoint optimization, selection, and held-out evaluation seeds.
5. Declare budget, fidelity, stopping conditions, and optimizer state format.
6. Declare held-out evaluation metrics and any optional decision policy.
7. Merge the protocol and create an annotated protocol tag.

## During execution

1. Run from a clean commit-pinned experiment worktree.
2. Persist every optimizer suggestion before dispatch.
3. Keep run registries, output roots, and mutable caches isolated.
4. Preserve technically valid poor outcomes.
5. Quarantine incomplete or corrupt observations without inventing penalty
   losses unless the `LossSpec` explicitly defines that behavior.
6. Do not alter loss, seeds, simulator, evaluator, or stopping rule after
   seeing results.

## After optimization

1. Freeze the selected candidate.
2. Evaluate it on untouched seeds and declared stress scenarios.
3. Report effect sizes, uncertainty, resource cost, slices, and failure modes.
4. Apply a decision policy only if one was explicitly versioned.
5. Commit compact results, hashes, manifests, and interpretation.
6. Create an annotated result tag after verification.

## Parallel development

Long runs and development use separate worktrees. The game UI, graph runtime,
and analysis tooling may progress while a campaign runs, but no code change may
enter the frozen experiment worktree. A changed simulator or producer
configuration creates a new campaign revision.

The authoritative research taxonomy and historical mapping are in
[`research/INDEX.md`](../research/INDEX.md).
