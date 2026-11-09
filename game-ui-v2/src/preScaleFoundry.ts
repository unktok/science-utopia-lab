import { parseNativeLab, type NativeLab } from "./nativeContract";

export const PRE_SCALE_SOURCE = "62388a74d071a3a4fdc8cc309c2807422f96223f";
export const PRE_SCALE_PLAN = "db2df5c5e54a68c8201b6b8c460cffa66770ee37da4f7b0d1089c7f5fc7702cb";
export const PRE_SCALE_FOUNDRY_SCOPE = "closed-pre-scale-development-cells-not-unused-seed-generalization";
export const PRE_SCALE_ARMS = ["throughput", "efficiency"].flatMap(objective =>
  ["parameters", "code-fixed-graph", "code-and-graph", "random"].map(method => `${objective}:${method}`));

export function preScaleFoundryArm(search: string): string | null {
  const values = new URLSearchParams(search).getAll("pre-scale-arm");
  if (!values.length) return null;
  if (values.length !== 1 || !PRE_SCALE_ARMS.includes(values[0]!)) throw new Error("Unknown pre-scale arm; no alternate evidence is loaded");
  return values[0]!;
}

export function preScaleFoundryFile(arm: string): string {
  if (!PRE_SCALE_ARMS.includes(arm)) throw new Error("Unknown pre-scale arm");
  return `./data/pre-scale-foundry-v1/${arm.replace(":", "--")}.json`;
}

export async function parsePreScaleFoundry(value: unknown, arm: string): Promise<NativeLab> {
  preScaleFoundryFile(arm);
  const lab = await parseNativeLab(value), boundary = lab.interpretation;
  if (lab.source.world.source_commit !== PRE_SCALE_SOURCE || lab.source.world.years !== 4
    || lab.source.world.model !== "qwen3:8b" || boundary.scope !== PRE_SCALE_FOUNDRY_SCOPE
    || boundary.plan_sha256 !== PRE_SCALE_PLAN || boundary.pre_scale_arm !== arm
    || boundary.development_only !== true || boundary.selection_is_not_recomputed_by_viewer !== true || lab.relaxation !== null
    || typeof boundary.original_audit_content_sha256 !== "string"
    || !/^[0-9a-f]{64}$/.test(boundary.original_audit_content_sha256)
    || lab.systems.some(row => typeof row.evidence_label !== "string" || !row.evidence_label.trim())) {
    throw new Error("Pre-scale source, plan, arm or closed-audit evidence scope differs; no fallback");
  }
  for (const row of lab.systems) for (const run of row.runs) {
    if (run.seed !== 41001 || run.frames.length > 4 || run.frames.some((frame, index) => frame.year !== index + 1)
      || row.status === "complete" && run.frames.length !== 4) throw new Error("Pre-scale committed development frame/seed differs");
  }
  return lab;
}
