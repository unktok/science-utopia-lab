import type { CanonicalEvent, ProjectionFrame, ReplayV2 } from "./types";

export type QuayActivityKind = "arrival" | "research" | "writing" | "review" | "decision" | "funding" | "reporting" | "year-close";
export type QuayPacketKind = "paper" | "review" | "funding" | "knowledge" | "none";

export interface QuayPresentationMotion {
  truth_status: "presentation_only";
  from: "ARRIVAL GATE" | "LAB BERTH" | "SUBMISSION PIER" | "REVIEW TOWER" | "FUNDING EXCHANGE" | "PUBLICATION BEACON" | "CIVIC LEDGER";
  to: "ARRIVAL GATE" | "LAB BERTH" | "SUBMISSION PIER" | "REVIEW TOWER" | "FUNDING EXCHANGE" | "PUBLICATION BEACON" | "CIVIC LEDGER";
  packet_kind: QuayPacketKind;
}

export interface QuayCue {
  event: CanonicalEvent;
  frame: ProjectionFrame;
  activity: QuayActivityKind;
  activity_label: string;
  actor_ids: string[];
  artifact_ids: string[];
  subject: string;
  motion: QuayPresentationMotion;
}

export interface EvidenceQuayProjection {
  truth_status: "verified_replay";
  disclosure: string;
  cues: QuayCue[];
  researcher_ids: string[];
}

const category = (event: CanonicalEvent): string => typeof event.payload?.category === "string" ? event.payload.category : "";

function classify(event: CanonicalEvent): Omit<QuayCue, "event" | "frame" | "actor_ids" | "artifact_ids" | "subject"> {
  if (event.kind === "agent.registered") return {
    activity: "arrival",
    activity_label: "registered in the research system",
    motion: { truth_status: "presentation_only", from: "ARRIVAL GATE", to: "LAB BERTH", packet_kind: "none" },
  };
  if (event.kind === "paper.submitted") return {
    activity: "writing",
    activity_label: "submitted a manuscript",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "SUBMISSION PIER", packet_kind: "paper" },
  };
  if (event.kind === "review.completed") return {
    activity: "review",
    activity_label: "completed a review",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "REVIEW TOWER", packet_kind: "review" },
  };
  if (event.kind === "paper.decided") return {
    activity: "decision",
    activity_label: `received a ${String(event.payload?.decision ?? "recorded")} decision`,
    motion: { truth_status: "presentation_only", from: "REVIEW TOWER", to: "PUBLICATION BEACON", packet_kind: "knowledge" },
  };
  if (event.kind === "resource.changed" && category(event) === "annual_research_cost") return {
    activity: "research",
    activity_label: "recorded annual research activity",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "LAB BERTH", packet_kind: "knowledge" },
  };
  if (event.kind === "resource.changed" && category(event) === "production_submission_cost") return {
    activity: "writing",
    activity_label: "recorded manuscript production cost",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "SUBMISSION PIER", packet_kind: "paper" },
  };
  if (event.kind === "resource.changed" && category(event) === "funding_application_cost") return {
    activity: "funding",
    activity_label: "submitted a funding application cost",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "FUNDING EXCHANGE", packet_kind: "funding" },
  };
  if (event.kind === "resource.changed" && category(event) === "grant_income") return {
    activity: "funding",
    activity_label: "received recorded grant income",
    motion: { truth_status: "presentation_only", from: "FUNDING EXCHANGE", to: "LAB BERTH", packet_kind: "funding" },
  };
  if (event.kind === "resource.balance_reported") return {
    activity: "reporting",
    activity_label: "reported an authoritative resource balance",
    motion: { truth_status: "presentation_only", from: "LAB BERTH", to: "CIVIC LEDGER", packet_kind: "knowledge" },
  };
  if (event.kind === "year.completed") return {
    activity: "year-close",
    activity_label: "closed the canonical simulation year",
    motion: { truth_status: "presentation_only", from: "CIVIC LEDGER", to: "CIVIC LEDGER", packet_kind: "knowledge" },
  };
  throw new Error(`Evidence Quay has no fail-closed activity mapping for ${event.kind}`);
}

const subjectFor = (event: CanonicalEvent): string => {
  if (event.artifact_ids[0]) return event.artifact_ids[0].replace("https://arxiv.org/abs/", "arXiv:");
  if (event.kind === "resource.changed") return category(event).replaceAll("_", " ") || "resource change";
  return event.kind.replaceAll(".", " ");
};

export function buildEvidenceQuayProjection(replay: ReplayV2): EvidenceQuayProjection {
  if (!replay.metadata.empirical || replay.metadata.source_kind !== "verified_commit_pinned_campaign_run") {
    throw new Error("Evidence Quay requires a verified commit-pinned campaign replay");
  }
  if (replay.projection.frames.length !== replay.canonical.events.length + 1) {
    throw new Error("Evidence Quay requires one authoritative frame per canonical event plus the initial frame");
  }
  const researcherIds = new Set(replay.canonical.entities.researchers.map((researcher) => researcher.id));
  const cues = replay.canonical.events.map((event) => {
    const frame = replay.projection.frames[event.sequence + 1];
    if (!frame || frame.event_id !== event.id || frame.logical_timestamp_ms !== event.logical_timestamp_ms) {
      throw new Error(`Canonical event ${event.id} has no matching authoritative frame`);
    }
    const applied = Array.isArray(frame.state.applied_event_ids) ? frame.state.applied_event_ids : [];
    if (!applied.includes(event.id)) throw new Error(`Authoritative frame ${frame.cursor} does not apply event ${event.id}`);
    const semantic = classify(event);
    return {
      ...semantic,
      event,
      frame,
      actor_ids: event.actor_ids.filter((id) => researcherIds.has(id)),
      artifact_ids: [...event.artifact_ids],
      subject: subjectFor(event),
    };
  });
  return {
    truth_status: "verified_replay",
    disclosure: "Activity labels are canonical-event facts and state is read from authoritative frames. Routes, courier paths, packet motion, and persistence between event timestamps are presentation-only.",
    cues,
    researcher_ids: [...researcherIds],
  };
}

export function cueAtCursor(projection: EvidenceQuayProjection, cursorMs: number): { cue: QuayCue; progress: number } | undefined {
  let index = -1;
  for (let candidate = projection.cues.length - 1; candidate >= 0; candidate -= 1) {
    if (projection.cues[candidate]!.event.logical_timestamp_ms <= cursorMs) {
      index = candidate;
      break;
    }
  }
  if (index < 0) return undefined;
  const cue = projection.cues[index]!;
  const next = projection.cues[index + 1];
  const end = next?.event.logical_timestamp_ms ?? cue.event.logical_timestamp_ms + 2_000;
  const span = Math.max(1, end - cue.event.logical_timestamp_ms);
  return { cue, progress: Math.max(0, Math.min(1, (cursorMs - cue.event.logical_timestamp_ms) / span)) };
}

export function agentStateAtCue(cue: QuayCue, actorId: string): Record<string, unknown> | undefined {
  const agents = cue.frame.state.agents;
  if (!agents || typeof agents !== "object" || Array.isArray(agents)) return undefined;
  const state = (agents as Record<string, unknown>)[actorId];
  return state && typeof state === "object" && !Array.isArray(state) ? state as Record<string, unknown> : undefined;
}
