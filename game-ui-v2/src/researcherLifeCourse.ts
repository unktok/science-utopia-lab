import { buildEvidenceQuayProjection } from "./evidenceQuay";
import type { CanonicalEvent, ProjectionFrame, ReplayV2 } from "./types";

export interface LifeCourseEvent {
  event: CanonicalEvent;
  frame: ProjectionFrame;
  activity_kind: "registration" | "research" | "paper" | "review" | "funding" | "resource" | "reporting" | "other";
  canonical_label: string;
}

export interface ResourcePoint {
  event_id: string;
  frame_cursor: number;
  year: number;
  logical_timestamp_ms: number;
  balance: number;
  active: boolean;
  category: string;
}

export interface EvidenceRelationship {
  truth_status: "canonical_evidence";
  peer_id: string;
  event_id: string;
  event_kind: string;
  artifact_id: string;
  evidence_label: string;
  year: number;
  logical_timestamp_ms: number;
}

export interface ResearcherDossier {
  researcher_id: string;
  label: string;
  events: LifeCourseEvent[];
  resource_points: ResourcePoint[];
  authored_topics: string[];
  authored_artifact_ids: string[];
  relationships: EvidenceRelationship[];
  observed_years: number[];
  missingness: string[];
}

export interface ResearcherLifeCourseProjection {
  truth_status: "verified_replay";
  disclosure: string;
  frames: ProjectionFrame[];
  dossiers: ResearcherDossier[];
}

export interface DossierCursorState {
  frame: ProjectionFrame;
  agent_state?: Record<string, unknown>;
  events: LifeCourseEvent[];
  resource_points: ResourcePoint[];
}

const record = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
const strings = (value: unknown): string[] => Array.isArray(value) ? value.filter((entry): entry is string => typeof entry === "string") : [];

function activity(event: CanonicalEvent): LifeCourseEvent["activity_kind"] {
  if (event.kind === "agent.registered") return "registration";
  if (event.kind === "paper.submitted" || event.kind === "paper.decided") return "paper";
  if (event.kind === "review.completed") return "review";
  if (event.kind === "resource.balance_reported") return "reporting";
  if (event.kind === "resource.changed") {
    const category = String(event.payload?.category ?? "");
    if (category === "annual_research_cost") return "research";
    if (category === "funding_application_cost" || category === "grant_income") return "funding";
    return "resource";
  }
  return "other";
}

const canonicalLabel = (event: CanonicalEvent): string => {
  if (event.kind === "resource.changed") return `${event.kind} · ${String(event.payload?.category ?? "uncategorized")}`;
  if (event.kind === "paper.decided") return `${event.kind} · ${String(event.payload?.decision ?? "recorded")}`;
  if (event.kind === "review.completed" && typeof event.payload?.score === "number") return `${event.kind} · score ${event.payload.score}`;
  return event.kind;
};

const stateRecord = (frame: ProjectionFrame, key: "agents" | "artifacts", id: string): Record<string, unknown> | undefined => {
  const state = record(frame.state[key]);
  const value = state[id];
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : undefined;
};

function resourcePoint(event: CanonicalEvent, frame: ProjectionFrame, researcherId: string): ResourcePoint | undefined {
  const agent = stateRecord(frame, "agents", researcherId);
  if (!agent || typeof agent.balance !== "number" || typeof agent.active !== "boolean") return undefined;
  const isResource = event.kind === "agent.registered" || event.kind === "resource.changed" || event.kind === "resource.balance_reported";
  if (!isResource) return undefined;
  return {
    event_id: event.id,
    frame_cursor: frame.cursor,
    year: event.year,
    logical_timestamp_ms: event.logical_timestamp_ms,
    balance: agent.balance,
    active: agent.active,
    category: event.kind === "resource.changed" ? String(event.payload?.category ?? "resource") : event.kind,
  };
}

function relationshipsFor(replay: ReplayV2, researcherId: string): EvidenceRelationship[] {
  const relationships: EvidenceRelationship[] = [];
  for (const event of replay.canonical.events) {
    if (event.kind !== "review.completed" || !event.artifact_ids[0]) continue;
    const frame = replay.projection.frames[event.sequence + 1]!;
    const artifactId = event.artifact_ids[0];
    const artifact = stateRecord(frame, "artifacts", artifactId);
    const authorId = typeof artifact?.author_id === "string" ? artifact.author_id : undefined;
    const reviewerId = event.actor_ids[0];
    if (!authorId || !reviewerId) continue;
    if (reviewerId === researcherId) relationships.push({
      truth_status: "canonical_evidence",
      peer_id: authorId,
      event_id: event.id,
      event_kind: event.kind,
      artifact_id: artifactId,
      evidence_label: "reviewed peer artifact",
      year: event.year,
      logical_timestamp_ms: event.logical_timestamp_ms,
    });
    if (authorId === researcherId) relationships.push({
      truth_status: "canonical_evidence",
      peer_id: reviewerId,
      event_id: event.id,
      event_kind: event.kind,
      artifact_id: artifactId,
      evidence_label: "peer reviewed authored artifact",
      year: event.year,
      logical_timestamp_ms: event.logical_timestamp_ms,
    });
  }
  return relationships;
}

export function buildResearcherLifeCourseProjection(replay: ReplayV2): ResearcherLifeCourseProjection {
  buildEvidenceQuayProjection(replay);
  const dossiers = replay.canonical.entities.researchers.map((researcher) => {
    const events = replay.canonical.events.flatMap((event) => {
      if (!event.actor_ids.includes(researcher.id)) return [];
      return [{ event, frame: replay.projection.frames[event.sequence + 1]!, activity_kind: activity(event), canonical_label: canonicalLabel(event) } satisfies LifeCourseEvent];
    });
    const resourcePoints = events.flatMap(({ event, frame }) => {
      const point = resourcePoint(event, frame, researcher.id);
      return point ? [point] : [];
    });
    const submitted = events.filter(({ event }) => event.kind === "paper.submitted");
    const authoredTopics = [...new Set(submitted.flatMap(({ event }) => strings(event.payload?.topics)))];
    const authoredArtifactIds = [...new Set(submitted.flatMap(({ event }) => event.artifact_ids))];
    const observedYears = [...new Set(events.map(({ event }) => event.year))].sort((left, right) => left - right);
    const lastObservedYear = observedYears.at(-1);
    const missingness = [
      ...(authoredTopics.length ? [] : ["Research direction is not observed: no authored-paper topics occur in the loaded canonical stream."]),
      ...(lastObservedYear === undefined ? ["No canonical year is observed for this researcher."] : [`Loaded evidence ends at Year ${lastObservedYear}; no later-year life course is available.`]),
      "No explicit researcher.exit event type occurs in the loaded canonical stream; inactive state is reported only as frame state.",
      "Absence from this finite stream is not evidence of absence outside the simulation run.",
    ];
    return {
      researcher_id: researcher.id,
      label: researcher.label,
      events,
      resource_points: resourcePoints,
      authored_topics: authoredTopics,
      authored_artifact_ids: authoredArtifactIds,
      relationships: relationshipsFor(replay, researcher.id),
      observed_years: observedYears,
      missingness,
    } satisfies ResearcherDossier;
  });
  return {
    truth_status: "verified_replay",
    disclosure: "Dossier events, topics, balances, active state, and artifact-mediated peer evidence come from canonical events and authoritative frames. Node layout, relationship lines, avatar expression, and narrative styling are presentation-only.",
    frames: replay.projection.frames,
    dossiers,
  };
}

export function dossierAtCursor(projection: ResearcherLifeCourseProjection, dossier: ResearcherDossier, cursorMs: number): DossierCursorState {
  const frames = projection.frames.filter((frame) => frame.logical_timestamp_ms <= cursorMs);
  const frame = frames.at(-1) ?? projection.frames[0]!;
  return {
    frame,
    agent_state: stateRecord(frame, "agents", dossier.researcher_id),
    events: dossier.events.filter(({ event }) => event.logical_timestamp_ms <= cursorMs),
    resource_points: dossier.resource_points.filter((point) => point.logical_timestamp_ms <= cursorMs),
  };
}
