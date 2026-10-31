import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseNativeLab } from "../src/nativeContract";

const envelope = () => JSON.parse(readFileSync(new URL("../public/data/native-design-lab-v1.json", import.meta.url), "utf8"));
function changed(edit: (data: any) => void) {
  const source = envelope(), data = JSON.parse(source.payload_json); edit(data);
  const payload_json = JSON.stringify(data);
  return { ...source, payload_json, payload_sha256: createHash("sha256").update(payload_json).digest("hex") };
}
describe("native institution evidence", () => {
  it("loads real native worlds and their source/protocol/wiring difference", async () => {
    const lab = await parseNativeLab(envelope());
    expect(lab.systems.length).toBe(2);
    expect(lab.systems[1]!.runs[0]!.frames.length).toBeGreaterThan(0);
    expect(lab.systems[1]!.spec.mechanisms.some(n => n.implementation === "code.python.v1")).toBe(true);
  });
  it("rejects modified raw evidence", async () => {
    const value = envelope(); value.payload_json += " ";
    await expect(parseNativeLab(value)).rejects.toThrow("hash mismatch");
  });
  it("independently matches the exact SystemSpec bytes to its fingerprint", async () => {
    await expect(parseNativeLab(changed(data => data.systems[0].system_spec_json += " "))).rejects.toThrow("fingerprint mismatch");
  });
  it.each(["model_weights_trained", "full_native_world_autograd", "live_player_intervention"])("rejects false claim %s", async key => {
    await expect(parseNativeLab(changed(data => data.interpretation[key] = true))).rejects.toThrow("Unsupported");
  });
  it("does not invent activity when execution evidence is missing", async () => {
    await expect(parseNativeLab(changed(data => data.systems[0].runs[0].frames = []))).rejects.toThrow("Missing native execution");
  });
  it("does not turn a technical failure into a numeric loss", async () => {
    await expect(parseNativeLab(changed(data => data.systems[0].status = "failed"))).rejects.toThrow("status/loss mismatch");
  });
});
