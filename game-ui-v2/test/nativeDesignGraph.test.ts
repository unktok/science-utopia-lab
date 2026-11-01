import { describe, expect, it } from "vitest";
import {
  addMechanism, parseEditableSystemSpec, removeMechanism, removePort, renameMechanism,
  setConnection, structuralCheck,
} from "../src/nativeDesignGraph";

const fixture = () => parseEditableSystemSpec({
  system_id: "test-system", version: 1, metadata: { preserved: "yes" },
  mechanisms: [
    { mechanism_id: "producer", family: "research", implementation: "test.producer.v1", version: 1, inputs: [], outputs: [{ port_id: "paper", channel: "artifact", artifact_type: "paper", required: true }], parameters: {} },
    { mechanism_id: "review", family: "evaluation", implementation: "test.review.v1", version: 1, inputs: [{ port_id: "submission", channel: "artifact", artifact_type: "paper", required: true }], outputs: [], parameters: {} },
  ],
  connections: [{ source_mechanism: "producer", source_port: "paper", target_mechanism: "review", target_port: "submission", channel: "artifact", latency: 0 }],
  schedules: [{ mechanism_id: "producer", phase: 0, trigger: "annual" }, { mechanism_id: "review", phase: 20, trigger: "annual" }],
  agent_types: [], artifact_types: [{ artifact_type_id: "paper", description: "" }], initial_state: {}, global_invariants: [],
});

describe("native visual SystemSpec editing", () => {
  it("round-trips unknown canonical fields and checks a typed graph", () => {
    const spec = fixture(), check = structuralCheck(spec);
    expect(check).toEqual({ valid: true, errors: [], warnings: [] });
    expect(spec.metadata).toEqual({ preserved: "yes" });
  });

  it("renames node references across wires and schedules", () => {
    const renamed = renameMechanism(fixture(), "review", "peer-review");
    expect(renamed.connections[0]!.target_mechanism).toBe("peer-review");
    expect(renamed.schedules[1]!.mechanism_id).toBe("peer-review");
    expect(structuralCheck(renamed).valid).toBe(true);
  });

  it("cleans dependent graph records when a node or port is removed", () => {
    const noPort = removePort(fixture(), "producer", "outputs", "paper");
    expect(noPort.connections).toHaveLength(0);
    const noNode = removeMechanism(fixture(), "review");
    expect(noNode.mechanisms.map(node => node.mechanism_id)).toEqual(["producer"]);
    expect(noNode.connections).toHaveLength(0);
    expect(noNode.schedules.map(row => row.mechanism_id)).toEqual(["producer"]);
  });

  it("adds an editable scheduled custom node and supports explicit rewiring", () => {
    const added = addMechanism(fixture(), "new-mechanism");
    expect(added.mechanisms.at(-1)?.family).toBe("custom");
    expect(added.schedules.at(-1)).toMatchObject({ mechanism_id: "new-mechanism", trigger: "annual" });
    const rewired = setConnection(added, 0, { source_mechanism: "producer", source_port: "paper", target_mechanism: "review", target_port: "submission", channel: "artifact", latency: 2 });
    expect(rewired.connections[0]!.latency).toBe(2);
  });

  it("fails closed on missing endpoints, wrong channels, duplicate ids and required inputs", () => {
    const spec = fixture();
    spec.mechanisms[0]!.mechanism_id = "review";
    spec.connections[0]!.source_mechanism = "missing";
    spec.connections[0]!.channel = "resource";
    const check = structuralCheck(spec);
    expect(check.valid).toBe(false);
    expect(check.errors.join("\n")).toContain("duplicates review");
    expect(check.errors.join("\n")).toContain("source_mechanism does not exist");
    expect(check.errors.join("\n")).toContain("channel does not match target port");
  });
});
