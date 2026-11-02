import { defineConfig } from "vitest/config";
import { resolve } from "node:path";

export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    sourcemap: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, "index.html"),
        compare: resolve(__dirname, "compare.html"),
        sandbox: resolve(__dirname, "sandbox.html"),
        mission: resolve(__dirname, "mission.html"),
        heldout: resolve(__dirname, "heldout.html"),
        hub: resolve(__dirname, "hub.html"),
        generative: resolve(__dirname, "generative.html"),
        native: resolve(__dirname, "native.html"),
        lifecycle: resolve(__dirname, "lifecycle.html"),
        openEvidence: resolve(__dirname, "open-evidence.html"),
        objectiveStructure: resolve(__dirname, "objective-structure.html"),
        methodObservatory: resolve(__dirname, "method-observatory.html"),
      },
    },
  },
  server: {
    port: 4173,
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
