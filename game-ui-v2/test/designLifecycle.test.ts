import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { AdoptionController, parseDesignLifecycle, type AdoptionCandidate } from "../src/designLifecycleContract";

const snapshotPath = new URL("../public/data/native-design-lifecycle-v5.json", import.meta.url);
const auditPath = new URL("../../research/results/native-external-objectives-v5-a1.json", import.meta.url);
const fixture = () => JSON.parse(readFileSync(snapshotPath, "utf8"));
const candidate: AdoptionCandidate = {
  parent_observation_id: "observation-1", expected_checkpoint_sha256: "a".repeat(64), candidate_fingerprint: "b".repeat(64), candidate_system: {},
  loss_spec_sha256: "c".repeat(64), state_actions: [], discard_deliveries: [], authoring: { kind: "explicit-test" },
};

describe("audited native design lifecycle", () => {
  it("binds the portable UI snapshot to the exact audited v5 artifact", () => {
    const parsed = parseDesignLifecycle(fixture());
    const auditHash = createHash("sha256").update(readFileSync(auditPath)).digest("hex");
    expect(parsed.source.artifact_sha256).toBe(auditHash);
    expect(parsed.source.artifact).toBe("research/results/native-external-objectives-v5-a1.json");
  });

  it("retains both loss paths, every observed system, and deterministic first-best ties", () => {
    const parsed = parseDesignLifecycle(fixture());
    expect(parsed.arms).toHaveLength(2);
    expect(parsed.arms.map((arm) => arm.loss_path)).toEqual(expect.arrayContaining([[0.7, 0.45, 0.45], [-1, -3, -3]]));
    for (const arm of parsed.arms) {
      expect(arm.systems).toHaveLength(3);
      expect(arm.systems[1]!.status).toBe("selected");
      expect(arm.systems[2]!.status).toBe("observed-not-selected");
      expect(arm.systems[2]!.loss).toBe(arm.systems[1]!.loss);
    }
  });

  it("keeps the nonselected two-node protocol revision and its code/protocol/wiring evidence", () => {
    const parsed = parseDesignLifecycle(fixture());
    const utility = parsed.arms.find((arm) => arm.id === "native-joint-v5-net-reviewed-utility")!;
    const structural = utility.systems[2]!;
    expect(structural.generated_node_ids).toEqual([
      "generated-d8aa32eb5778.review-pricing",
      "generated-d8aa32eb5778.surplus-clearing",
    ]);
    expect(structural.diff.protocol_types_added).toContain("publication-loss-offers-v1");
    expect(structural.diff.generated_code).toHaveLength(2);
    expect(structural.diff.connections_added.some((edge) => edge.source_mechanism.includes("review-pricing") && edge.target_mechanism.includes("surplus-clearing"))).toBe(true);
  });

  it("fails closed if unsupported achievement claims or adoption transport are inserted", () => {
    const changed = fixture(); changed.claims.held_out = true;
    expect(() => parseDesignLifecycle(changed)).toThrow("held_out");
    const connected = fixture(); connected.adoption.transport = "connected";
    expect(() => parseDesignLifecycle(connected)).toThrow("fail closed");
  });
});

describe("same-society adoption state boundary", () => {
  it("is unavailable without a durable transport and never fakes success", async () => {
    const controller = new AdoptionController();
    expect(controller.state).toBe("unavailable");
    await expect(controller.submit(candidate, true)).rejects.toThrow("not connected");
    expect(controller.state).toBe("unavailable");
  });

  it("requires confirmation, stays pending after dispatch, and completes only with migration receipt", async () => {
    const transport = {
      dispatch: vi.fn(async () => ({ status: "pending" as const, request_id: "request-1", request_sha256: "d".repeat(64) })),
      receipt: vi.fn(async () => ({ status: "adopted" as const, request_id: "request-1", request_sha256: "d".repeat(64), migration_receipt_sha256: "e".repeat(64) })),
    };
    const controller = new AdoptionController(transport);
    await expect(controller.submit(candidate, false)).rejects.toThrow("Explicit confirmation");
    expect(transport.dispatch).not.toHaveBeenCalled();
    await controller.submit(candidate, true);
    expect(controller.state).toBe("pending");
    await controller.refresh();
    expect(controller.state).toBe("completed");
  });

  it("rejects an adopted status without a verified durable receipt hash", async () => {
    const controller = new AdoptionController({
      dispatch: async () => ({ status: "pending", request_id: "request-1", request_sha256: "d".repeat(64) }),
      receipt: async () => ({ status: "adopted", request_id: "request-1", request_sha256: "d".repeat(64) }),
    });
    await controller.submit(candidate, true);
    await expect(controller.refresh()).rejects.toThrow("verified durable migration receipt");
    expect(controller.state).toBe("failed");
  });
});
