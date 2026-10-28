import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const captures = {
  "noctiluca-v4-review-network-cursor-20000.png": "38a8766980a149cfcec33244a6133e3444684c8ab5314a4ac84d7760cfea1183",
  "noctiluca-v4-publication-funding-cursor-26000.png": "4516ddd36a8da5a295978ccdec13eb8c0417068abf45323de73f532dd4b585b1",
  "noctiluca-v4-publication-evidence-cursor-26000.png": "8d65b81b37cabf8bb7597d35052fb34bab45cd3b2001f9361a77e2d9a7bbb58b",
};

describe("v4 deterministic visual review artifacts", () => {
  for (const [name, expectedHash] of Object.entries(captures)) {
    it(`${name} is the reviewed 1440x1050 PNG`, async () => {
      const bytes = await readFile(fileURLToPath(new URL(`../screenshots/${name}`, import.meta.url)));
      expect(bytes.subarray(1, 4).toString("ascii")).toBe("PNG");
      expect(bytes.readUInt32BE(16)).toBe(1440);
      expect(bytes.readUInt32BE(20)).toBe(1050);
      expect(createHash("sha256").update(bytes).digest("hex")).toBe(expectedHash);
    });
  }
});
