import { ACTION_TYPES, FLOW_TYPES, type AssetPack, type EvidenceRecord, type ReplayV2, type TruthStatus, type WorldEntity, type WorldPoint } from "./types";

const asRecord = (value: unknown, path: string): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  return value as Record<string, unknown>;
};

const asArray = (value: unknown, path: string): unknown[] => {
  if (!Array.isArray(value)) throw new Error(`${path} must be an array`);
  return value;
};

const asString = (value: unknown, path: string): string => {
  if (typeof value !== "string" || value.length === 0) throw new Error(`${path} must be a non-empty string`);
  return value;
};

const asNumber = (value: unknown, path: string, fallback?: number): number => {
  if (value === undefined && fallback !== undefined) return fallback;
  if (typeof value !== "number" || !Number.isFinite(value)) throw new Error(`${path} must be a finite number`);
  return value;
};

const truthStatus = (value: unknown, path: string): TruthStatus => {
  if (value === "canonical" || value === "derived" || value === "ambient") return value;
  throw new Error(`${path} must be canonical, derived, or ambient`);
};

const point = (raw: unknown, path: string): WorldPoint => {
  const row = asRecord(raw, path);
  return { x: asNumber(row.x, `${path}.x`), y: asNumber(row.y, `${path}.y`) };
};

const evidence = (raw: unknown, path: string): EvidenceRecord => {
  const row = asRecord(raw, path);
  const refs = row.derived_from_event_ids === undefined ? [] : asArray(row.derived_from_event_ids, `${path}.derived_from_event_ids`).map((v, i) => asString(v, `${path}.derived_from_event_ids[${i}]`));
  return {
    id: asString(row.id, `${path}.id`),
    kind: asString(row.kind, `${path}.kind`),
    label: asString(row.label ?? row.id, `${path}.label`),
    truth_status: truthStatus(row.truth_status, `${path}.truth_status`),
    derived_from_event_ids: refs,
    derivation_version: typeof row.derivation_version === "string" ? row.derivation_version : undefined,
    logical_timestamp_ms: asNumber(row.logical_timestamp_ms, `${path}.logical_timestamp_ms`, 0),
    duration_ms: asNumber(row.duration_ms, `${path}.duration_ms`, 0),
    causal_parent_id: typeof row.causal_parent_id === "string" ? row.causal_parent_id : undefined,
  };
};

const inferredAssetKey = (id: string, entityType: WorldEntity["entity_type"]): string => {
  if (entityType === "institution") {
    if (id.includes("knowledge-lab")) return "institution_lab";
    if (id.includes("peer-review")) return "institution_review";
    if (id.includes("funding")) return "institution_funding";
    return "institution_publication";
  }
  if (entityType === "researcher") {
    if (id.includes(":mino")) return "researcher_reviewer";
    if (id.includes(":iren")) return "researcher_editor";
    if (id.includes(":sol")) return "researcher_pi";
    return "researcher_early";
  }
  if (entityType === "artifact") return "flow_paper";
  return "ambient_courier_drone";
};

const entity = (raw: unknown, path: string, entityType: WorldEntity["entity_type"], placement?: { x: number; y: number }): WorldEntity => {
  const row = asRecord(raw, path);
  const base = evidence(row, path);
  return {
    ...base,
    entity_type: entityType,
    asset_key: typeof row.asset_key === "string" ? row.asset_key : inferredAssetKey(base.id, entityType),
    x: asNumber(row.x, `${path}.x`, placement?.x ?? 0),
    y: asNumber(row.y, `${path}.y`, placement?.y ?? 0),
    role: typeof row.role === "string" ? row.role : undefined,
    state: typeof row.state === "string" ? row.state : undefined,
    description: typeof row.description === "string" ? row.description : undefined,
  };
};

export function parseReplayV2(input: unknown): ReplayV2 {
  const root = asRecord(input, "replay");
  const metadata = asRecord(root.metadata, "metadata");
  const canonical = asRecord(root.canonical, "canonical");
  const entities = asRecord(canonical.entities, "canonical.entities");
  const choreography = asRecord(root.choreography, "choreography");
  const projection = asRecord(root.projection, "projection");
  const ambient = asRecord(root.ambient, "ambient");

  const facts = asArray(canonical.facts ?? [], "canonical.facts");
  const factsByEventId = new Map<string, Record<string, unknown>>();
  for (let i = 0; i < facts.length; i += 1) {
    const fact = asRecord(facts[i], `canonical.facts[${i}]`);
    factsByEventId.set(asString(fact.event_id, `canonical.facts[${i}].event_id`), fact);
  }

  const rawEvents = asArray(canonical.events, "canonical.events");
  const events = rawEvents.map((raw, i) => {
    const row = asRecord(raw, `canonical.events[${i}]`);
    const eventId = asString(row.event_id ?? row.id, `canonical.events[${i}].event_id`);
    const fact = factsByEventId.get(eventId);
    const parsed = fact ? evidence({ ...fact, id: eventId, kind: row.event_type, label: row.event_type }, `canonical.events[${i}]`) : evidence(row, `canonical.events[${i}]`);
    return {
      ...parsed,
      id: eventId,
      kind: asString(row.event_type ?? row.kind, `canonical.events[${i}].event_type`),
      label: typeof row.label === "string" ? row.label : asString(row.event_type ?? row.kind, `canonical.events[${i}].event_type`),
      truth_status: "canonical" as const,
      payload: row.payload && typeof row.payload === "object" ? row.payload as Record<string, unknown> : undefined,
    };
  });
  const eventIds = new Set(events.map((item) => item.id));

  const placements = asArray(choreography.placements ?? [], "choreography.placements").map((raw, i) => {
    const path = `choreography.placements[${i}]`;
    const row = asRecord(raw, path);
    return {
      ...evidence(row, path),
      entity_id: asString(row.entity_id, `${path}.entity_id`),
      x: asNumber(row.x, `${path}.x`),
      y: asNumber(row.y, `${path}.y`),
    };
  });
  const placementsByEntity = new Map(placements.map((placement) => [placement.entity_id, placement]));

  const parseEntities = (key: "researchers" | "institutions" | "artifacts", type: WorldEntity["entity_type"]) =>
    asArray(entities[key], `canonical.entities.${key}`).map((raw, i) => {
      const row = asRecord(raw, `canonical.entities.${key}[${i}]`);
      const id = asString(row.id, `canonical.entities.${key}[${i}].id`);
      return entity(row, `canonical.entities.${key}[${i}]`, type, placementsByEntity.get(id));
    });

  const flows = asArray(choreography.flows, "choreography.flows").map((raw, i) => {
    const path = `choreography.flows[${i}]`;
    const row = asRecord(raw, path);
    const base = evidence(row, path);
    if (!FLOW_TYPES.includes(row.flow_type as never)) throw new Error(`${path}.flow_type is unknown`);
    if (base.truth_status !== "derived") throw new Error(`${path} must be derived`);
    if (base.derived_from_event_ids.length === 0) throw new Error(`${path} requires canonical evidence references`);
    for (const id of base.derived_from_event_ids) if (!eventIds.has(id)) throw new Error(`${path} references missing event ${id}`);
    return {
      ...base,
      flow_type: row.flow_type as (typeof FLOW_TYPES)[number],
      from_entity_id: asString(row.from_entity_id, `${path}.from_entity_id`),
      to_entity_id: asString(row.to_entity_id, `${path}.to_entity_id`),
      color: typeof row.color === "string" ? row.color : undefined,
    };
  });

  const actions = asArray(choreography.actions ?? [], "choreography.actions").map((raw, i) => {
    const path = `choreography.actions[${i}]`;
    const row = asRecord(raw, path);
    const base = evidence(row, path);
    if (!ACTION_TYPES.includes(row.action_type as never)) throw new Error(`${path}.action_type is unknown`);
    if (base.truth_status !== "derived") throw new Error(`${path} must be derived`);
    if (base.derived_from_event_ids.length === 0) throw new Error(`${path} requires canonical evidence references`);
    for (const id of base.derived_from_event_ids) if (!eventIds.has(id)) throw new Error(`${path} references missing event ${id}`);
    return {
      ...base,
      actor_entity_id: asString(row.actor_entity_id, `${path}.actor_entity_id`),
      action_type: row.action_type as (typeof ACTION_TYPES)[number],
      start: point(row.start, `${path}.start`),
      end: point(row.end, `${path}.end`),
    };
  });

  const ambientActors = asArray(ambient.actors, "ambient.actors").map((raw, i) => {
    const row = asRecord(raw, `ambient.actors[${i}]`);
    const path = Array.isArray(row.path) ? row.path : [];
    const first = Array.isArray(path[0]) ? path[0] : [0, 0];
    const parsedPath = path.map((value, pointIndex) => {
      if (!Array.isArray(value) || value.length !== 2 || typeof value[0] !== "number" || typeof value[1] !== "number") {
        throw new Error(`ambient.actors[${i}].path[${pointIndex}] must be an [x, y] pair`);
      }
      return { x: value[0], y: value[1] };
    });
    return {
      ...entity(row, `ambient.actors[${i}]`, "ambient_actor", { x: typeof first[0] === "number" ? first[0] : 0, y: typeof first[1] === "number" ? first[1] : 0 }),
      path: parsedPath,
    };
  });
  const ambientEffects = asArray(ambient.effects, "ambient.effects").map((raw, i) => evidence(raw, `ambient.effects[${i}]`));
  for (const [path, records] of [["ambient.actors", ambientActors], ["ambient.effects", ambientEffects]] as const) {
    records.forEach((record, i) => {
      if (record.truth_status !== "ambient" || record.derived_from_event_ids.length > 0) throw new Error(`${path}[${i}] must be ambient without evidence references`);
    });
  }

  const frames = asArray(projection.frames, "projection.frames").map((raw, i) => {
    const path = `projection.frames[${i}]`;
    const row = asRecord(raw, path);
    return {
      cursor: asNumber(row.cursor, `${path}.cursor`),
      event_id: typeof row.event_id === "string" ? row.event_id : undefined,
      logical_timestamp_ms: asNumber(row.logical_timestamp_ms, `${path}.logical_timestamp_ms`),
      state: asRecord(row.state, `${path}.state`),
    };
  });

  const cameraCues = asArray(choreography.camera_cues ?? [], "choreography.camera_cues").map((raw, i) => {
    const path = `choreography.camera_cues[${i}]`;
    const row = asRecord(raw, path);
    const base = evidence(row, path);
    const zoomValue = row.zoom === undefined ? undefined : asNumber(row.zoom, `${path}.zoom`);
    return {
      ...base,
      target_entity_id: typeof row.target_entity_id === "string" ? row.target_entity_id : undefined,
      x: typeof row.x === "number" ? row.x : undefined,
      y: typeof row.y === "number" ? row.y : undefined,
      zoom: zoomValue,
    };
  });

  const replay: ReplayV2 = {
    schema_version: asString(root.schema_version, "schema_version"),
    event_schema_version: asString(root.event_schema_version, "event_schema_version"),
    stream_hash: asString(root.stream_hash, "stream_hash"),
    derivation_version: asString(root.derivation_version, "derivation_version"),
    metadata: {
      run_id: asString(metadata.run_id ?? metadata.run ?? metadata.source_label ?? metadata.title, "metadata.run_id"),
      branch: asString(metadata.branch ?? metadata.source_kind, "metadata.branch"),
      source_kind: asString(metadata.source_kind, "metadata.source_kind"),
      empirical: metadata.empirical === true,
      disclosure: asString(metadata.disclosure, "metadata.disclosure"),
      phase: typeof metadata.phase === "string" ? metadata.phase : undefined,
      year: typeof metadata.year === "string" || typeof metadata.year === "number" ? metadata.year : undefined,
    },
    canonical: {
      events,
      raw_events: rawEvents,
      entities: {
        researchers: parseEntities("researchers", "researcher"),
        institutions: parseEntities("institutions", "institution"),
        artifacts: parseEntities("artifacts", "artifact"),
      },
    },
    projection: { frames },
    choreography: {
      duration_ms: asNumber(choreography.duration_ms, "choreography.duration_ms"),
      flows,
      actions,
      camera_cues: cameraCues,
      placements,
    },
    ambient: { actors: ambientActors, effects: ambientEffects },
  };

  const allEntities = [...replay.canonical.entities.researchers, ...replay.canonical.entities.institutions, ...replay.canonical.entities.artifacts, ...ambientActors];
  const entityIds = new Set(allEntities.map((item) => item.id));
  if (entityIds.size !== allEntities.length) throw new Error("entity ids must be unique");
  for (const flow of flows) {
    if (!entityIds.has(flow.from_entity_id) || !entityIds.has(flow.to_entity_id)) throw new Error(`${flow.id} has an unknown endpoint`);
  }
  for (const action of actions) {
    const actor = allEntities.find((item) => item.id === action.actor_entity_id);
    if (!actor || actor.entity_type !== "researcher") throw new Error(`${action.id} has an unknown researcher actor`);
  }
  return replay;
}

export function parseAssetPack(input: unknown): AssetPack {
  const root = asRecord(input, "asset pack");
  const images = asArray(root.images, "asset pack.images").map((raw, i) => {
    const path = `asset pack.images[${i}]`;
    const row = asRecord(raw, path);
    const kind = asString(row.kind, `${path}.kind`);
    if (!["researcher", "institution", "flow", "environment", "ui"].includes(kind)) throw new Error(`${path}.kind is unknown`);
    const frames = row.frames === undefined ? undefined : asRecord(row.frames, `${path}.frames`);
    return {
      key: asString(row.key, `${path}.key`),
      url: asString(row.url, `${path}.url`),
      kind: kind as "researcher" | "institution" | "flow" | "environment" | "ui",
      width: asNumber(row.width, `${path}.width`),
      height: asNumber(row.height, `${path}.height`),
      frames: frames ? {
        frameWidth: asNumber(frames.frameWidth, `${path}.frames.frameWidth`),
        frameHeight: asNumber(frames.frameHeight, `${path}.frames.frameHeight`),
        end: asNumber(frames.end, `${path}.frames.end`),
      } : undefined,
    };
  });
  return {
    version: asString(root.version, "asset pack.version"),
    palette: asString(root.palette, "asset pack.palette"),
    images,
  };
}

export async function loadJson<T>(url: string, parser: (input: unknown) => T): Promise<T> {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
  return parser(await response.json());
}
