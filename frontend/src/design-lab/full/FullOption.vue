<script setup lang="ts">
import { ref, provide, onMounted, onUnmounted, watch } from "vue";
import TabletOption from "../TabletOption.vue";
import EmployeeApp from "./EmployeeApp.vue";
import AdminApp from "./AdminApp.vue";
import ComponentGallery from "./ComponentGallery.vue";
import { kitKey, type Kit } from "./context";
import { api } from "../../services/api";
import { clearAccounts } from "./account";
import type { Scenario } from "../../domain/types";
import "./full.css";
const props = defineProps<{ variant: string; kit: Kit }>();
provide(kitKey, props.kit);
const surfaces = ["tablet", "employee", "admin", "components"];
const initial = new URLSearchParams(location.search).get("surface") || "tablet";
const surface = ref(surfaces.includes(initial) ? initial : "tablet"),
  epoch = ref(0),
  error = ref("");
function report() {
  window.parent.postMessage(
    { type: "yanxu-full-ready", surface: surface.value },
    location.origin,
  );
}
async function message(e: MessageEvent) {
  if (
    e.origin !== location.origin ||
    e.source !== window.parent ||
    e.data?.type !== "yanxu-design"
  )
    return;
  if (e.data.action === "navigate" && surfaces.includes(e.data.surface)) {
    surface.value = e.data.surface;
    report();
  }
  if (e.data.action === "full-reset") {
    try {
      await api.demo.reset();
      clearAccounts();
      epoch.value++;
      error.value = "";
      report();
    } catch (err) {
      error.value = (err as Error).message;
    }
  }
  if (e.data.action === "scenario") {
    try {
      await api.demo.settings({ scenario: e.data.value as Scenario });
      error.value = "";
    } catch (err) {
      error.value = (err as Error).message;
    }
  }
}
onMounted(() => {
  window.addEventListener("message", message);
  report();
});
onUnmounted(() => window.removeEventListener("message", message));
watch(
  surface,
  () => {
    document.documentElement.dataset.surface = surface.value;
  },
  { immediate: true },
);
</script>
<template>
  <div class="full-app" :class="variant">
    <p v-if="error" role="alert" class="error-banner">{{ error }}</p>
    <div :key="epoch">
      <TabletOption
        v-if="surface === 'tablet'"
        :variant="variant"
        :kit="kit"
      /><EmployeeApp v-else-if="surface === 'employee'" /><AdminApp
        v-else-if="surface === 'admin'"
      /><ComponentGallery v-else />
    </div>
  </div>
</template>
