import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { validatePreScale, valueLabel, statusLabel, snapshotSource } from "../src/preScaleContract";
import { webCanonicalHash } from "../src/hash";

const actual = () => JSON.parse(readFileSync(new URL("../public/data/pre-scale-observatory.actual.json", import.meta.url), "utf8"));
const rehash = async (e: ReturnType<typeof actual>) => { e.web_sha256 = await webCanonicalHash([e.payload]); return e; };

describe("pre-scale actual journal projection", () => {
  it("verifies the exported Python/browser checksum and all twelve slots", async () => {
    const p = await validatePreScale(actual());
    expect(p.information.worlds).toHaveLength(12);
    expect(p.information.numeric_readiness).toHaveLength(2);
    expect(p.information.numeric_readiness.every(r => r.scientific_loss === null)).toBe(true);
    expect(p.observation_kind).toContain("not-live-heartbeat");
  });
  it("never displays an unknown as zero or a start as a running process", () => {
    expect(valueLabel(null)).toBe("—"); expect(valueLabel(0)).toBe("0");
    expect(statusLabel("started-no-terminal-observation")).toBe("Started · completion unverified");
    expect(statusLabel("started-no-terminal-observation")).not.toContain("Running");
  });
  it("selects only the two explicit same-origin files, never an arbitrary URL", () => {
    expect(snapshotSource("")).toBe("recorded"); expect(snapshotSource("?source=latest")).toBe("latest");
    expect(snapshotSource("?source=recorded")).toBe("recorded");
    expect(() => snapshotSource("?source=https://untrusted.example/data.json")).toThrow();
    expect(statusLabel("stage-started-no-terminal")).not.toContain("Running");
  });
  it.each(["duplicate-slot", "invented-null-loss", "unknown-arm", "unbound-stage"])("rejects %s in a correctly rehashed projection", async kind => {
    const e = actual();
    e.payload.search.candidate_slots = [{ arm: "throughput:parameters", generation: 0, status: "failed", loss: null }];
    if (kind === "duplicate-slot") e.payload.search.candidate_slots.push(structuredClone(e.payload.search.candidate_slots[0]));
    if (kind === "invented-null-loss") e.payload.search.candidate_slots[0].loss = 0;
    if (kind === "unknown-arm") e.payload.search.candidate_slots[0].arm = "invented:method";
    if (kind === "unbound-stage") { e.payload.search.status = "stage-started-no-terminal"; e.payload.search.observed_stage = null; }
    await expect(validatePreScale(await rehash(e))).rejects.toThrow();
  });
  it("rejects changed evidence without a matching checksum", async () => {
    const e = actual(); e.payload.information.worlds[0].scores = { throughput: -999 };
    await expect(validatePreScale(e)).rejects.toThrow("checksum");
  });
  it.each(["fake-complete", "duplicate", "string-seed", "readiness-loss", "early-evaluation", "claim-live"])("rejects %s even with recomputed envelope integrity", async kind => {
    const e = actual();
    if (kind === "fake-complete") { e.payload.information.worlds[0].status = "complete"; e.payload.information.worlds[0].observation_sha256 = null; }
    if (kind === "duplicate") e.payload.information.worlds[1] = structuredClone(e.payload.information.worlds[0]);
    if (kind === "string-seed") e.payload.information.worlds[0].seed = "41001";
    if (kind === "readiness-loss") e.payload.information.numeric_readiness[0].scientific_loss = -5;
    if (kind === "early-evaluation") { e.payload.search.selection_fixed = false; e.payload.search.evaluation_observations = 1; }
    if (kind === "claim-live") e.payload.observation_kind = "live-running-experiment";
    await expect(validatePreScale(await rehash(e))).rejects.toThrow();
  });
});
