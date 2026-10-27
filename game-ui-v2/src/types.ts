export const FLOW_TYPES = ["data", "paper", "review", "funding", "citation", "policy"] as const;
export type FlowType = (typeof FLOW_TYPES)[number];
export type TruthStatus = "canonical" | "derived" | "ambient";

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
  entity_type: "researcher" | "institution" | "artifact" | "ambient_actor";
  asset_key: string;
  x: number;
  y: number;
  role?: string;
  state?: string;
  description?: string;
}

export interface CanonicalEvent extends EvidenceRecord {
  payload?: Record<string, unknown>;
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

export interface ReplayV2 {
  schema_version: string;
  event_schema_version: string;
  stream_hash: string;
  derivation_version: string;
  metadata: {
    run_id: string;
    branch: string;
    source_kind: string;
    empirical: boolean;
    disclosure: string;
    phase?: string;
    year?: string | number;
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
    camera_cues: CameraCue[];
    placements: Array<EvidenceRecord & { entity_id: string; x: number; y: number }>;
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
  category: "entity" | "flow" | "event";
}

export interface RuntimePreferences {
  reducedMotion: boolean;
  highContrast: boolean;
  atmosphere: number;
}
