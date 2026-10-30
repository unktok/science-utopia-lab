import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { joinHeldoutOps, parseFrozenSystemGrid, parseHeldoutProgressSnapshot, verifyFrozenSystemGrid, verifyHeldoutProgressSnapshot } from "../src/heldoutContract";

const progressPath = fileURLToPath(new URL("../public/data/held-out-progress.synthetic.json", import.meta.url));
const gridPath = fileURLToPath(new URL("../public/data/held-out-run-grid.synthetic.json", import.meta.url));
const fixture = async (path: string): Promise<any> => JSON.parse(await readFile(path, "utf8"));

describe("metric-conditioned held-out operations contract", () => {
  it("accepts and hash-verifies the versioned synthetic 3 × 5 snapshot", async () => {
    const progress = parseHeldoutProgressSnapshot(await fixture(progressPath));
    const grid = parseFrozenSystemGrid(await fixture(gridPath));
    expect(progress.schema).toBe("scienceutopia.held-out-progress.v1");
    expect(grid.truth_status).toBe("synthetic");
    expect(grid.systems).toHaveLength(3);
    expect(grid.systems.every((system) => system.runs.length === 5 && system.freeze_status === "sealed")).toBe(true);
    expect(progress.progress.counts).toEqual({ complete: 3, failed: 0, planned: 11, running: 1 });
    await expect(verifyHeldoutProgressSnapshot(progress)).resolves.toBeUndefined();
    await expect(verifyFrozenSystemGrid(grid)).resolves.toBeUndefined();
    expect(joinHeldoutOps(progress, grid).grid.systems).toHaveLength(3);
  });

  it("requires one identical held-out split across all frozen systems", async () => {
    const value = await fixture(gridPath) as { systems: Array<{ runs: Array<{ seed: number }> }> };
    value.systems[1]!.runs[0]!.seed = 999;
    expect(() => parseFrozenSystemGrid(value)).toThrow(/identical held-out split/);
  });

  it("rejects result values and provisional winner fields at every depth", async () => {
    for (const [key, value] of [["objective_value", 0.4], ["metric_values", { participation: 0.7 }], ["provisional_winner", "system-a"]] as const) {
      const row = await fixture(gridPath) as Record<string, unknown>;
      row[key] = value;
      expect(() => parseFrozenSystemGrid(row)).toThrow(/forbidden in the result-blind run-grid schema/);
    }
  });

  it("keeps technical failure validity separate from scientific outcome", async () => {
    const value = await fixture(gridPath) as any;
    const run = value.systems[0].runs[0];
    run.status = "technical_failed";
    run.wall_seconds = null;
    run.failure_id = "failure-001";
    value.technical_failures = [{ id: "failure-001", run_id: run.run_id, system_id: value.systems[0].system_id, seed: run.seed, category: "transport_timeout", retryable: true }];
    const parsed = parseFrozenSystemGrid(value);
    expect(parsed.technical_failures[0]!.category).toBe("transport_timeout");
    expect(parsed.systems[0]!.runs[0]).not.toHaveProperty("metric_values");
  });

  it("fails closed when the formal active run does not match the run-grid", async () => {
    const progressValue = await fixture(progressPath);
    progressValue.progress.active_runs[0].run_id = "unknown-run";
    const progress = parseHeldoutProgressSnapshot(progressValue);
    const grid = parseFrozenSystemGrid(await fixture(gridPath));
    expect(() => joinHeldoutOps(progress, grid)).toThrow(/active runs disagree/);
  });

  it("declares the browser boundary and semantic regions", async () => {
    const html = await readFile(fileURLToPath(new URL("../heldout.html", import.meta.url)), "utf8");
    const source = await readFile(fileURLToPath(new URL("../src/heldout.ts", import.meta.url)), "utf8");
    expect(html).toContain("THREE SCIENCE SYSTEMS ENTER THE SAME WEATHER");
    expect(html).toContain("TECHNICAL FAILURE BAY");
    expect(html).toContain("EVIDENCE QUARANTINE");
    expect(html).toContain("PROVISIONAL WINNER</dt><dd>NOT A VALID OBJECT");
    expect(source).toContain('fetch("/data/held-out-progress.synthetic.json"');
    expect(source).toContain('fetch("/data/held-out-run-grid.synthetic.json"');
    expect(source).not.toMatch(/sqlite|campaign-state|outputs\//i);
  });
});
