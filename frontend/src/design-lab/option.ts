import { createApp } from "vue";
import FullOption from "./full/FullOption.vue";
import * as kit from "./kits/element";
import "../styles/a-theme.css";
import { startMocks } from "../mocks/browser";
document.documentElement.dataset.design = "element";
async function boot() {
  if (import.meta.env.VITE_MOCKS !== "true")
    throw new Error("设计样板仅支持模拟环境");
  await startMocks();
  createApp(FullOption, { variant: "element", kit }).mount("#app");
}
void boot().catch(() => {
  document.getElementById("app")!.textContent =
    "样板暂时无法加载，请刷新重试。";
});
