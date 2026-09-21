import { createApp } from "vue";
import App from "./PhaseOneApp.vue";
import "../styles/a-theme.css";
import "../styles/a-layout.css";
import "../styles/records.css";
document.documentElement.dataset.design = "element";
createApp(App).mount("#app");
