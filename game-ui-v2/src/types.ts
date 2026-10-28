export const FLOW_TYPES = ["data", "paper", "review", "funding", "citation", "policy"] as const;
export type FlowType = (typeof FLOW_TYPES)[number];
export type TruthStatus = "canonical" | "derived" | "ambient";
export const ACTION_TYPES = ["move", "experiment", "write", "review", "revise", "publish", "allocate", "receive", "read", "cite", "policy"] as const;
export type ActionType = (typeof ACTION_TYPES)[number];
export const EPISTEMIC_FLOW_KINDS = ["manuscript", "review", "decision", "application", "award"] as const;
export type EpistemicFlowKind = (typeof EPISTEMIC_FLOW_KINDS)[number];

export interface WorldPoint {
  x: number;
  y: number;
}

export interface EvidenceRecord {
  id: string;
  kind: string;
  label: string;
  truth_status: TruthStatus;
  derived_from_event_ids: string[];
  derivation_version?: string;
  logical_timestamp_ms: number;
  duration_ms: number;
  causal_parent_id?: string;
}

export interface WorldEntity extends EvidenceRecord {
  entity_type: "researcher" | "institution" | "artifact" | "ambient_actor" | "workflow_node";
  asset_key: string;
  x: number;
  y: number;
  role?: string;
  state?: string;
  description?: string;
  path?: WorldPoint[];
}

export interface CanonicalEvent extends EvidenceRecord {
  payload?: Record<string, unknown>;
  sequence: number;
  year: number;
  phase: number;
  actor_ids: string[];
  artifact_ids: string[];
  provenance: Record<string, unknown>;
}

export interface VisualFlow extends EvidenceRecord {
  flow_type: FlowType;
  from_entity_id: string;
  to_entity_id: string;
  color?: string;
}

export interface ProjectionFrame {
  cursor: number;
  event_id?: string;
  logical_timestamp_ms: number;
  state: Record<string, unknown>;
}

export interface CameraCue extends EvidenceRecord {
  target_entity_id?: string;
  x?: number;
  y?: number;
  zoom?: number;
}

export interface VisualAction extends EvidenceRecord {
  actor_entity_id: string;
  action_type: ActionType;
  start: WorldPoint;
  end: WorldPoint;
  path: WorldPoint[];
}

export interface EpistemicFlow extends EvidenceRecord {
  flow_kind: EpistemicFlowKind;
  from_entity_id: string;
  to_entity_id: string;
  path: WorldPoint[];
  packet_asset_key: string;
  event_type: string;
}

export interface CinematicChapter extends EvidenceRecord {
  end_ms: number;
}

export interface ReplayV2 {
  schema_version: string;
  event_schema_version: string;
  stream_hash: string;
  web_stream_hash?: string;
  derivation_version: string;
  metadata: {
    run_id: string;
    branch: string;
    source_kind: string;
    empirical: boolean;
    disclosure: string;
    phase?: string;
    year?: string | number;
    campaign_id?: string;
    campaign_revision?: string;
    source_commit?: string;
    claim_boundary?: string;
  };
  canonical: {
    events: CanonicalEvent[];
    raw_events: unknown[];
    entities: {
      researchers: WorldEntity[];
      institutions: WorldEntity[];
      artifacts: WorldEntity[];
    };
  };
  projection: { frames: ProjectionFrame[] };
  choreography: {
    duration_ms: number;
    flows: VisualFlow[];
    actions: VisualAction[];
    camera_cues: CameraCue[];
    chapters: CinematicChapter[];
    workflow_nodes: WorldEntity[];
    epistemic_flows: EpistemicFlow[];
    time_compression: {
      kind: string;
      canonical_event_count: number;
      duration_ms: number;
    };
    placements: Array<EvidenceRecord & { entity_id: string; x: number; y: number; asset_key?: string }>;
  };
  ambient: {
    actors: WorldEntity[];
    effects: EvidenceRecord[];
  };
}

export interface AssetImage {
  key: string;
  url: string;
  kind: "researcher" | "institution" | "flow" | "environment" | "ui";
  width: number;
  height: number;
  frames?: { frameWidth: number; frameHeight: number; end: number };
}

export interface AssetPack {
  version: string;
  palette: string;
  images: AssetImage[];
}

export interface SelectionDetail {
  id: string;
  category: "entity" | "flow" | "epistemic" | "action" | "event";
}

export interface RuntimePreferences {
  reducedMotion: boolean;
  highContrast: boolean;
  atmosphere: number;
}
