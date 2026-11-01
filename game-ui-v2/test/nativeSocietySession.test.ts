import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";
import { NativeSocietyApi, SocietyApiUnavailable, latestRecoverableAdoption, parseNativeSocietyProjection, parseSocietyFixture } from "../src/nativeSocietySession";

const envelope = () => JSON.parse(readFileSync(new URL("../public/data/native-society-session-ui-fixture-v1.json", import.meta.url), "utf8"));

describe("same-society projection contract", () => {
  it("loads a clearly labelled read-only fixture with interval loss and exact pending request", () => {
    const fixture = parseSocietyFixture(envelope());
    expect(fixture.label).toContain("ACTIONS DISABLED");
    expect(fixture.projection.observations.map((item) => [item.after_year, item.through_year, item.loss])).toEqual([[0, 1, 0.7], [1, 3, 0.45]]);
    expect(fixture.projection.pending?.request_sha256).toBe("e".repeat(64));
    expect(fixture.projection.adoptions).toHaveLength(1);
    expect(fixture.projection.model_weights_trained).toBe(false);
    expect(fixture.projection.causal_improvement_established).toBe(false);
  });

  it("rejects causal/training claims and unbound pending/adoption identity", () => {
    const trained = envelope().projection; trained.model_weights_trained = true;
    expect(() => parseNativeSocietyProjection(trained)).toThrow("training or causal");
    const pending = envelope().projection; pending.pending.request_id = "other-request";
    expect(() => parseNativeSocietyProjection(pending)).toThrow("Pending request");
    const substitutedPending = envelope().projection; substitutedPending.pending.expected_checkpoint_sha256 = "0".repeat(64);
    expect(() => parseNativeSocietyProjection(substitutedPending)).toThrow("exact staged request");
    const adoption = envelope().projection; adoption.adoptions[0].candidate_fingerprint = "f".repeat(64);
    expect(() => parseNativeSocietyProjection(adoption)).toThrow("Adoption does not match");
    const confirmation = envelope().projection; confirmation.confirmations = [{ request_id: "other-request", request_sha256: "e".repeat(64) }];
    expect(() => parseNativeSocietyProjection(confirmation)).toThrow("Confirmation does not match");
  });

  it("accepts only a confirmation bound to the exact staged request identity", () => {
    const projection = envelope().projection;
    projection.confirmations = [{
      request_id: projection.pending.request_id,
      request_sha256: projection.pending.request_sha256,
    }];
    expect(parseNativeSocietyProjection(projection).confirmations).toEqual(projection.confirmations);
  });

  it("recovers a completed request only when adoption and confirmation share its exact identity", () => {
    const projection = parseNativeSocietyProjection(envelope().projection);
    const adoption = projection.adoptions[0]!;
    projection.confirmations = [{ request_id: adoption.request_id, request_sha256: adoption.request_sha256 }];
    expect(latestRecoverableAdoption(projection)?.request_sha256).toBe(adoption.request_sha256);
    projection.confirmations = [];
    expect(latestRecoverableAdoption(projection)).toBeNull();
  });
});

describe("loopback same-society API transport", () => {
  it("uses the session token, confirms only exact ID/SHA, and reads the receipt endpoint", async () => {
    const projection = envelope().projection;
    const pending = projection.pending;
    const calls: Array<{ input: string; init: RequestInit }> = [];
    const fetcher = vi.fn(async (input: string | URL | Request, init: RequestInit = {}) => {
      const path = String(input); calls.push({ input: path, init });
      if (path === "/native-api/session") return new Response(JSON.stringify({ token: "loopback-token" }), { status: 200, headers: { "Content-Type": "application/json" } });
      if (path === "/native-api/society") return new Response(JSON.stringify(projection), { status: 200, headers: { "Content-Type": "application/json" } });
      if (path === "/native-api/society/confirm") return new Response(JSON.stringify({ status: "pending", request_id: pending.request_id, request_sha256: pending.request_sha256 }), { status: 200, headers: { "Content-Type": "application/json" } });
      if (path === `/native-api/society/requests/${pending.request_id}`) return new Response(JSON.stringify({ status: "adopted", request_id: pending.request_id, request_sha256: pending.request_sha256, verified_receipt: true, migration_receipt_sha256: "1".repeat(64) }), { status: 200, headers: { "Content-Type": "application/json" } });
      return new Response("not found", { status: 404 });
    }) as unknown as typeof fetch;
    const api = await NativeSocietyApi.connect(fetcher);
    expect((await api.projection()).pending?.request_id).toBe(pending.request_id);
    expect(await api.dispatch(pending, pending.request_sha256)).toMatchObject({ status: "pending", request_id: pending.request_id });
    expect(await api.receipt(pending.request_id)).toMatchObject({ status: "adopted", verified_receipt: true });
    const confirmCall = calls.find((call) => call.input.endsWith("/society/confirm"))!;
    expect(confirmCall.init.method).toBe("POST");
    expect(JSON.parse(String(confirmCall.init.body))).toEqual({ request_id: pending.request_id, confirmed_request_sha256: pending.request_sha256 });
    expect(new Headers(confirmCall.init.headers).get("X-Native-Lab-Token")).toBe("loopback-token");
    expect(calls.filter((call) => call.input !== "/native-api/session").every((call) => new Headers(call.init.headers).get("X-Native-Lab-Token") === "loopback-token")).toBe(true);
  });

  it("maps absent server/endpoint to unavailable and rejects unsafe request IDs locally", async () => {
    const unavailable = vi.fn(async () => new Response("missing", { status: 404 })) as unknown as typeof fetch;
    await expect(NativeSocietyApi.connect(unavailable)).rejects.toBeInstanceOf(SocietyApiUnavailable);
    const projection = envelope().projection;
    const fetchMock = vi.fn(async (input: string | URL | Request) => String(input) === "/native-api/session"
      ? new Response(JSON.stringify({ token: "token" }), { status: 200, headers: { "Content-Type": "application/json" } })
      : new Response(JSON.stringify(projection), { status: 200, headers: { "Content-Type": "application/json" } }));
    const fetcher = fetchMock as unknown as typeof fetch;
    const api = await NativeSocietyApi.connect(fetcher);
    const calls = fetchMock.mock.calls.length;
    await expect(api.receipt("../other-request")).rejects.toThrow("Unsafe");
    expect(fetchMock.mock.calls.length).toBe(calls);
  });
});
