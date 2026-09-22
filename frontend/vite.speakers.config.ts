import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

// Isolated review build. Never add this entry to the public production build.
export default defineConfig({
  plugins: [vue()],
  server: { host: "127.0.0.1", port: 5180, strictPort: true },
  build: {
    outDir: "../.local-data/speaker-prototype-dist",
    emptyOutDir: true,
    rolldownOptions: { input: "speaker-prototype.html" },
  },
});
