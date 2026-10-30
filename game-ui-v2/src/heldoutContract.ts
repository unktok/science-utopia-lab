import { canonicalHash, stableStringify } from "./hash";

export type HeldoutRunStatus = "planned" | "running" | "complete" | "technical_failed";

export interface HeldoutProgressSnapshot {
  schema: "scienceutopia.held-out-progress.v1";
  truth_status: "verified_progress_snapshot";
  disclosure: string;
  observed_at_utc: string;
  study: { id: string; revision: string };
  registry: { path: string; registered_runs: number; expected_runs: number; projection_sha256: string };
  progress: {
    counts: { planned: number; running: number; complete: number; failed: number };
    completion_fraction: number;
    retryable_failures: number;
    terminal_failures: number;
    active_runs: Array<{ run_id: string; seed: number; attempt: number; max_attempts: number; started_utc: string; elapsed_seconds: number }>;
    duration_summary: null | { count: number; mean_seconds: number; median_seconds: number; minimum_seconds: number; maximum_seconds: number };
    eta: null | { method: "completed_run_median"; remaining_seconds: number; estimated_completion_utc: string };
  };
  health: { stalled: boolean; stale_after_hours: number; stale_run_ids: string[]; failures: Array<{ run_id: string; seed: number; attempt: number; max_attempts: number; terminal: boolean; error: string | null }> };
  gate: { ready_for_report: boolean; next_action: "continue-evaluation" | "investigate-stall" | "report-evaluation" };
  snapshot_sha256: string;
}

export interface HeldoutRun {
  run_id: string;
  seed: number;
  status: HeldoutRunStatus;
  elapsed_seconds: number | null;
  wall_seconds: number | null;
  attempt: number;
  failure_id: string | null;
}

export interface FrozenSystem {
  system_id: string;
  label: string;
  loss_spec_id: string;
  loss_condition: string;
  design_fingerprint: string;
  freeze_status: "sealed";
  freeze_id: string;
  asset: string;
  runs: HeldoutRun[];
}

export interface FrozenSystemGrid {
  schema: "scienceutopia.game-held-out-run-grid.synthetic.v1";
  truth_status: "synthetic";
  disclosure: string;
  observed_at_utc: string;
  study: { id: string; revision: string; system_count: 3; seeds_per_system: 5; total_runs: 15 };
  systems: FrozenSystem[];
  technical_failures: Array<{ id: string; run_id: string; system_id: string; seed: number; category: string; retryable: boolean }>;
  boundary: { result_visibility: "sealed_until_phase_complete"; loss_values_exported: false; heldout_metrics_exported: false; provisional_winner_exported: false; statement: string };
  provenance: { fixture_revision: string; input_mode: "versioned_portable_snapshot"; live_registry_access: false };
  snapshot_sha256: string;
}

export interface HeldoutOpsBundle { progress: HeldoutProgressSnapshot; grid: FrozenSystemGrid }

const forbiddenResultKeys = new Set(["loss", "objective_value", "objective_values", "metric", "metrics", "metric_values", "rank", "ranking", "provisional_winner", "winner", "model_output", "outputs"]);
function rejectResultFields(value: unknown, path = "grid"): void {
  if (Array.isArray(value)) return value.forEach((item, index) => rejectResultFields(item, `${path}[${index}]`));
  if (!value || typeof value !== "object") return;
  for (const [key, item] of Object.entries(value as Record<string, unknown>)) {
    if (forbiddenResultKeys.has(key)) throw new Error(`${path}.${key} is forbidden in the result-blind run-grid schema`);
    rejectResultFields(item, `${path}.${key}`);
  }
}

const object = (value: unknown, path: string): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  return value as Record<string, unknown>;
};
const array = (value: unknown, path: string): unknown[] => {
  if (!Array.isArray(value)) throw new Error(`${path} must be an array`);
  return value;
};
const text = (value: unknown, path: string): string => {
  if (typeof value !== "string" || !value) throw new Error(`${path} must be a non-empty string`);
  return value;
};
const count = (value: unknown, path: string): number => {
  if (!Number.isInteger(value) || (value as number) < 0) throw new Error(`${path} must be a non-negative integer`);
  return value as number;
};
const finite = (value: unknown, path: string): number => {
  if (typeof value !== "number" || !Number.isFinite(value) || value < 0) throw new Error(`${path} must be a non-negative finite number`);
  return value;
};
const nullableCount = (value: unknown, path: string): number | null => value === null ? null : count(value, path);
const boolean = (value: unknown, path: string): boolean => {
  if (typeof value !== "boolean") throw new Error(`${path} must be boolean`);
  return value;
};
const stringArray = (value: unknown, path: string): string[] => array(value, path).map((item, index) => text(item, `${path}[${index}]`));
const runStatus = (value: unknown, path: string): HeldoutRunStatus => {
  if (!["planned", "running", "complete", "technical_failed"].includes(String(value))) throw new Error(`${path} has an unknown status`);
  return value as HeldoutRunStatus;
};

export function parseHeldoutProgressSnapshot(value: unknown): HeldoutProgressSnapshot {
  const root = object(value, "progress");
  if (root.schema !== "scienceutopia.held-out-progress.v1") throw new Error("unsupported formal held-out progress schema");
  if (root.truth_status !== "verified_progress_snapshot") throw new Error("formal progress snapshot truth status is invalid");
  const study = object(root.study, "progress.study");
  const registry = object(root.registry, "progress.registry");
  const progress = object(root.progress, "progress.progress");
  const counts = object(progress.counts, "progress.progress.counts");
  const parsedCounts = { planned: count(counts.planned, "counts.planned"), running: count(counts.running, "counts.running"), complete: count(counts.complete, "counts.complete"), failed: count(counts.failed, "counts.failed") };
  const registered = count(registry.registered_runs, "progress.registry.registered_runs");
  const expected = count(registry.expected_runs, "progress.registry.expected_runs");
  if (registered !== expected || Object.values(parsedCounts).reduce((sum, item) => sum + item, 0) !== registered) throw new Error("formal progress counts disagree with the registry size");
  const activeRuns = array(progress.active_runs, "progress.progress.active_runs").map((item, index) => {
    const row = object(item, `active_runs[${index}]`);
    return { run_id: text(row.run_id, "active.run_id"), seed: count(row.seed, "active.seed"), attempt: count(row.attempt, "active.attempt"), max_attempts: count(row.max_attempts, "active.max_attempts"), started_utc: text(row.started_utc, "active.started_utc"), elapsed_seconds: finite(row.elapsed_seconds, "active.elapsed_seconds") };
  });
  if (activeRuns.length !== parsedCounts.running) throw new Error("formal active run list disagrees with running count");
  const duration = progress.duration_summary === null ? null : object(progress.duration_summary, "progress.progress.duration_summary");
  const eta = progress.eta === null ? null : object(progress.eta, "progress.progress.eta");
  if (eta && eta.method !== "completed_run_median") throw new Error("unknown ETA method");
  const health = object(root.health, "progress.health");
  const failures = array(health.failures, "progress.health.failures").map((item, index) => {
    const row = object(item, `progress.health.failures[${index}]`);
    return { run_id: text(row.run_id, "failure.run_id"), seed: count(row.seed, "failure.seed"), attempt: count(row.attempt, "failure.attempt"), max_attempts: count(row.max_attempts, "failure.max_attempts"), terminal: boolean(row.terminal, "failure.terminal"), error: row.error === null ? null : text(row.error, "failure.error") };
  });
  if (failures.length !== parsedCounts.failed) throw new Error("formal failure ledger disagrees with failed count");
  const gate = object(root.gate, "progress.gate");
  const nextAction = text(gate.next_action, "progress.gate.next_action");
  if (!["continue-evaluation", "investigate-stall", "report-evaluation"].includes(nextAction)) throw new Error("unknown progress gate action");
  return {
    schema: "scienceutopia.held-out-progress.v1", truth_status: "verified_progress_snapshot", disclosure: text(root.disclosure, "progress.disclosure"), observed_at_utc: text(root.observed_at_utc, "progress.observed_at_utc"),
    study: { id: text(study.id, "progress.study.id"), revision: text(study.revision, "progress.study.revision") },
    registry: { path: text(registry.path, "progress.registry.path"), registered_runs: registered, expected_runs: expected, projection_sha256: text(registry.projection_sha256, "progress.registry.projection_sha256") },
    progress: { counts: parsedCounts, completion_fraction: finite(progress.completion_fraction, "progress.completion_fraction"), retryable_failures: count(progress.retryable_failures, "progress.retryable_failures"), terminal_failures: count(progress.terminal_failures, "progress.terminal_failures"), active_runs: activeRuns, duration_summary: duration ? { count: count(duration.count, "duration.count"), mean_seconds: finite(duration.mean_seconds, "duration.mean_seconds"), median_seconds: finite(duration.median_seconds, "duration.median_seconds"), minimum_seconds: finite(duration.minimum_seconds, "duration.minimum_seconds"), maximum_seconds: finite(duration.maximum_seconds, "duration.maximum_seconds") } : null, eta: eta ? { method: "completed_run_median", remaining_seconds: finite(eta.remaining_seconds, "eta.remaining_seconds"), estimated_completion_utc: text(eta.estimated_completion_utc, "eta.estimated_completion_utc") } : null },
    health: { stalled: boolean(health.stalled, "health.stalled"), stale_after_hours: finite(health.stale_after_hours, "health.stale_after_hours"), stale_run_ids: stringArray(health.stale_run_ids, "health.stale_run_ids"), failures },
    gate: { ready_for_report: boolean(gate.ready_for_report, "gate.ready_for_report"), next_action: nextAction as HeldoutProgressSnapshot["gate"]["next_action"] }, snapshot_sha256: text(root.snapshot_sha256, "progress.snapshot_sha256"),
  };
}

export function parseFrozenSystemGrid(value: unknown): FrozenSystemGrid {
  rejectResultFields(value);
  const root = object(value, "grid");
  if (root.schema !== "scienceutopia.game-held-out-run-grid.synthetic.v1" || root.truth_status !== "synthetic") throw new Error("unsupported or unlabelled synthetic run-grid schema");
  const study = object(root.study, "grid.study");
  if (study.system_count !== 3 || study.seeds_per_system !== 5 || study.total_runs !== 15) throw new Error("run-grid shape must be 3 systems × 5 seeds");
  const systems = array(root.systems, "grid.systems").map((item, systemIndex) => {
    const path = `grid.systems[${systemIndex}]`;
    const system = object(item, path);
    if (system.freeze_status !== "sealed") throw new Error(`${path} must be frozen before held-out execution`);
    const runs = array(system.runs, `${path}.runs`).map((runItem, runIndex) => {
      const runPath = `${path}.runs[${runIndex}]`;
      const run = object(runItem, runPath);
      const status = runStatus(run.status, `${runPath}.status`);
      const failureId = run.failure_id === null ? null : text(run.failure_id, `${runPath}.failure_id`);
      if ((status === "technical_failed") !== Boolean(failureId)) throw new Error(`${runPath} failure identity disagrees with status`);
      return { run_id: text(run.run_id, `${runPath}.run_id`), seed: count(run.seed, `${runPath}.seed`), status, elapsed_seconds: nullableCount(run.elapsed_seconds, `${runPath}.elapsed_seconds`), wall_seconds: nullableCount(run.wall_seconds, `${runPath}.wall_seconds`), attempt: count(run.attempt, `${runPath}.attempt`), failure_id: failureId };
    });
    if (runs.length !== 5 || new Set(runs.map((run) => run.seed)).size !== 5) throw new Error(`${path} must contain five unique held-out seeds`);
    return { system_id: text(system.system_id, `${path}.system_id`), label: text(system.label, `${path}.label`), loss_spec_id: text(system.loss_spec_id, `${path}.loss_spec_id`), loss_condition: text(system.loss_condition, `${path}.loss_condition`), design_fingerprint: text(system.design_fingerprint, `${path}.design_fingerprint`), freeze_status: "sealed" as const, freeze_id: text(system.freeze_id, `${path}.freeze_id`), asset: text(system.asset, `${path}.asset`), runs };
  });
  if (systems.length !== 3 || new Set(systems.map((system) => system.system_id)).size !== 3) throw new Error("run-grid requires exactly three unique frozen systems");
  const seedSet = systems[0]!.runs.map((run) => run.seed).sort((a, b) => a - b).join(",");
  if (systems.some((system) => system.runs.map((run) => run.seed).sort((a, b) => a - b).join(",") !== seedSet)) throw new Error("all frozen systems must use the identical held-out split");
  const failures = array(root.technical_failures, "grid.technical_failures").map((item, index) => {
    const row = object(item, `grid.technical_failures[${index}]`);
    return { id: text(row.id, "failure.id"), run_id: text(row.run_id, "failure.run_id"), system_id: text(row.system_id, "failure.system_id"), seed: count(row.seed, "failure.seed"), category: text(row.category, "failure.category"), retryable: boolean(row.retryable, "failure.retryable") };
  });
  const boundary = object(root.boundary, "grid.boundary");
  if (boundary.result_visibility !== "sealed_until_phase_complete" || boundary.loss_values_exported !== false || boundary.heldout_metrics_exported !== false || boundary.provisional_winner_exported !== false) throw new Error("result boundary is not fail-closed");
  const provenance = object(root.provenance, "grid.provenance");
  if (provenance.input_mode !== "versioned_portable_snapshot" || provenance.live_registry_access !== false) throw new Error("run-grid input must be a versioned portable snapshot without live registry access");
  return {
    schema: "scienceutopia.game-held-out-run-grid.synthetic.v1", truth_status: "synthetic", disclosure: text(root.disclosure, "grid.disclosure"), observed_at_utc: text(root.observed_at_utc, "grid.observed_at_utc"),
    study: { id: text(study.id, "grid.study.id"), revision: text(study.revision, "grid.study.revision"), system_count: 3, seeds_per_system: 5, total_runs: 15 }, systems, technical_failures: failures,
    boundary: { result_visibility: "sealed_until_phase_complete", loss_values_exported: false, heldout_metrics_exported: false, provisional_winner_exported: false, statement: text(boundary.statement, "grid.boundary.statement") },
    provenance: { fixture_revision: text(provenance.fixture_revision, "grid.provenance.fixture_revision"), input_mode: "versioned_portable_snapshot", live_registry_access: false }, snapshot_sha256: text(root.snapshot_sha256, "grid.snapshot_sha256"),
  };
}

async function verifyHash(value: Record<string, unknown>, key: string, claimed: string, label: string): Promise<void> {
  const unsigned = JSON.parse(stableStringify(value)) as Record<string, unknown>;
  delete unsigned[key];
  if (await canonicalHash(unsigned) !== claimed) throw new Error(`${label} SHA-256 mismatch`);
}
export async function verifyHeldoutProgressSnapshot(snapshot: HeldoutProgressSnapshot): Promise<void> {
  await verifyHash(snapshot as unknown as Record<string, unknown>, "snapshot_sha256", snapshot.snapshot_sha256, "formal held-out progress snapshot");
}
export async function verifyFrozenSystemGrid(grid: FrozenSystemGrid): Promise<void> {
  await verifyHash(grid as unknown as Record<string, unknown>, "snapshot_sha256", grid.snapshot_sha256, "synthetic run-grid snapshot");
}

export function joinHeldoutOps(progress: HeldoutProgressSnapshot, grid: FrozenSystemGrid): HeldoutOpsBundle {
  if (progress.study.id !== grid.study.id || progress.study.revision !== grid.study.revision || progress.observed_at_utc !== grid.observed_at_utc) throw new Error("formal progress and synthetic run-grid identities do not match");
  const gridRuns = grid.systems.flatMap((system) => system.runs);
  const gridCounts = gridRuns.reduce<Record<HeldoutRunStatus, number>>((totals, run) => ({ ...totals, [run.status]: totals[run.status] + 1 }), { planned: 0, running: 0, complete: 0, technical_failed: 0 });
  if (progress.progress.counts.planned !== gridCounts.planned || progress.progress.counts.running !== gridCounts.running || progress.progress.counts.complete !== gridCounts.complete || progress.progress.counts.failed !== gridCounts.technical_failed) throw new Error("formal progress counts disagree with the synthetic run-grid");
  const activeIds = new Set(progress.progress.active_runs.map((run) => run.run_id));
  if (gridRuns.filter((run) => run.status === "running").some((run) => !activeIds.has(run.run_id)) || activeIds.size !== gridCounts.running) throw new Error("formal active runs disagree with the synthetic run-grid");
  const gridFailureIds = new Set(grid.technical_failures.map((failure) => failure.run_id));
  if (progress.health.failures.some((failure) => !gridFailureIds.has(failure.run_id)) || gridFailureIds.size !== progress.progress.counts.failed) throw new Error("formal failures disagree with the synthetic failure ledger");
  return { progress, grid };
}
