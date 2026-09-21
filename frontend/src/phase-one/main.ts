import { createApp } from "vue";
import App from "./PhaseOneApp.vue";
import "../design-lab/option.css";
import "../design-lab/full/full.css";
import "./phase-one.css";
document.documentElement.dataset.design = "element";
createApp(App).mount("#app");
