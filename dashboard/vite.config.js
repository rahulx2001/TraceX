// Vite config — production assets served under FastAPI mount /ui (Docker + pilot).
// Dev: open http://127.0.0.1:8787/ui/  (base is /ui/ so paths match the container).
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/ui/",
  // Single-bundle pilot SPA: the shipped dist must provably contain the auth
  // wiring (X-API-Key + protected API paths) in the main chunk, pinned by
  // tests/frontline/test_dashboard_pilot_auth.py. Served locally/Docker, so
  // one ~1MB bundle is an acceptable trade for a verifiable build.
  build: { rolldownOptions: { output: { codeSplitting: false } } },
  server: {
    port: 8787,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/ws": {
        target: "http://127.0.0.1:8000",
        ws: true,
      },
      "/health": "http://127.0.0.1:8000",
    },
  },
});
