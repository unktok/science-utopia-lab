import { canonicalHash, stableStringify } from "./hash";

export type RunStatus = "planned" | "running" | "complete" | "failed";
export type ExecutionKind = "physical" | "adopted" | "unmaterialized";

export interface MissionSeed {
  seed: number;
  status: RunStatus;
  execution_kind: ExecutionKind;
  attempt: number;
  max_attempts: number;
  started_utc: string | null;
  finished_utc: string | null;
  wall_seconds: number | null;
  physical_run_id: string | null;
}

export interface MissionCandidate {
  proposal_index: number;
  suggestion_id: string;
  design_id: string;
  phase: string;
  status: RunStatus;
  seeds: MissionSeed[];
}

export interface MissionArm {
  campaign_id: string;
  revision: string;
  state_updated_utc: string;
  loss_spec: {
    id: string;
    version: string;
    direction: string;
    label: string;
    interpretation: string;
    prohibited_claims: string[];
  };
  budget: { used: number; maximum: number; optimization_seeds: number };
  winner: { status: "not_frozen"; design_id: null };
  candidates: MissionCandidate[];
  registry_projection_sha256: string;
}

export interface MissionBundle {
  schema_version: "scienceutopia.optimization-mission-control.v1";
  truth_status: "verified_snapshot" | "synthetic";
  source_kind: "read_only_metric_conditioned_registry_snapshot" | "synthetic_optimization_mission_fixture";
  disclosure: string;
  observed_at_utc: string;
  snapshot_hash: string;
  study: {
    id: string;
    version: string;
    goal: string;
    decision_policy: string;
    arms: number;
    candidate_capacity: number;
    logical_run_capacity: number;
  };
  workflow: Array<{ id: string; label: string; status: "running" | "pending" | "locked" | "complete" }>;
  progress: {
    logical_registered: number;
    logical_capacity: number;
    status_counts: Record<RunStatus, number>;
    execution_counts: { physical_complete: number; physical_running: number; adopted_complete: number };
  };
  arms: MissionArm[];
  winner_freeze: { status: "not_frozen"; frozen_arms: 0; required_arms: number };
  held_out: { status: "locked"; reason: string; seeds: number[]; registry_exists: false; registered_runs: 0 };
  runtime: { model: string; backend: string; batch_size: number; max_attempts: number; workers: number; fidelity: string };
  provenance: {
    source_commit: string;
    source_tree_clean: true;
    study_spec_sha256: string;
    registry_projection_sha256: string;
    source_files: Array<{ role: string; path: string; sha256: string }>;
  };
}

const object = (value: unknown, path: string): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  return value as Record<string, unknown>;
};
const array = (value: unknown, path: string): unknown[] => {
  if (!Array.isArray(value)) throw new Error(`${path} must be an array`);
  return value;
};
const string = (value: unknown, path: string): string => {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${path} must be a non-empty string`);
  return value;
};
const number = (value: unknown, path: string): number => {
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${path} must be a finite number`);
  return value;
};
const status = (value: unknown, path: string): RunStatus => {
  if (!(["planned", "running", "complete", "failed"] as unknown[]).includes(value)) throw new Error(`${path} has an unknown status`);
  return value as RunStatus;
};

export function parseMissionBundle(value: unknown): MissionBundle {
  const root = object(value, "mission");
  if (root.schema_version !== "scienceutopia.optimization-mission-control.v1") throw new Error("unsupported mission-control schema");
  const synthetic = root.truth_status === "synthetic";
  if (!synthetic && root.truth_status !== "verified_snapshot") throw new Error("mission truth status is invalid");
  if (synthetic !== (root.source_kind === "synthetic_optimization_mission_fixture")) throw new Error("mission truth/source boundary is inconsistent");
  if (!synthetic && root.source_kind !== "read_only_metric_conditioned_registry_snapshot") throw new Error("verified mission must use the registry snapshot adapter");
  const arms = array(root.arms, "mission.arms").map((item, armIndex) => {
    const path = `mission.arms[${armIndex}]`;
    const arm = object(item, path);
    const loss = object(arm.loss_spec, `${path}.loss_spec`);
    const budget = object(arm.budget, `${path}.budget`);
    const winner = object(arm.winner, `${path}.winner`);
    if (winner.status !== "not_frozen" || winner.design_id !== null) throw new Error(`${path} may not expose an unfrozen winner`);
    const candidates = array(arm.candidates, `${path}.candidates`).map((candidateItem, candidateIndex) => {
      const candidatePath = `${path}.candidates[${candidateIndex}]`;
      const candidate = object(candidateItem, candidatePath);
      const seeds = array(candidate.seeds, `${candidatePath}.seeds`).map((seedItem, seedIndex) => {
        const seedPath = `${candidatePath}.seeds[${seedIndex}]`;
        const seed = object(seedItem, seedPath);
        const execution = string(seed.execution_kind, `${seedPath}.execution_kind`);
        if (!["physical", "adopted", "unmaterialized"].includes(execution)) throw new Error(`${seedPath}.execution_kind is unknown`);
        return {
          seed: number(seed.seed, `${seedPath}.seed`), status: status(seed.status, `${seedPath}.status`), execution_kind: execution as ExecutionKind,
          attempt: number(seed.attempt, `${seedPath}.attempt`), max_attempts: number(seed.max_attempts, `${seedPath}.max_attempts`),
          started_utc: seed.started_utc === null ? null : string(seed.started_utc, `${seedPath}.started_utc`),
          finished_utc: seed.finished_utc === null ? null : string(seed.finished_utc, `${seedPath}.finished_utc`),
          wall_seconds: seed.wall_seconds === null ? null : number(seed.wall_seconds, `${seedPath}.wall_seconds`),
          physical_run_id: seed.physical_run_id === null ? null : string(seed.physical_run_id, `${seedPath}.physical_run_id`),
        };
      });
      return {
        proposal_index: number(candidate.proposal_index, `${candidatePath}.proposal_index`), suggestion_id: string(candidate.suggestion_id, `${candidatePath}.suggestion_id`),
        design_id: string(candidate.design_id, `${candidatePath}.design_id`), phase: string(candidate.phase, `${candidatePath}.phase`), status: status(candidate.status, `${candidatePath}.status`), seeds,
      };
    });
    const parsedBudget = { used: number(budget.used, `${path}.budget.used`), maximum: number(budget.maximum, `${path}.budget.maximum`), optimization_seeds: number(budget.optimization_seeds, `${path}.budget.optimization_seeds`) };
    if (candidates.length !== parsedBudget.used || candidates.length > parsedBudget.maximum) throw new Error(`${path} budget does not match candidates`);
    return {
      campaign_id: string(arm.campaign_id, `${path}.campaign_id`), revision: string(arm.revision, `${path}.revision`), state_updated_utc: string(arm.state_updated_utc, `${path}.state_updated_utc`),
      loss_spec: { id: string(loss.id, `${path}.loss_spec.id`), version: string(loss.version, `${path}.loss_spec.version`), direction: string(loss.direction, `${path}.loss_spec.direction`), label: string(loss.label, `${path}.loss_spec.label`), interpretation: string(loss.interpretation, `${path}.loss_spec.interpretation`), prohibited_claims: array(loss.prohibited_claims, `${path}.loss_spec.prohibited_claims`).map((claim, index) => string(claim, `${path}.loss_spec.prohibited_claims[${index}]`)) },
      budget: parsedBudget, winner: { status: "not_frozen" as const, design_id: null }, candidates,
      registry_projection_sha256: string(arm.registry_projection_sha256, `${path}.registry_projection_sha256`),
    };
  });
  if (arms.length !== 3) throw new Error("mission requires exactly three LossSpec arms");
  const study = object(root.study, "mission.study");
  const progress = object(root.progress, "mission.progress");
  const counts = object(progress.status_counts, "mission.progress.status_counts");
  const executions = object(progress.execution_counts, "mission.progress.execution_counts");
  const held = object(root.held_out, "mission.held_out");
  if (held.status !== "locked" || held.registry_exists !== false || held.registered_runs !== 0) throw new Error("held-out firewall must remain locked in mission-control v1");
  const freeze = object(root.winner_freeze, "mission.winner_freeze");
  if (freeze.status !== "not_frozen" || freeze.frozen_arms !== 0) throw new Error("mission-control v1 refuses a partial or inferred winner freeze");
  const runtime = object(root.runtime, "mission.runtime");
  const provenance = object(root.provenance, "mission.provenance");
  if (provenance.source_tree_clean !== true) throw new Error("mission source must be commit-pinned and clean");
  return {
    schema_version: "scienceutopia.optimization-mission-control.v1", truth_status: synthetic ? "synthetic" : "verified_snapshot",
    source_kind: synthetic ? "synthetic_optimization_mission_fixture" : "read_only_metric_conditioned_registry_snapshot",
    disclosure: string(root.disclosure, "mission.disclosure"), observed_at_utc: string(root.observed_at_utc, "mission.observed_at_utc"), snapshot_hash: string(root.snapshot_hash, "mission.snapshot_hash"),
    study: { id: string(study.id, "mission.study.id"), version: string(study.version, "mission.study.version"), goal: string(study.goal, "mission.study.goal"), decision_policy: string(study.decision_policy, "mission.study.decision_policy"), arms: number(study.arms, "mission.study.arms"), candidate_capacity: number(study.candidate_capacity, "mission.study.candidate_capacity"), logical_run_capacity: number(study.logical_run_capacity, "mission.study.logical_run_capacity") },
    workflow: array(root.workflow, "mission.workflow").map((item, index) => { const row = object(item, `mission.workflow[${index}]`); const stageStatus = string(row.status, `mission.workflow[${index}].status`); if (!["running", "pending", "locked", "complete"].includes(stageStatus)) throw new Error("unknown workflow status"); return { id: string(row.id, `mission.workflow[${index}].id`), label: string(row.label, `mission.workflow[${index}].label`), status: stageStatus as "running" | "pending" | "locked" | "complete" }; }),
    progress: { logical_registered: number(progress.logical_registered, "mission.progress.logical_registered"), logical_capacity: number(progress.logical_capacity, "mission.progress.logical_capacity"), status_counts: { planned: number(counts.planned, "counts.planned"), running: number(counts.running, "counts.running"), complete: number(counts.complete, "counts.complete"), failed: number(counts.failed, "counts.failed") }, execution_counts: { physical_complete: number(executions.physical_complete, "executions.physical_complete"), physical_running: number(executions.physical_running, "executions.physical_running"), adopted_complete: number(executions.adopted_complete, "executions.adopted_complete") } },
    arms,
    winner_freeze: { status: "not_frozen", frozen_arms: 0, required_arms: number(freeze.required_arms, "mission.winner_freeze.required_arms") },
    held_out: { status: "locked", reason: string(held.reason, "mission.held_out.reason"), seeds: array(held.seeds, "mission.held_out.seeds").map((seed, index) => number(seed, `mission.held_out.seeds[${index}]`)), registry_exists: false, registered_runs: 0 },
    runtime: { model: string(runtime.model, "mission.runtime.model"), backend: string(runtime.backend, "mission.runtime.backend"), batch_size: number(runtime.batch_size, "mission.runtime.batch_size"), max_attempts: number(runtime.max_attempts, "mission.runtime.max_attempts"), workers: number(runtime.workers, "mission.runtime.workers"), fidelity: string(runtime.fidelity, "mission.runtime.fidelity") },
    provenance: { source_commit: string(provenance.source_commit, "mission.provenance.source_commit"), source_tree_clean: true, study_spec_sha256: string(provenance.study_spec_sha256, "mission.provenance.study_spec_sha256"), registry_projection_sha256: string(provenance.registry_projection_sha256, "mission.provenance.registry_projection_sha256"), source_files: array(provenance.source_files, "mission.provenance.source_files").map((item, index) => { const file = object(item, `source_files[${index}]`); return { role: string(file.role, "source_file.role"), path: string(file.path, "source_file.path"), sha256: string(file.sha256, "source_file.sha256") }; }) },
  };
}

export async function verifyMissionBundle(bundle: MissionBundle): Promise<void> {
  const unhashed = JSON.parse(stableStringify(bundle)) as Record<string, unknown>;
  delete unhashed.snapshot_hash;
  if (await canonicalHash(unhashed) !== bundle.snapshot_hash) throw new Error("mission snapshot SHA-256 mismatch");
  const optimizationSeeds = new Set(bundle.arms[0]!.candidates.flatMap((candidate) => candidate.seeds.map((seed) => seed.seed)));
  for (const arm of bundle.arms) {
    for (const candidate of arm.candidates) {
      if (candidate.seeds.length !== arm.budget.optimization_seeds) throw new Error(`${arm.campaign_id}:${candidate.design_id} seed grid is incomplete`);
      if (candidate.seeds.some((seed) => bundle.held_out.seeds.includes(seed.seed))) throw new Error("held-out seed leaked into development registry");
      if (candidate.seeds.some((seed) => !optimizationSeeds.has(seed.seed))) throw new Error("optimization seed sets differ across arms");
    }
  }
}
