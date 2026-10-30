# Game UI: result-blind held-out relay v1

Status: implemented and locally verified on
`feature/game-ui-heldout-progress`.

## Outcome

NOCTILUCA now has a fourth district, the **Common-Split Relay**, for the
metric-conditioned study's common held-out execution. The screen makes the
experimental unit visible as three frozen systems evaluated under the same
five seeds. It shows orchestration progress, the current physical run,
elapsed time, median-based ETA, and technical failure state while keeping all
scientific results sealed.

The pixel-world metaphor is operational rather than decorative: each frozen
system is a habitat, each held-out run is a seed pod on a five-stop relay, and
the current physical attempt is a lit station. A separate technical-failure
bay prevents execution invalidity from being presented as a poor scientific
outcome. The system-comparison dock compares identity, conditioning LossSpec,
design fingerprint, freeze seal, and run state only.

## Two independently hashed inputs

The browser never opens the active experiment registry or raw outputs.

1. `held-out-progress.synthetic.json` uses the production monitor schema
   `scienceutopia.held-out-progress.v1` unchanged. It represents a snapshot
   produced from a synthetic UI-test registry and contains result-blind
   orchestration counts, active-run timing, health, ETA, and report gate.
2. `held-out-run-grid.synthetic.json` uses the separately labelled
   `scienceutopia.game-held-out-run-grid.synthetic.v1` presentation contract.
   It supplies the frozen-system identities and 3 × 5 status grid required by
   the visual slice. Its identities and states are invented test data.

Each document has an independent canonical SHA-256. The TypeScript adapter
verifies both before joining them, then requires matching study identity,
revision, observation time, counts, active run IDs, and technical-failure
ledger. A mismatch rejects the entire view.

## Fail-closed result boundary

The run-grid parser recursively rejects exact fields for loss values,
objective values, metric values, rank/ranking, model output, provisional
winner, winner, or outputs. The boundary also requires explicit false flags
for loss, held-out metric, and provisional-winner export. The page therefore
cannot render a provisional scientific comparison from an unfinished study.

A later verified adapter should join:

- frozen system identity and fingerprint from the immutable winner-freeze;
- status, active timing, ETA, and failures from the formal progress snapshot.

It must not include simulator output, loss, held-out metrics, ranking, or
post-evaluation policy decisions before the report gate. Completion unlocks a
separate cross-evaluation report, not a universal-winner label in this view.

## Verification

- formal progress snapshot hash: verified in browser and Vitest;
- synthetic run-grid hash: independently verified in browser and Vitest;
- result-field rejection, common seed split, count join, active-run join, and
  technical-failure separation: covered by contract tests;
- complete TypeScript/Vitest/Vite suite: passed;
- local browser review: 1440 × 1050 deterministic screenshot, reduced motion.

No Apple Python, simulator, Ollama, GPU, active experiment registry, raw
output, or experiment worktree was used or modified.
