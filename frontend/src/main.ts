import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import { restore } from "./composables/session";
import "./styles/tokens.css";
import "./styles/app.css";
async function boot() {
  if (location.pathname === "/") {
    location.replace("/prototype.html");
    return;
  }
  if (import.meta.env.VITE_MOCKS !== "true")
    throw new Error("真实服务未配置，此原型只能在模拟模式运行。");
  const { startMocks } = await import("./mocks/browser");
  await startMocks();
  await restore();
  const app = createApp(App);
  app.use(router);
  await router.isReady();
  app.mount("#app");
}
boot().catch((error) => {
  document.querySelector("#app")!.textContent =
    "原型启动失败：" + String(error);
});
