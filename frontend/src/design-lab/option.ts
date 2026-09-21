import { createApp } from "vue";
import TabletOption from "./TabletOption.vue";
import "./option.css";
import { startMocks } from "../mocks/browser";
const value = new URLSearchParams(location.search).get("variant");
const variant = value === "shadcn" || value === "tdesign" ? value : "element";
document.documentElement.dataset.design = variant;
const kits = {
  element: () => import("./kits/element"),
  shadcn: () => import("./kits/shadcn"),
  tdesign: () => import("./kits/tdesign"),
};
async function boot() {
  if (import.meta.env.VITE_MOCKS !== "true")
    throw new Error("设计样板仅支持模拟环境");
  const kit = await kits[variant]();
  await startMocks();
  if (variant === "tdesign")
    createApp(TabletOption, { variant, kit }).mount("#app");
  else {
    const { default: FullOption } = await import("./full/FullOption.vue");
    createApp(FullOption, {
      variant,
      kit: kit as import("./full/context").Kit,
    }).mount("#app");
  }
}
void boot().catch(() => {
  document.getElementById("app")!.textContent =
    "样板暂时无法加载，请刷新重试。";
});
