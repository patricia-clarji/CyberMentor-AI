import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
const trustedApiOrigin =
  process.env.CYBERMENTOR_TRUSTED_API_ORIGIN || "http://127.0.0.1:8010";
const legacyApiOrigin =
  process.env.CYBERMENTOR_LEGACY_API_ORIGIN || "http://127.0.0.1:8787";
const localHost = process.env.CYBERMENTOR_LOCAL_HOST || "127.0.0.1";
const webPort = Number(process.env.CYBERMENTOR_WEB_PORT || 5173);
export default defineConfig({
  plugins: [react()],
  server: {
    port: webPort,
    strictPort: true,
    host: localHost,
    proxy: {
      "/api/v1": trustedApiOrigin,
      "/api": legacyApiOrigin,
    },
  },
  preview: { port: 4173, host: "127.0.0.1" },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    pool: "forks",
    fileParallelism: false,
    maxWorkers: 1,
    testTimeout: 120_000,
    hookTimeout: 120_000,
  },
});
