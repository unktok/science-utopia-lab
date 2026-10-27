# Metric-Conditioned v1 initial-trajectory reuse audit

Date: 2026-10-27  
Experiment source commit: `9f9868d5bac631f6c7c373229d7807a26695a62f`  
Audit source state: `125bedf8f2c0f3dd2b2e3cba8a28494d3a1ed9f4`

## Decision

Do **not** reuse the nine initial design-seed trajectories across arms in the
currently initialized v1 campaign. Execute all 27 initial logical runs
independently.

Sharing a realized trajectory across LossSpecs is scientifically appropriate
for these byte-identical initial proposals: the simulator never reads the
LossSpec, and evaluating the same trajectory under three losses is a common
random-numbers design rather than extra replication. The prohibition is an
implementation and provenance decision. The current registry, output layout,
manifest contract, and evaluator do not distinguish a physical simulation
artifact from an arm-specific logical run.

This decision follows the preregistered fallback: the protocol authorizes
content-addressed reuse only after the complete immutable artifact and its hash
can be linked into every campaign record; otherwise each campaign runs
normally.

## Evidence inspected

The audit was read-only with respect to the experiment worktree and its three
registries.

- All three campaign snapshots identify source commit `9f9868d`.
- The registries contain 27 logical runs: three designs x three optimization
  seeds x three arms.
- Grouping by `(design_id, seed)` yields nine groups of exactly three rows.
- Within every group, `design_json`, fidelity, seed, model/backend, scientific
  CLI options, and the normalized producer command are identical.
- The only producer-command differences are `--run-id` and `--output-dir`.
- At audit time, one participation/review run had entered attempt 1; the other
  26 rows remained planned. No held-out seed was present.

The relevant contracts are implemented in:

- `utopia/optimization/harness.py`: `run_id`, `RunRegistry`,
  `manifest_status`, `execute_pending`, and `build_report`;
- `utopia/optimization/closed_loop.py`: arm-specific run planning and
  `observe_ready`;
- `utopia/optimization/objective_evaluator.py`: physical artifact lookup and
  derived-evaluation writeback;
- `utopia/analysis/release.py`: native manifest and checkpoint admission.

## Why filesystem linking or copying is unsafe

### Symlinking an arm-specific run directory

`manifest_status` would accept a linked complete manifest because it does not
check that the manifest's `experiment_id` equals the registry row's `run_id`.
Later stages are not alias-safe:

- `summarize_run` rejects the artifact with `Manifest experiment ID mismatch`;
- `write_evaluation` writes `objective_evaluation.json` through the logical
  path, which would mutate the shared source directory;
- multiple arms could overwrite the same derived file while labelling it with
  different logical run IDs;
- the checkpoint/replay layer explicitly rejects symlinks in replay outputs.

### Hardlinking or copying files

An unmodified copy retains the source `experiment_id`, command, `run_id`, and
absolute output paths, so native admission still fails. Rewriting those fields
creates a new manifest with a different hash and falsely makes a reused
artifact look independently produced. Hardlinks additionally make any
in-place derived write or later metadata update affect the source inode.

No current bundle receipt enumerates and hashes the complete required raw
artifact. `manifest_status` checks lifecycle status and selected integrity
reports, not artifact immutability or origin.

### Changing only registry status

The schema has no `reused` or `adopted` execution provenance. Calling
`RunRegistry.finish` on a planned, attempt-zero row can set `runs.status` to
`complete` while creating no `attempts` or `attempt_schedulers` row. Such a row
is indistinguishable in headline completion counts from an executed run but
has no process, command, wall-time, or source-artifact receipt. Direct SQL has
the same defect. This is not an acceptable provenance record.

## Minimum safe design for a later version

1. Define an execution identity independent of arm and filesystem location:
   source producer commit/code identity, normalized producer configuration,
   `SystemSpec` fingerprint/design JSON, fidelity, seed, model identity,
   dataset identity, and relevant runtime versions. Explicitly exclude only
   `run_id`, output paths, LossSpec, and optimizer/campaign identity.
2. Seal each completed physical trajectory with an immutable bundle receipt
   listing every admitted raw file and SHA-256. Derived evaluations must live
   outside the sealed bundle.
3. Add an `artifact_links` (or equivalent) registry relation containing the
   logical run ID, physical source run ID/root, execution-identity hash,
   bundle-receipt hash, source attempt/scheduler provenance, adoption tool
   version/commit, and adoption timestamp.
4. Add one transactional `adopt_artifact` API. It must accept only an
   attempt-zero planned target; verify a terminal valid source, normalized
   identity equality, all bundle hashes, and the absence of symlinks; then
   record adoption without fabricating an execution attempt.
5. Resolve physical artifacts read-only in `manifest_status`, `build_report`,
   `evaluate_run`, and `summarize_run`, while returning the logical run ID in
   arm reports. Never write arm-specific evaluation files into the physical
   artifact.
6. Report executed and adopted counts, wall time, failures, and source lineage
   separately. One physical trajectory must never be counted as three
   independent simulator executions.
7. Test tampered files, wrong seed/design/fidelity/commit/model, source failure,
   partial bundles, symlinks, adoption after an attempt, cross-arm evaluator
   write isolation, and restart/idempotency.

## Version and running-campaign impact

Implementing the above changes modifies optimizer/harness source and therefore
changes both the clean source commit and the campaign revision (the revision
hash includes `source_commit`). It cannot be installed into the active
commit-pinned worktree without invalidating its clean-source claim and making
the already-started run belong to a different controller revision.

Accordingly:

- v1 at commit `9f9868d` continues with independent execution;
- provenance-safe reuse should be introduced as a protocol/controller
  amendment (recommended `v1.1`) from a new clean commit and worktree;
- a v1.1 campaign must not silently adopt v1 artifacts unless its adoption
  contract explicitly supports cross-controller producer identities and proves
  that the simulator-producing code/configuration are equivalent. The simpler
  path is to use reuse only in a newly initialized campaign.

This affects compute cost, not the registered LossSpecs, held-out firewall, or
scientific question. V1 remains valid under its conservative 45-run
optimization budget.
