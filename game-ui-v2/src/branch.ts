import { canonicalHash } from "./hash";
import type { ReplayV2 } from "./types";

export interface BranchDescriptor {
  id: string;
  label: string;
  color: string;
  replay_url: string;
  stream_hash: string;
  intervention_event_id: string;
}

export interface BranchManifest {
  schema_version: "scienceutopia.replay-branch-manifest.v1";
  comparison_id: string;
  source_kind: string;
  empirical: boolean;
  disclosure: string;
  shared_origin: {
    event_count: number;
    stream_hash: string;
    last_event_id: string;
    split_after_event_type: string;
  };
  branches: [BranchDescriptor, BranchDescriptor];
}

const record = (value: unknown, path: string): Record<string, unknown> => {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${path} must be an object`);
  return value as Record<string, unknown>;
};
const string = (value: unknown, path: string): string => {
  if (typeof value !== "string" || !value) throw new Error(`${path} must be a non-empty string`);
  return value;
};

export function parseBranchManifest(input: unknown): BranchManifest {
  const root = record(input, "branch manifest");
  if (root.schema_version !== "scienceutopia.replay-branch-manifest.v1") throw new Error("Unsupported branch manifest schema");
  const origin = record(root.shared_origin, "shared_origin");
  if (!Array.isArray(root.branches) || root.branches.length !== 2) throw new Error("branch manifest must contain exactly two futures");
  const branches = root.branches.map((value, index) => {
    const row = record(value, `branches[${index}]`);
    return {
      id: string(row.id, `branches[${index}].id`),
      label: string(row.label, `branches[${index}].label`),
      color: string(row.color, `branches[${index}].color`),
      replay_url: string(row.replay_url, `branches[${index}].replay_url`),
      stream_hash: string(row.stream_hash, `branches[${index}].stream_hash`),
      intervention_event_id: string(row.intervention_event_id, `branches[${index}].intervention_event_id`),
    };
  }) as [BranchDescriptor, BranchDescriptor];
  const eventCount = origin.event_count;
  if (!Number.isInteger(eventCount) || Number(eventCount) < 1) throw new Error("shared_origin.event_count must be a positive integer");
  return {
    schema_version: root.schema_version,
    comparison_id: string(root.comparison_id, "comparison_id"),
    source_kind: string(root.source_kind, "source_kind"),
    empirical: root.empirical === true,
    disclosure: string(root.disclosure, "disclosure"),
    shared_origin: {
      event_count: Number(eventCount),
      stream_hash: string(origin.stream_hash, "shared_origin.stream_hash"),
      last_event_id: string(origin.last_event_id, "shared_origin.last_event_id"),
      split_after_event_type: string(origin.split_after_event_type, "shared_origin.split_after_event_type"),
    },
    branches,
  };
}

export async function verifyBranchBundle(manifest: BranchManifest, replays: [ReplayV2, ReplayV2]): Promise<void> {
  for (let index = 0; index < replays.length; index += 1) {
    const replay = replays[index]!;
    const branch = manifest.branches[index]!;
    const actualStreamHash = await canonicalHash(replay.canonical.raw_events);
    if (actualStreamHash !== branch.stream_hash || actualStreamHash !== replay.stream_hash) throw new Error(`${branch.id}: canonical stream hash mismatch`);
    if (!replay.canonical.events.some((event) => event.id === branch.intervention_event_id && event.kind === "policy.changed")) throw new Error(`${branch.id}: intervention event is absent from its canonical stream`);
  }
  const count = manifest.shared_origin.event_count;
  const leftPrefix = replays[0].canonical.raw_events.slice(0, count);
  const rightPrefix = replays[1].canonical.raw_events.slice(0, count);
  const [leftHash, rightHash] = await Promise.all([canonicalHash(leftPrefix), canonicalHash(rightPrefix)]);
  if (leftHash !== rightHash || leftHash !== manifest.shared_origin.stream_hash) throw new Error("declared common origin does not match both canonical prefixes");
  const leftLast = replays[0].canonical.events[count - 1];
  const rightLast = replays[1].canonical.events[count - 1];
  if (leftLast?.id !== manifest.shared_origin.last_event_id || rightLast?.id !== manifest.shared_origin.last_event_id) throw new Error("declared split event does not match both branches");
}
