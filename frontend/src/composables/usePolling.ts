import { onMounted, onUnmounted, ref, shallowRef } from "vue";
export function usePolling<T>(fetcher: () => Promise<T>, interval = 1600) {
  const data = shallowRef<T | null>(null),
    error = ref(""),
    loading = ref(true);
  let active = true,
    inFlight = false,
    timer: ReturnType<typeof setInterval> | undefined;
  async function refresh() {
    if (inFlight || !active) return;
    inFlight = true;
    try {
      const value = await fetcher();
      if (active) {
        data.value = value;
        error.value = "";
      }
    } catch (e) {
      if (active) {
        data.value = null;
        error.value = e instanceof Error ? e.message : "请求失败";
      }
    } finally {
      if (active) loading.value = false;
      inFlight = false;
    }
  }
  onMounted(() => {
    void refresh();
    if (interval) timer = setInterval(() => void refresh(), interval);
  });
  onUnmounted(() => {
    active = false;
    if (timer) clearInterval(timer);
  });
  return { data, error, loading, refresh };
}
