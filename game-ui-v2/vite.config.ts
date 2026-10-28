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
