import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import QRCode from "qrcode";
import { api } from "../services/api";
import { usePolling } from "../composables/usePolling";
import type { DemoConfig, DeviceView } from "../domain/types";
export function useTabletDemo() {
  const {
    data: device,
    error,
    loading,
    refresh,
  } = usePolling(api.device.get, 800);
  const config = ref<DemoConfig>(),
    department = ref(""),
    scanUser = ref("lin"),
    dialog = ref(false),
    busy = ref(false),
    actionError = ref(""),
    qr = ref(""),
    clock = ref(Date.now());
  let timer: ReturnType<typeof setInterval>;
  const expired = computed(
    () => !!device.value && device.value.expiresAt <= clock.value,
  );
  const people = computed(
    () =>
      config.value?.people
        .filter((p) => !p.admin)
        .map((p) => ({ value: p.id, label: p.name })) || [],
  );
  const departments = computed(
    () =>
      device.value?.allowedDepartments.map((id) => ({
        value: id,
        label: config.value?.departments.find((d) => d.id === id)?.name || id,
      })) || [],
  );
  async function run(fn: () => Promise<DeviceView>) {
    if (busy.value) return;
    busy.value = true;
    actionError.value = "";
    try {
      device.value = await fn();
      return true;
    } catch (e) {
      actionError.value = (e as Error).message;
      return false;
    } finally {
      busy.value = false;
    }
  }
  async function scan() {
    if (!device.value) return;
    const ok = await run(() =>
      api.device.scan(device.value!.challenge, scanUser.value),
    );
    if (ok) dialog.value = false;
  }
  function openScan() {
    if (
      device.value?.phase !== "scan" ||
      expired.value ||
      !device.value?.online
    )
      return;
    actionError.value = "";
    dialog.value = true;
  }
  async function reset() {
    if (busy.value) return;
    dialog.value = false;
    actionError.value = "";
    await run(async () => {
      await api.demo.reset();
      config.value = await api.demo.config();
      return api.device.get();
    });
  }
  function message(e: MessageEvent) {
    if (
      e.origin !== location.origin ||
      e.source !== window.parent ||
      e.data?.type !== "yanxu-design"
    )
      return;
    if (e.data.action === "scan") openScan();
    if (e.data.action === "expire" && device.value?.phase === "scan")
      void run(() => api.device.action("expire"));
    if (e.data.action === "reset") void reset();
  }
  watch(
    () => device.value?.employee,
    () => {
      department.value = device.value?.department || "";
    },
  );
  watch(
    () => device.value?.phase,
    (phase) => {
      if (phase)
        window.parent.postMessage(
          { type: "yanxu-design-state", phase },
          location.origin,
        );
    },
  );
  watch(
    () => device.value?.challenge,
    async (challenge) => {
      if (challenge)
        qr.value = await QRCode.toDataURL(
          "YANXU-DEMO-NOT-A-LOGIN:" + challenge,
          {
            width: 240,
            margin: 2,
            color: { dark: "#222b26", light: "#ffffff" },
          },
        );
    },
  );
  onMounted(() => {
    window.addEventListener("message", message);
    timer = setInterval(() => (clock.value = Date.now()), 500);
    void api.demo
      .config()
      .then((v) => (config.value = v))
      .catch((e) => (actionError.value = e.message));
  });
  onUnmounted(() => {
    clearInterval(timer);
    window.removeEventListener("message", message);
  });
  return {
    device,
    error,
    loading,
    refresh,
    department,
    scanUser,
    dialog,
    busy,
    actionError,
    qr,
    expired,
    people,
    departments,
    run,
    scan,
  };
}
