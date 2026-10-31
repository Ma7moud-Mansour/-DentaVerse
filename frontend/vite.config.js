import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiTarget = process.env.DENTAVERSE_API_URL || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: Number(process.env.DENTAVERSE_UI_PORT || 5173),
    strictPort: true,
    proxy: {
      "/api": apiTarget,
      "/ws": { target: apiTarget.replace(/^http/, "ws"), ws: true },
    },
  },
});
