import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const captures = {
  "noctiluca-v4-review-network-cursor-20000.png": "38a8766980a149cfcec33244a6133e3444684c8ab5314a4ac84d7760cfea1183",
  "noctiluca-v4-publication-funding-cursor-26000.png": "4516ddd36a8da5a295978ccdec13eb8c0417068abf45323de73f532dd4b585b1",
  "noctiluca-v4-publication-evidence-cursor-26000.png": "8d65b81b37cabf8bb7597d35052fb34bab45cd3b2001f9361a77e2d9a7bbb58b",
  "noctiluca-completed-campaign-seed521-cursor-9000.png": "eb984c5aaadc69aeddb5b9b5d07b840e85f7649c1a19bef0fba7bf7e518aa923",
  "noctiluca-cinematic-review-seed521-cursor-20000.png": "5a20b9df6775a814974cd9a4a428d1cbc9f870b71ff42c1a24d5d97dfe9551ea",
  "noctiluca-cinematic-funding-seed521-cursor-42000.png": "f5fd5245077c45c503d16586038eba0a9623acb80c0e97b3714b5c3686d98cd1",
  "noctiluca-epistemic-review-seed521-cursor-21000.png": "db48e5764458655d5dc4a9842642bd4b9e0ad710f82380de73390f92b1ef8b81",
  "noctiluca-epistemic-application-seed521-cursor-36500.png": "33680042350acf333af329822976b05121c4da0ed514e9eb90398bd097147fe7",
  "noctiluca-epistemic-award-seed521-cursor-42000.png": "f6d1e26f6e13ffb9deaa21f98457e6223808c46a3c204f1cc8899592ba20daf5",
  "noctiluca-life-writing-seed521-cursor-6200.png": "bbcb21a6f4e9f18216d6bf47ce1dfdd0a1e51e9cfbb318b41fa202b48623a584",
  "noctiluca-life-review-seed521-cursor-20200.png": "1da1e23bb561fcf0e270665e3bf8bb450067c54d997adc3a8c380229e5bf91a7",
  "noctiluca-life-application-seed521-cursor-36500.png": "0a0393ac54e5ad2b0933a91ad8a6f83b5ce86e46d586e098b37da39ec2069937",
  "noctiluca-system-sandbox-valid.png": "835da7a83355eff5b338fc262d6b3905408d7c4dfb767a47c7b049f70d9604f3",
  "noctiluca-system-sandbox-invalid-publication.png": "d0007a200d82ce38633dcb1bc7e9c21c87e1a51ca96aeb42768b47dce42bc047",
  "noctiluca-optimization-mission-verified.png": "de0f3bac244fad8229ffc7fdfc337947f8e1bdb5ce127b6bcc25ce93508d41e4",
  "noctiluca-optimization-mission-synthetic.png": "c32572a8c905cba705e69dfdfdbbb75546db0b006f759354051808e89c8e25eb",
  "noctiluca-arcology-hub.png": "8b59639a5ee2c1553d40db99617808ac96986cc26ab59321a9b9aa9d6489beb1",
  "noctiluca-arcology-hub-system-foundry.png": "2a7dc8db1aba35a94fc0338ed9c3ef7a5fecc91d7b7e526e3857c3042f45413c",
  "noctiluca-evidence-quay-review-seed521-cursor-20200.png": "d0a1aeec6f9d90b9e0a930f2e44011022c138a5e0e9106ccd378b9b18bd5d530",
  "noctiluca-evidence-quay-funding-seed521-cursor-36500.png": "bb440d6db67ff7bac71811a0c8238dcbab889e5f510c6952610bd12cdf197ff6",
  "noctiluca-institution-interior-writing-seed521-cursor-6200.png": "386e32d44b3c94bbe99a5343f0ae0968e0eceb5386ccd0d5e5858f29e47368a6",
  "noctiluca-institution-interior-review-seed521-cursor-20200.png": "8a5c715a3dddaebd0b71b2cf4c02a75dc31a747f92fa860c413a2d7c42a5a236",
  "noctiluca-institution-interior-funding-seed521-cursor-36500.png": "b952e4e69f74fe08d1880de6de7bc68209d7e3461cc477031f11e73ab8e52d94",
  "noctiluca-researcher-dossier-inactive-seed521-cursor-47000.png": "253a7a2c85cf97e666fa0ada5f74105d4e71124ec91cdfeec166921863e0e5f2",
  "noctiluca-researcher-dossier-author-seed521-cursor-47000.png": "8f799f72a92d0b460f2583f4d8c4e7c11fc3b3c5200b6ce5a060f0ba2f915824",
  "noctiluca-evidence-graph-artifact-seed521-cursor-47000.png": "587064a7f46b8207b50ab7b3ac3bc5ef39010105c15a9132af24e4dd1f3d9485",
  "noctiluca-evidence-graph-funding-seed521-cursor-47000.png": "00cb4f7ab85131b305880bdd63752ea94d001389150e6d5a2b6e6f47aeebf6c5",
};

describe("deterministic visual review artifacts", () => {
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
