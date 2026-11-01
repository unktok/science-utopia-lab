import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const sourcePath = resolve(root, "research/results/native-external-objectives-v5-a1.json");
const outputPath = resolve(root, "game-ui-v2/public/data/native-design-lifecycle-v5.json");
const bytes = await readFile(sourcePath);
const audit = JSON.parse(bytes.toString("utf8"));
const sha256 = (value) => createHash("sha256").update(value).digest("hex");

function connectionKey(connection) {
  return `${connection.source_mechanism}.${connection.source_port} -> ${connection.target_mechanism}.${connection.target_port} [${connection.channel}]`;
}

function protocolTypes(system) {
  return [...new Set(system.mechanisms.flatMap((node) => [
    ...(node.inputs ?? []).map((port) => port.artifact_type),
    ...(node.outputs ?? []).map((port) => port.artifact_type),
  ]))].sort();
}

function nodeView(node, schedule) {
  const code = node.parameters?.code_artifact;
  return {
    id: node.mechanism_id,
    family: node.family,
    implementation: node.implementation,
    phase: schedule?.phase ?? null,
    trigger: schedule?.trigger ?? null,
    inputs: node.inputs ?? [],
    outputs: node.outputs ?? [],
    code: code ? {
      label: code.label,
      source: code.source,
      schema: code.schema,
      input_schema: code.inputs,
      output_schema: code.outputs,
      state_schema: code.state_schema,
    } : null,
  };
}

function observedSystem(arm, system, index) {
  const row = arm.audit.rows[index];
  const executedCode = new Map((row.runs?.[0]?.executed_code ?? []).map((entry) => [entry.mechanism_id, entry]));
  const parent = index === 0 ? null : arm.observed_systems[index - 1];
  const generated = system.mechanisms.filter((node) => node.implementation === "code.python.v1");
  const parentTypes = parent ? protocolTypes(parent) : [];
  const types = protocolTypes(system);
  const difference = row.difference;
  return {
    index,
    role: index === 0 ? "shared baseline" : `authored revision ${index}`,
    status: index === arm.selected_index ? "selected" : index < arm.selected_index ? "baseline" : "observed-not-selected",
    selection_reason: index === arm.selected_index
      ? "First minimum encountered; retained by deterministic first-best selection."
      : index > arm.selected_index && row.loss === arm.loss_path[arm.selected_index]
        ? `Tied the selected loss (${row.loss}); deterministic first-best retained revision ${arm.selected_index}.`
        : "Observed development-world candidate; not the minimum selected design.",
    loss: row.loss,
    system_fingerprint: row.system_fingerprint,
    run_id: row.runs?.[0]?.run_id ?? null,
    checkpoint_sha256: row.runs?.[0]?.checkpoint_sha256 ?? null,
    response_count: row.runs?.[0]?.response_count ?? null,
    technical_failures: row.technical_failures ?? [],
    metrics: row.measurements?.[0]?.metrics ?? {},
    nodes: system.mechanisms.map((node) => nodeView(node, system.schedules.find((schedule) => schedule.mechanism_id === node.mechanism_id))),
    connections: system.connections,
    generated_node_ids: generated.map((node) => node.mechanism_id),
    diff: {
      nodes_added: difference?.nodes_added ?? [],
      nodes_removed: difference?.nodes_removed ?? [],
      nodes_changed: difference?.nodes_changed ?? [],
      connections_added: difference ? difference.connections_after.filter((connection) => !new Set(difference.connections_before.map(connectionKey)).has(connectionKey(connection))) : [],
      connections_removed: difference ? difference.connections_before.filter((connection) => !new Set(difference.connections_after.map(connectionKey)).has(connectionKey(connection))) : [],
      protocol_types_added: parent ? types.filter((type) => !parentTypes.includes(type)) : [],
      protocol_types_removed: parent ? parentTypes.filter((type) => !types.includes(type)) : [],
      generated_code: generated.map((node) => ({
        mechanism_id: node.mechanism_id,
        label: node.parameters.code_artifact.label,
        source_sha256: executedCode.get(node.mechanism_id)?.source_sha256 ?? null,
        artifact_sha256: executedCode.get(node.mechanism_id)?.artifact_sha256 ?? null,
        executions: executedCode.get(node.mechanism_id)?.executions ?? null,
      })),
    },
  };
}

const armLabels = {
  "native-joint-v5-throughput": { short: "THROUGHPUT", formula: "minimize −A", accent: "cyan" },
  "native-joint-v5-net-reviewed-utility": { short: "NET REVIEWED UTILITY", formula: "minimize 3.25A − Q + 0.05R", accent: "violet" },
};

const snapshot = {
  schema: "scienceutopia.native-design-lifecycle-ui.v1",
  truth_status: "audited-development-result",
  source: {
    artifact: "research/results/native-external-objectives-v5-a1.json",
    artifact_sha256: sha256(bytes),
    artifact_schema: audit.schema,
    source_commit: audit.source_commit,
    input_manifest_sha256: audit.input_manifest_sha256,
  },
  experiment: {
    classification: audit.classification,
    status: audit.status,
    designer: {
      role: "institution designer",
      model: "Codex specialist agent",
      identity: "/root/joint_region_v5",
      transport: audit.designer_transport,
      provider_authenticated: audit.authoring_provenance.provider_authenticated,
      nonblinded_across_objectives: true,
    },
    researchers: {
      role: "researcher society",
      model: "fixed local Qwen3:8B",
      population: 5,
      seed: 1301,
      years: 2,
      responses_per_world: 57,
      total_responses: 285,
    },
    physical_complete_runs: audit.physical_complete_runs,
    logical_observations: audit.logical_observations,
    shared_initial_physical_runs: audit.shared_initial_physical_runs,
  },
  claims: {
    held_out: false,
    independent_replicates: false,
    scientific_value: false,
    full_world_differentiation: false,
    same_society_adoption_executed: false,
    automatic_recursive_designer: false,
    author_identity_authenticated: false,
    native_code_executed_in_experiment: true,
  },
  arms: Object.values(audit.arms).sort((left, right) => left.loss_spec.id.localeCompare(right.loss_spec.id)).map((arm) => ({
    id: arm.loss_spec.id,
    ...armLabels[arm.loss_spec.id],
    direction: arm.loss_spec.direction,
    interpretation: arm.loss_spec.interpretation,
    loss_spec: arm.loss_spec,
    loss_spec_sha256: arm.audit.binding.loss_spec_sha256,
    loss_path: arm.loss_path,
    selected_index: arm.selected_index,
    selected_fingerprint: arm.selected_fingerprint,
    systems: arm.observed_systems.map((system, index) => observedSystem(arm, system, index)),
  })),
  adoption: {
    transport: "unavailable",
    contract_schema: "scienceutopia.native-society-design-session.v1",
    available_states: ["unavailable", "confirm-required", "pending", "completed", "failed"],
    completion_boundary: "A verified durable migration receipt is required before completed may be displayed.",
  },
  limits: audit.limits,
};

// Guard the exporter itself against silently dropping an observed design.
for (const arm of snapshot.arms) {
  if (arm.systems.length !== arm.loss_path.length || arm.systems.length !== 3) throw new Error(`Unexpected observed-system count for ${arm.id}`);
  if (arm.systems[arm.selected_index].system_fingerprint !== arm.selected_fingerprint) throw new Error(`Selected fingerprint mismatch for ${arm.id}`);
  if (arm.systems.some((system) => system.loss === undefined)) throw new Error(`Missing audited loss for ${arm.id}`);
}

await writeFile(outputPath, `${JSON.stringify(snapshot, null, 2)}\n`, "utf8");
console.log(`${outputPath}\nsource ${snapshot.source.artifact_sha256}\nui ${sha256(Buffer.from(JSON.stringify(snapshot), "utf8"))}`);
