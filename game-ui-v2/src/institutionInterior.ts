import { buildEvidenceQuayProjection, type QuayActivityKind, type QuayPacketKind } from "./evidenceQuay";
import type { CanonicalEvent, ProjectionFrame, ReplayV2 } from "./types";

export const INTERIOR_ROOM_IDS = ["laboratory", "writing-room", "review-room", "funding-assembly"] as const;
export type InteriorRoomId = (typeof INTERIOR_ROOM_IDS)[number];
export type InteriorPose = "arrive" | "research" | "write" | "review" | "confer" | "apply" | "report";

export interface InteriorEvidence {
  truth_status: "authoritative_projection";
  event: CanonicalEvent;
  frame: ProjectionFrame;
  actor_states: Record<string, Record<string, unknown>>;
  artifact_states: Record<string, Record<string, unknown>>;
}

export interface InteriorPresentation {
  truth_status: "presentation_only";
  room_id: InteriorRoomId;
  pose: InteriorPose;
  packet_kind: QuayPacketKind;
  route_label: string;
}

export interface InstitutionalInteriorScene {
  evidence: InteriorEvidence;
  presentation: InteriorPresentation;
  activity: QuayActivityKind;
  activity_label: string;
  subject: string;
}

export interface InstitutionalInteriorProjection {
  truth_status: "verified_replay";
  disclosure: string;
  scenes: InstitutionalInteriorScene[];
}

const recordMap = (value: unknown): Record<string, unknown> => value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};

const selectedRecords = (state: Record<string, unknown>, key: "agents" | "artifacts", ids: string[]): Record<string, Record<string, unknown>> => {
  const records = recordMap(state[key]);
  return Object.fromEntries(ids.flatMap((id) => {
    const value = records[id];
    return value && typeof value === "object" && !Array.isArray(value) ? [[id, value as Record<string, unknown>]] : [];
  }));
};

function presentationFor(activity: QuayActivityKind, packetKind: QuayPacketKind): InteriorPresentation {
  const base = { truth_status: "presentation_only" as const, packet_kind: packetKind };
  if (activity === "arrival") return { ...base, room_id: "laboratory", pose: "arrive", route_label: "arrival gate → lab airlock" };
  if (activity === "research") return { ...base, room_id: "laboratory", pose: "research", route_label: "instrument bench loop" };
  if (activity === "writing") return { ...base, room_id: "writing-room", pose: "write", route_label: "lab archive → manuscript desk" };
  if (activity === "review") return { ...base, room_id: "review-room", pose: "review", route_label: "sealed queue → review booth" };
  if (activity === "decision") return { ...base, room_id: "review-room", pose: "confer", route_label: "review dais → decision chamber" };
  if (activity === "funding") return { ...base, room_id: "funding-assembly", pose: "apply", route_label: "application tube → funding assembly" };
  return { ...base, room_id: "funding-assembly", pose: "report", route_label: "civic ledger → assembly archive" };
}

export function buildInstitutionalInteriorProjection(replay: ReplayV2): InstitutionalInteriorProjection {
  const quay = buildEvidenceQuayProjection(replay);
  return {
    truth_status: "verified_replay",
    disclosure: "Event, actor, artifact, and state readouts come from canonical events and matching authoritative frames. Rooms, furniture, researcher pose, walking routes, packet travel, light, and ambience are presentation-only.",
    scenes: quay.cues.map((cue) => ({
      evidence: {
        truth_status: "authoritative_projection",
        event: cue.event,
        frame: cue.frame,
        actor_states: selectedRecords(cue.frame.state, "agents", cue.actor_ids),
        artifact_states: selectedRecords(cue.frame.state, "artifacts", cue.artifact_ids),
      },
      presentation: presentationFor(cue.activity, cue.motion.packet_kind),
      activity: cue.activity,
      activity_label: cue.activity_label,
      subject: cue.subject,
    })),
  };
}

export function interiorAtCursor(projection: InstitutionalInteriorProjection, cursorMs: number): { scene: InstitutionalInteriorScene; progress: number } | undefined {
  let index = -1;
  for (let candidate = projection.scenes.length - 1; candidate >= 0; candidate -= 1) {
    if (projection.scenes[candidate]!.evidence.event.logical_timestamp_ms <= cursorMs) {
      index = candidate;
      break;
    }
  }
  if (index < 0) return undefined;
  const scene = projection.scenes[index]!;
  const next = projection.scenes[index + 1];
  const start = scene.evidence.event.logical_timestamp_ms;
  const end = next?.evidence.event.logical_timestamp_ms ?? start + 2_000;
  const progress = Math.max(0, Math.min(1, (cursorMs - start) / Math.max(1, end - start)));
  return { scene, progress };
}
