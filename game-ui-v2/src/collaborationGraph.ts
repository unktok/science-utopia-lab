import { buildEvidenceQuayProjection } from "./evidenceQuay";
import type { CanonicalEvent, ReplayV2 } from "./types";

export const EVIDENCE_EDGE_KINDS = ["affiliation", "authorship", "coauthor", "reviewer", "funding_activity", "funder", "citation"] as const;
export type EvidenceEdgeKind = (typeof EVIDENCE_EDGE_KINDS)[number];
export type EvidenceNodeKind = "researcher" | "artifact" | "institution" | "event";

export interface EvidenceGraphNode {
  id: string;
  kind: EvidenceNodeKind;
  label: string;
  truth_status: "canonical" | "authoritative_projection";
  evidence_event_ids: string[];
}

export interface EvidenceGraphEdge {
  id: string;
  kind: EvidenceEdgeKind;
  source_id: string;
  target_id: string;
  truth_status: "canonical_evidence";
  event_id: string;
  event_kind: string;
  label: string;
}

export interface EdgeObservation {
  kind: "coauthor" | "reviewer" | "funder" | "citation";
  count: number;
  status: "observed" | "not_observed" | "identity_missing";
  note: string;
}

export interface EvidenceGraphPresentation {
  truth_status: "presentation_only";
  fields: readonly ["force_layout", "node_placement", "edge_routes", "edge_animation", "colour", "narrative_labels"];
}

export interface CollaborationEvidenceGraph {
  truth_status: "verified_replay";
  observation_scope: "loaded_verified_run";
  disclosure: string;
  nodes: EvidenceGraphNode[];
  edges: EvidenceGraphEdge[];
  lineage: CanonicalEvent[];
  observations: EdgeObservation[];
  missingness: string[];
  presentation: EvidenceGraphPresentation;
}

const graphEventNodeId = (eventId: string): string => `event:${eventId}`;
const institutionNodeId = (institution: string): string => `institution:${institution}`;

export function buildCollaborationEvidenceGraph(replay: ReplayV2): CollaborationEvidenceGraph {
  buildEvidenceQuayProjection(replay);
  const nodes = new Map<string, EvidenceGraphNode>();
  const edges: EvidenceGraphEdge[] = [];
  for (const researcher of replay.canonical.entities.researchers) nodes.set(researcher.id, {
    id: researcher.id,
    kind: "researcher",
    label: researcher.label,
    truth_status: "canonical",
    evidence_event_ids: [...researcher.derived_from_event_ids],
  });
  for (const artifact of replay.canonical.entities.artifacts) nodes.set(artifact.id, {
    id: artifact.id,
    kind: "artifact",
    label: artifact.label,
    truth_status: "authoritative_projection",
    evidence_event_ids: [...artifact.derived_from_event_ids],
  });

  const addEdge = (kind: EvidenceEdgeKind, sourceId: string, targetId: string, event: CanonicalEvent, label: string): void => {
    if (!nodes.has(sourceId) || !nodes.has(targetId)) return;
    edges.push({
      id: `${kind}:${event.id}:${sourceId}:${targetId}`,
      kind,
      source_id: sourceId,
      target_id: targetId,
      truth_status: "canonical_evidence",
      event_id: event.id,
      event_kind: event.kind,
      label,
    });
  };

  for (const event of replay.canonical.events) {
    if (event.kind === "agent.registered") {
      const institution = typeof event.payload?.institution === "string" ? event.payload.institution : undefined;
      if (institution) {
        const id = institutionNodeId(institution);
        const node = nodes.get(id);
        if (node) node.evidence_event_ids.push(event.id);
        else nodes.set(id, { id, kind: "institution", label: institution, truth_status: "canonical", evidence_event_ids: [event.id] });
        for (const researcherId of event.actor_ids) addEdge("affiliation", researcherId, id, event, "registered institution affiliation");
      }
    }
    if (event.kind === "paper.submitted" && event.artifact_ids[0]) {
      const artifactId = event.artifact_ids[0];
      for (const authorId of event.actor_ids) addEdge("authorship", authorId, artifactId, event, "submitted authored artifact");
      for (let left = 0; left < event.actor_ids.length; left += 1) {
        for (let right = left + 1; right < event.actor_ids.length; right += 1) {
          addEdge("coauthor", event.actor_ids[left]!, event.actor_ids[right]!, event, "coauthored submitted artifact");
        }
      }
    }
    if (event.kind === "review.completed" && event.artifact_ids[0]) {
      for (const reviewerId of event.actor_ids) addEdge("reviewer", reviewerId, event.artifact_ids[0], event, "completed review of artifact");
    }
    if (event.kind === "resource.changed" && ["funding_application_cost", "grant_income"].includes(String(event.payload?.category ?? ""))) {
      const eventNodeId = graphEventNodeId(event.id);
      nodes.set(eventNodeId, {
        id: eventNodeId,
        kind: "event",
        label: String(event.payload?.category).replaceAll("_", " "),
        truth_status: "canonical",
        evidence_event_ids: [event.id],
      });
      for (const researcherId of event.actor_ids) addEdge("funding_activity", researcherId, eventNodeId, event, "recorded funding activity");
      const funderId = typeof event.payload?.funder_id === "string" ? event.payload.funder_id : undefined;
      if (funderId && nodes.has(funderId)) for (const researcherId of event.actor_ids) addEdge("funder", funderId, researcherId, event, "named funder provided resource");
    }
    if (event.kind === "citation.created" && event.artifact_ids.length >= 2) {
      addEdge("citation", event.artifact_ids[0]!, event.artifact_ids[1]!, event, "canonical citation");
    }
  }

  const count = (kind: EvidenceEdgeKind): number => edges.filter((edge) => edge.kind === kind).length;
  const fundingEvents = replay.canonical.events.filter((event) => event.kind === "resource.changed" && ["funding_application_cost", "grant_income"].includes(String(event.payload?.category ?? "")));
  const observations: EdgeObservation[] = [
    { kind: "coauthor", count: count("coauthor"), status: count("coauthor") ? "observed" : "not_observed", note: count("coauthor") ? "Canonical multi-author submission events." : "No canonical submission names more than one author." },
    { kind: "reviewer", count: count("reviewer"), status: count("reviewer") ? "observed" : "identity_missing", note: count("reviewer") ? "Reviewer identity is explicit in canonical review events." : "No reviewer identity is available; no reviewer edge was created." },
    { kind: "funder", count: count("funder"), status: count("funder") ? "observed" : fundingEvents.length ? "identity_missing" : "not_observed", note: count("funder") ? "Funder identity is explicit." : "Funding activity exists, but no canonical funder_id names its source." },
    { kind: "citation", count: count("citation"), status: count("citation") ? "observed" : "not_observed", note: count("citation") ? "Canonical citation events." : "No canonical citation.created event occurs in this run." },
  ];
  return {
    truth_status: "verified_replay",
    observation_scope: "loaded_verified_run",
    disclosure: "Nodes and typed evidence edges come from canonical events and authoritative artifact identities. Force layout, node placement, edge routes, animation, colour, and narrative styling are presentation-only.",
    nodes: [...nodes.values()],
    edges,
    lineage: [...replay.canonical.events],
    observations,
    missingness: [
      "Coauthor, reviewer, funder, and citation are distinct edge types and are never substituted for one another.",
      "Funding application and grant-income events do not identify a funder in this stream; funding-activity event nodes are shown without a funder edge.",
      "No citation edge is created without a canonical citation.created event.",
      "Missing or anonymous identities remain missing; the graph does not guess them from institutions, topics, or proximity.",
    ],
    presentation: {
      truth_status: "presentation_only",
      fields: ["force_layout", "node_placement", "edge_routes", "edge_animation", "colour", "narrative_labels"],
    },
  };
}

export function graphAtCursor(graph: CollaborationEvidenceGraph, cursorMs: number): CollaborationEvidenceGraph {
  const eventIds = new Set(graph.lineage.filter((event) => event.logical_timestamp_ms <= cursorMs).map((event) => event.id));
  const edges = graph.edges.filter((edge) => eventIds.has(edge.event_id));
  const connectedIds = new Set(edges.flatMap((edge) => [edge.source_id, edge.target_id]));
  for (const node of graph.nodes) if (node.kind === "researcher" && node.evidence_event_ids.some((id) => eventIds.has(id))) connectedIds.add(node.id);
  return {
    ...graph,
    nodes: graph.nodes.filter((node) => connectedIds.has(node.id)),
    edges,
    lineage: graph.lineage.filter((event) => eventIds.has(event.id)),
  };
}
