import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import Components from "unplugin-vue-components/vite";
import {
  ElementPlusResolver,
  VantResolver,
} from "unplugin-vue-components/resolvers";
export default defineConfig({
  plugins: [
    vue(),
    Components({
      resolvers: [ElementPlusResolver(), VantResolver()],
      dts: "src/components.d.ts",
    }),
  ],
  // Component resolvers add pure-ESM style imports lazily. Avoid discovery-triggered page reloads.
  optimizeDeps: {
    noDiscovery: true,
    include: [
      "vue",
      "vue-router",
      "element-plus/es",
      "vant/es",
      "msw",
      "msw/browser",
      "dayjs",
      "qrcode",
      "@lucide/vue",
    ],
  },
  build: {
    rolldownOptions: {
      input: {
        main: "index.html",
        prototype: "prototype.html",
        phaseOne: "phase-one.html",
        public: "public.html",
        account: "account.html",
        option: "design-option.html",
      },
    },
  },
  test: { include: ["tests/**/*.test.ts"], environment: "node" },
  server: { host: "127.0.0.1", port: 5178, strictPort: true },
});
