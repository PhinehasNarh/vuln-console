import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Dev only; in the compose stack Traefik routes /api to the api service.
      "/api": "http://localhost:8000",
    },
  },
});
