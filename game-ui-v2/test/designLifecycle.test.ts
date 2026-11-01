import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { AdoptionController, adoptionConfirmation, parseDesignLifecycle, type AdoptionCandidate } from "../src/designLifecycleContract";

const snapshotPath = new URL("../public/data/native-design-lifecycle-v5.json", import.meta.url);
const auditPath = new URL("../../research/results/native-external-objectives-v5-a1.json", import.meta.url);
const fixture = () => JSON.parse(readFileSync(snapshotPath, "utf8"));
const candidate: AdoptionCandidate = {
  request_id: "request-1", request_sha256: "d".repeat(64),
  parent_observation_id: "observation-1", expected_checkpoint_sha256: "a".repeat(64), candidate_fingerprint: "b".repeat(64), candidate_system: {},
  loss_spec_sha256: "c".repeat(64), state_actions: {}, discard_deliveries: {}, authoring: { kind: "explicit-test" },
};
function deferred<T>() { let resolve!: (value: T) => void, reject!: (reason?: unknown) => void; const promise = new Promise<T>((ok, fail) => { resolve = ok; reject = fail; }); return { promise, resolve, reject }; }

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
    await expect(controller.submit(candidate, candidate.request_sha256)).rejects.toThrow("historical v5 snapshot");
    expect(controller.state).toBe("unavailable");
  });

  it("exposes the exact staged request hash for UI confirmation", () => {
    expect(adoptionConfirmation(candidate)).toEqual({
      request_id: "request-1", confirmed_request_sha256: "d".repeat(64), candidate_fingerprint: "b".repeat(64), expected_checkpoint_sha256: "a".repeat(64),
    });
    expect(() => adoptionConfirmation({ ...candidate, state_actions: [] as never })).toThrow("state_actions must be a record");
    expect(() => adoptionConfirmation({ ...candidate, discard_deliveries: [] as never })).toThrow("discard_deliveries must be a record");
  });

  it("does not dispatch unless the user confirms the exact staged request hash", async () => {
    const transport = { dispatch: vi.fn(), receipt: vi.fn() };
    const controller = new AdoptionController(transport);
    await expect(controller.submit(candidate, "e".repeat(64))).rejects.toThrow("confirmed_request_sha256");
    expect(controller.state).toBe("confirm-required");
    expect(transport.dispatch).not.toHaveBeenCalled();
  });

  it("binds pending identity and completes only on its verified durable receipt", async () => {
    const transport = {
      dispatch: vi.fn(async (_candidate: AdoptionCandidate, confirmed: string) => ({ status: "pending" as const, request_id: "request-1", request_sha256: confirmed })),
      receipt: vi.fn(async () => ({ status: "adopted" as const, request_id: "request-1", request_sha256: "d".repeat(64), migration_receipt_sha256: "e".repeat(64), verified_receipt: true as const })),
    };
    const controller = new AdoptionController(transport);
    await controller.submit(candidate, candidate.request_sha256);
    expect(controller.state).toBe("pending");
    expect(controller.requestId).toBe(candidate.request_id);
    expect(controller.requestSha256).toBe(candidate.request_sha256);
    expect(transport.dispatch).toHaveBeenCalledWith(candidate, candidate.request_sha256);
    await controller.refresh();
    expect(controller.state).toBe("completed");
  });

  it("keeps a backend pending receipt pending and permits a later verified poll", async () => {
    const receipt = vi.fn()
      .mockResolvedValueOnce({ status: "pending", request_id: candidate.request_id, request_sha256: candidate.request_sha256 })
      .mockResolvedValueOnce({ status: "adopted", request_id: candidate.request_id, request_sha256: candidate.request_sha256, verified_receipt: true, migration_receipt_sha256: "e".repeat(64) });
    const controller = new AdoptionController({ dispatch: async () => ({ status: "pending", request_id: candidate.request_id, request_sha256: candidate.request_sha256 }), receipt });
    await controller.submit(candidate, candidate.request_sha256);
    await controller.refresh();
    expect(controller.state).toBe("pending");
    await controller.refresh();
    expect(controller.state).toBe("completed");
  });

  it.each([
    [{ status: "adopted", request_id: "other-request", request_sha256: "d".repeat(64), verified_receipt: true, migration_receipt_sha256: "e".repeat(64) }, "identity"],
    [{ status: "adopted", request_id: "request-1", request_sha256: "f".repeat(64), verified_receipt: true, migration_receipt_sha256: "e".repeat(64) }, "identity"],
    [{ status: "adopted", request_id: "request-1", request_sha256: "d".repeat(64), migration_receipt_sha256: "e".repeat(64) }, "verified_receipt=true"],
    [{ status: "adopted", request_id: "request-1", request_sha256: "d".repeat(64), verified_receipt: true, migration_receipt_sha256: "not-a-sha" }, "lowercase 64-hex"],
  ] as const)("rejects unbound or unverified adopted receipt %#", async (receipt, message) => {
    const controller = new AdoptionController({ dispatch: async () => ({ status: "pending", request_id: candidate.request_id, request_sha256: candidate.request_sha256 }), receipt: async () => receipt });
    await controller.submit(candidate, candidate.request_sha256);
    await expect(controller.refresh()).rejects.toThrow(message);
    expect(controller.state).toBe("failed");
  });

  it("prevents duplicate submit and early refresh while dispatch acknowledgement is delayed", async () => {
    const pending = deferred<{ status: "pending"; request_id: string; request_sha256: string }>();
    const transport = { dispatch: vi.fn(() => pending.promise), receipt: vi.fn() };
    const controller = new AdoptionController(transport);
    const first = controller.submit(candidate, candidate.request_sha256);
    await expect(controller.submit(candidate, candidate.request_sha256)).rejects.toThrow("already active");
    await controller.refresh();
    expect(controller.state).toBe("pending");
    expect(transport.receipt).not.toHaveBeenCalled();
    pending.resolve({ status: "pending", request_id: candidate.request_id, request_sha256: candidate.request_sha256 });
    await first;
    expect(controller.state).toBe("pending");
  });

  it("coalesces overlapping refreshes so a reordered response cannot overwrite another request", async () => {
    const delayed = deferred<{ status: "adopted"; request_id: string; request_sha256: string; verified_receipt: true; migration_receipt_sha256: string }>();
    const transport = { dispatch: async () => ({ status: "pending" as const, request_id: candidate.request_id, request_sha256: candidate.request_sha256 }), receipt: vi.fn(() => delayed.promise) };
    const controller = new AdoptionController(transport);
    await controller.submit(candidate, candidate.request_sha256);
    const first = controller.refresh();
    await controller.refresh();
    expect(transport.receipt).toHaveBeenCalledTimes(1);
    delayed.resolve({ status: "adopted", request_id: candidate.request_id, request_sha256: candidate.request_sha256, verified_receipt: true, migration_receipt_sha256: "e".repeat(64) });
    await first;
    expect(controller.state).toBe("completed");
    await expect(controller.submit({ ...candidate, request_id: "request-2", request_sha256: "f".repeat(64) }, "f".repeat(64))).rejects.toThrow("completed");
  });
});
