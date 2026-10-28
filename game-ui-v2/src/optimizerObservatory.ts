import type { MissionBundle, RunStatus } from "./missionContract";

export interface ObservatorySeedRun {
  seed: number;
  status: RunStatus;
  execution_kind: "physical" | "adopted" | "unmaterialized";
  score: { status: "not_observed"; value: null; reason: string };
}

export interface ObservatoryDesign {
  proposal_index: number;
  design_id: string;
  status: RunStatus;
  seeds: ObservatorySeedRun[];
}

export interface ObservatoryArm {
  campaign_id: string;
  loss_spec_id: string;
  loss_label: string;
  interpretation: string;
  direction: string;
  designs: ObservatoryDesign[];
}

export interface OptimizerObservatoryProjection {
  truth_status: "verified_snapshot" | "synthetic";
  source_kind: MissionBundle["source_kind"];
  observed_at_utc: string;
  arms: ObservatoryArm[];
  metric_conditioning: {
    optimized_variable: "system_design";
    conditioning_variable: "loss_spec";
    registered_cross_arm_divergence: "observed" | "not_observed";
    note: string;
  };
  score_export: { status: "not_observed"; note: string };
  winner_freeze: { status: "not_frozen"; frozen_arms: 0; required_arms: number };
  report: { status: "locked" | "pending" | "running" | "complete"; note: string };
  provenance: MissionBundle["provenance"] & { snapshot_hash: string };
  presentation: {
    truth_status: "presentation_only";
    fields: readonly ["district_layout", "facility_shape", "packet_routes", "packet_animation", "colour", "narrative_labels"];
  };
}

export function buildOptimizerObservatoryProjection(bundle: MissionBundle): OptimizerObservatoryProjection {
  const arms = bundle.arms.map((arm) => ({
    campaign_id: arm.campaign_id,
    loss_spec_id: arm.loss_spec.id,
    loss_label: arm.loss_spec.label,
    interpretation: arm.loss_spec.interpretation,
    direction: arm.loss_spec.direction,
    designs: arm.candidates.map((candidate) => ({
      proposal_index: candidate.proposal_index,
      design_id: candidate.design_id,
      status: candidate.status,
      seeds: candidate.seeds.map((seed) => ({
        seed: seed.seed,
        status: seed.status,
        execution_kind: seed.execution_kind,
        score: {
          status: "not_observed" as const,
          value: null,
          reason: "Objective values are not exported by the result-blind mission snapshot.",
        },
      })),
    })),
  }));
  const proposalIndexes = new Set(arms.flatMap((arm) => arm.designs.map((design) => design.proposal_index)));
  const divergence = [...proposalIndexes].some((index) => new Set(arms.map((arm) => arm.designs.find((design) => design.proposal_index === index)?.design_id).filter(Boolean)).size > 1);
  const reportStage = bundle.workflow.find((stage) => stage.id === "report");
  return {
    truth_status: bundle.truth_status,
    source_kind: bundle.source_kind,
    observed_at_utc: bundle.observed_at_utc,
    arms,
    metric_conditioning: {
      optimized_variable: "system_design",
      conditioning_variable: "loss_spec",
      registered_cross_arm_divergence: divergence ? "observed" : "not_observed",
      note: divergence
        ? "Registered candidate identities differ across LossSpec arms; the system-design search trajectory is metric-conditioned."
        : "All currently registered proposal slots share initial design identities. Metric-conditioned design divergence is not yet observed in this snapshot.",
    },
    score_export: { status: "not_observed", note: "No objective score field exists in this result-blind snapshot contract." },
    winner_freeze: bundle.winner_freeze,
    report: { status: reportStage?.status ?? "locked", note: reportStage ? `${reportStage.label}: ${reportStage.status}.` : "No report stage was exported." },
    provenance: { ...bundle.provenance, snapshot_hash: bundle.snapshot_hash },
    presentation: {
      truth_status: "presentation_only",
      fields: ["district_layout", "facility_shape", "packet_routes", "packet_animation", "colour", "narrative_labels"],
    },
  };
}
