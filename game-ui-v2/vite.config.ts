import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    sourcemap: true,
  },
  server: {
    port: 4173,
  },
  test: {
    environment: "node",
    include: ["test/**/*.test.ts"],
  },
});
