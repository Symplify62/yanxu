import { setupWorker } from "msw/browser";
import { handlers } from "./handlers";
export const worker = setupWorker(...handlers);
export async function startMocks() {
  await worker.start({
    quiet: true,
    onUnhandledRequest(request) {
      if (new URL(request.url).pathname.startsWith("/api/"))
        throw new Error("未定义的模拟API已阻止：" + request.url);
    },
  });
}
