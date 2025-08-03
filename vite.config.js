import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  base: "./",
  server: {
    host: true, // allow external access (needed for Gitpod URLs)
    strictPort: false,
    port: 3000,
    allowedHosts: [
      ".gitpod.io", // allow all Gitpod-generated preview URLs
    ],
  },
  build: {
    outDir: "build",
  },
});
