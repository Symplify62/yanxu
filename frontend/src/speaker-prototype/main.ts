import { createApp } from "vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";
import "../styles/a-theme.css";
import "../styles/a-layout.css";
import App from "./SpeakerPrototype.vue";
import "./speakers.css";
import "./redesign.css";

document.documentElement.dataset.design = "element";
createApp(App).use(ElementPlus).mount("#app");
