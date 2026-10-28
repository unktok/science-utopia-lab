import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { canonicalHash } from "../src/hash";
import {
  initialSandboxState,
  materializeSystemSpec,
  parseSandboxBundle,
  validateSystemSpec,
  verifySandboxBundle,
} from "../src/systemSandbox";

const contractUrl = new URL("../public/data/system-sandbox.contract.json", import.meta.url);
const pageUrl = new URL("../sandbox.html", import.meta.url);

async function contract() {
  return parseSandboxBundle(JSON.parse(await readFile(fileURLToPath(contractUrl), "utf8")));
}

describe("synthetic SystemSpec sandbox contract", () => {
  it("matches Python fingerprints and validation reports", async () => {
    const bundle = await contract();
    await expect(verifySandboxBundle(bundle)).resolves.toBeUndefined();
    expect(bundle.node_catalog.map((node) => node.mechanism_id).sort()).toEqual([
      "communication", "evaluation", "funding", "government", "publication",
    ]);
    expect(bundle.authoritative_fixtures[0]?.fingerprint).toBe("9a6262161548ff0a80897f29b62fad2988df02360c2b4812a1e24bf4f87c5314");
  });

  it("changes complete-system identity for implementation and latency edits", async () => {
    const bundle = await contract();
    const state = initialSandboxState(bundle);
    const base = materializeSystemSpec(bundle, state);
    const baseHash = await canonicalHash(base);
    state.nodes.evaluation!.implementation = "sandbox.evaluation.partial-lottery-v1";
    const implementationHash = await canonicalHash(materializeSystemSpec(bundle, state));
    state.edges["edge:2"]!.latency = 2;
    const latencyHash = await canonicalHash(materializeSystemSpec(bundle, state));
    expect(new Set([baseHash, implementationHash, latencyHash]).size).toBe(3);
  });

  it("surfaces an authoritative-style issue when a required edge is disabled", async () => {
    const bundle = await contract();
    const state = initialSandboxState(bundle);
    state.edges["edge:3"]!.enabled = false;
    const report = validateSystemSpec(materializeSystemSpec(bundle, state));
    expect(report.valid).toBe(false);
    expect(report.issues.map((issue) => issue.code)).toContain("unconnected_required_input");
  });

  it("fails closed when the synthetic contract claims a different provenance", async () => {
    const raw = JSON.parse(await readFile(fileURLToPath(contractUrl), "utf8")) as Record<string, unknown>;
    raw.truth_status = "canonical";
    expect(() => parseSandboxBundle(raw)).toThrow(/may not claim verified or empirical provenance/);
  });

  it("keeps claim boundaries and keyboard landmarks in the static shell", async () => {
    const html = await readFile(fileURLToPath(pageUrl), "utf8");
    expect(html).toContain("SYNTHETIC SANDBOX");
    expect(html).toContain("STRUCTURE ≠ OUTCOME");
    expect(html).toContain('class="skip-link"');
    expect(html).toContain('id="sandbox-controls"');
    expect(html).toContain('role="status"');
    expect(html).toContain('id="reset-spec"');
    expect(html).toContain('id="break-publication"');
  });
});
