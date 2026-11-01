import { canonicalHash } from "./hash";
import { OBJECTIVE_IDS, type ObjectiveStructureReport, type Row } from "./objectiveStructureContract";

const H = {
  initial: "1".repeat(64), throughputA: "2".repeat(64), throughputB: "3".repeat(64), utilityA: "4".repeat(64),
  sourceA: "a".repeat(64), sourceB: "b".repeat(64), inventory: "c".repeat(64),
};

function node(id: string, implementation: string, source?: string): Row {
  return {
    mechanism_id: id,
    family: id.startsWith("world.") ? "population" : "institution",
    implementation,
    version: 1,
    inputs: id === "world.open" ? [] : [{ port_id: "in", artifact_type: "signal", channel: "signal", required: true }],
    outputs: id === "archive" ? [] : [{ port_id: "out", artifact_type: "signal", channel: "signal", required: true }],
    parameters: source ? { code_artifact: { source, schema: "scienceutopia.generated-code.v1" } } : {},
  };
}

function edge(source: string, target: string): Row {
  return { source_mechanism: source, source_port: "out", target_mechanism: target, target_port: "in", channel: "signal", latency: 0 };
}

function system(variant: "initial" | "throughput-a" | "throughput-b" | "utility-a"): Row {
  const mechanisms = [node("world.open", "native.phase.open.v1"), node("review", "native.review.v1"), node("archive", "native.archive.v1")];
  if (variant === "throughput-a") mechanisms.splice(2, 0, node("rapid-disseminator", "code.python.v1", "def run(inputs, state):\n    return {'out': inputs.get('in')}"));
  if (variant === "throughput-b") mechanisms.splice(2, 0, node("open-review-router", "code.python.v1", "def run(inputs, state):\n    return {'out': inputs.get('in'), 'state': state}"));
  if (variant === "utility-a") mechanisms.splice(2, 0, node("deliberation-gate", "code.python.v1", "def run(inputs, state):\n    return {'out': inputs.get('in'), 'audit': True}"));
  const middle = mechanisms[2]!.mechanism_id;
  return {
    system_id: "native-research-world", version: 1, agent_types: [], artifact_types: [], global_invariants: [], metadata: {}, mechanisms,
    connections: variant === "initial" ? [edge("world.open", "review"), edge("review", "archive")] : [edge("world.open", "review"), edge("review", middle), edge(middle, "archive")],
    schedules: [], initial_state: {},
  };
}

const initial = system("initial");

function change(toFingerprint: string, added: string, sourceHash: string): Row {
  return {
    from_fingerprint: H.initial, to_fingerprint: toFingerprint,
    nodes_added: [added], nodes_removed: [],
    edges_added: [["review", "out", added, "in", "signal", 0], [added, "out", "archive", "in", "signal", 0]],
    edges_removed: [["review", "out", "archive", "in", "signal", 0]], rewired_endpoint_pairs: [],
    source_changes: [], source_bodies_added: [sourceHash], source_bodies_removed: [], same_source_body_renamed_ids: [],
    protocol_changes: [], mechanism_configuration_changes: [], schedules_added: [], schedules_removed: [],
    initial_state_change: { changed: false, before_sha256: "d".repeat(64), after_sha256: "d".repeat(64), counts_as_new_algorithm: false },
    counts: { nodes_added: 1, nodes_removed: 0, edges_added: 2, edges_removed: 1, rewired_endpoint_pairs: 0, source_changes: 0, source_bodies_added: 1, source_bodies_removed: 0, same_source_body_renamed_ids: 0, protocol_changes: 0, mechanism_configuration_changes: 0, schedules_added: 0, schedules_removed: 0, initial_state_changes: 0 },
  };
}

function evaluation(loss: number): Row { return { status: "complete", loss, rejected_runs: [] }; }
function unavailable(reason: string): Row { return { status: "unavailable", loss: null, rejected_runs: [{ reason }] }; }

function completeRow(arm: string, generation: number, drawIndex: number, candidate: Row, candidateFingerprint: string, own: number, cross: number | null, added: string, sourceHash: string): Row {
  const throughput = arm === OBJECTIVE_IDS[0] ? own : cross;
  const utility = arm === OBJECTIVE_IDS[1] ? own : cross;
  const suggestionId = `fixture-suggestion-${arm}-${generation}-${drawIndex}`;
  const observationId = `fixture-observation-${arm}-${generation}-${drawIndex}`;
  return {
    arm, generation, draw_index: drawIndex, version_sha256: "e".repeat(64), strategy: `fixture-${arm}`,
    draw: { suggestion: { suggestion_id: suggestionId, candidate }, assignment: {} },
    observation: { observation_id: observationId, suggestion_id: suggestionId, status: "complete", loss: own, metadata: { system_fingerprint: candidateFingerprint } }, status: "complete",
    independent_metrics: { "native.accepted_decisions": { status: "measured", value: 4 } },
    cross_objective_losses: { [OBJECTIVE_IDS[0]]: throughput, [OBJECTIVE_IDS[1]]: utility },
    loss_evaluations: {
      [OBJECTIVE_IDS[0]]: throughput === null ? unavailable("fixture omits the peer-score metric required only by the other objective") : evaluation(throughput),
      [OBJECTIVE_IDS[1]]: utility === null ? unavailable("fixture omits the peer-score metric required only by the other objective") : evaluation(utility),
    },
    physical_proof: { measurement: { system_fingerprint: candidateFingerprint }, run_id: `fixture-run-${generation}-${drawIndex}` },
    graph_changes: { vs_initial: change(candidateFingerprint, added, sourceHash), vs_parent: change(candidateFingerprint, added, sourceHash) },
  };
}

function failureRow(arm: string, generation: number, status: "technical-failure" | "generation-failure"): Row {
  return {
    arm, generation, planned_draws: 2, version_sha256: "f".repeat(64), strategy: `fixture-${arm}`, status,
    generation_error: status === "generation-failure" ? { type: "InvalidVocabulary", message: "fixture invalid generated vocabulary" } : null,
    draw: null, observation: null, independent_metrics: null,
    cross_objective_losses: { [OBJECTIVE_IDS[0]]: null, [OBJECTIVE_IDS[1]]: null },
    loss_evaluations: null, physical_proof: null, graph_changes: null,
  };
}

export async function objectiveStructureFixture(): Promise<ObjectiveStructureReport> {
  const throughputA = system("throughput-a");
  const throughputB = system("throughput-b");
  const utilityA = system("utility-a");
  const throughputRows = [
    completeRow(OBJECTIVE_IDS[0], 0, 0, throughputA, H.throughputA, -3, 2, "rapid-disseminator", H.sourceA),
    completeRow(OBJECTIVE_IDS[0], 0, 1, throughputA, H.throughputA, -4, 1.2, "rapid-disseminator", H.sourceA),
    completeRow(OBJECTIVE_IDS[0], 0, 2, throughputB, H.throughputB, -4, null, "open-review-router", H.sourceB),
    failureRow(OBJECTIVE_IDS[0], 1, "generation-failure"),
  ];
  const utilityRows = [
    completeRow(OBJECTIVE_IDS[1], 0, 0, utilityA, H.utilityA, 0.7, -2, "deliberation-gate", H.sourceA),
    failureRow(OBJECTIVE_IDS[1], 0, "technical-failure"),
  ];
  const arms: Row = {
    [OBJECTIVE_IDS[0]]: {
      loss_spec: { id: OBJECTIVE_IDS[0], name: "Throughput", terms: [{ metric: "native.accepted_decisions", weight: -1 }] }, binding: { initial_system: initial },
      rows: throughputRows, generation_failures: [throughputRows[3]], loss_path: [-3, -4, -4, null],
      selection: {
        criterion: "minimum observed bound development loss; earliest exact observation row in audited campaign order is display representative",
        best_loss: -4, tie_count: 2, tied_system_fingerprints: [H.throughputA, H.throughputB],
        tied_observation_ids: [`fixture-observation-${OBJECTIVE_IDS[0]}-0-1`, `fixture-observation-${OBJECTIVE_IDS[0]}-0-2`],
        tied_suggestion_ids: [`fixture-suggestion-${OBJECTIVE_IDS[0]}-0-1`, `fixture-suggestion-${OBJECTIVE_IDS[0]}-0-2`],
        representative_system_fingerprint: H.throughputA,
        representative_observation_id: `fixture-observation-${OBJECTIVE_IDS[0]}-0-1`,
        representative_suggestion_id: `fixture-suggestion-${OBJECTIVE_IDS[0]}-0-1`,
      },
    },
    [OBJECTIVE_IDS[1]]: {
      loss_spec: { id: OBJECTIVE_IDS[1], name: "Net reviewed utility", terms: [] }, binding: { initial_system: initial },
      rows: utilityRows, generation_failures: [], loss_path: [0.7, null],
      selection: {
        criterion: "minimum observed bound development loss; earliest exact observation row in audited campaign order is display representative",
        best_loss: 0.7, tie_count: 1, tied_system_fingerprints: [H.utilityA],
        tied_observation_ids: [`fixture-observation-${OBJECTIVE_IDS[1]}-0-0`],
        tied_suggestion_ids: [`fixture-suggestion-${OBJECTIVE_IDS[1]}-0-0`],
        representative_system_fingerprint: H.utilityA,
        representative_observation_id: `fixture-observation-${OBJECTIVE_IDS[1]}-0-0`,
        representative_suggestion_id: `fixture-suggestion-${OBJECTIVE_IDS[1]}-0-0`,
      },
    },
  };
  const report: Row = {
    schema: "scienceutopia.native-objective-structure-audit.v8", classification: "scripted-fixture-not-native-results",
    status: "budget-complete-with-failures", source_commit: "9".repeat(40), raw_inventory_sha256: H.inventory, raw_file_count: 18,
    completed_physical_worlds: 4, physical_cache_count: 4,
    raw_campaign_summary: { planned_native_world_budget: 8, committed_draws: 5, complete_native_worlds: 4, technical_failures: 2, budget_terminal: true, status: "budget-complete-with-failures", configured_researcher_provider: "qwen3:8b", physical_reply_count: 16 },
    arms,
    selected_cross_objective_matrix: {
      [OBJECTIVE_IDS[0]]: { [OBJECTIVE_IDS[0]]: -4, [OBJECTIVE_IDS[1]]: 1.2 },
      [OBJECTIVE_IDS[1]]: { [OBJECTIVE_IDS[0]]: -2, [OBJECTIVE_IDS[1]]: 0.7 },
    },
    held_out_metrics: { status: "not-defined-or-measured" }, promotion_policy: { status: "not-defined-or-applied" },
    claims: ["Development engineering evidence only; no held-out, causal, scientific-value, or improvement claim.", "Technical failures remain null and are excluded from numerical selection."],
  };
  report.content_sha256 = await canonicalHash(report);
  return report as ObjectiveStructureReport;
}
