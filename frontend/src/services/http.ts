import type { Scope } from "../domain/types";
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message);
  }
}
export const credentials = { employee: "", admin: "" };
export async function http<T>(
  path: string,
  options: { method?: string; body?: unknown; scope?: Scope } = {},
): Promise<T> {
  const scope = options.scope ?? "employee";
  const token =
    scope === "employee" || scope === "admin" ? credentials[scope] : "";
  const response = await fetch("/api/v1" + path, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { "X-Demo-Session": token } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const result = await response.json();
  if (!response.ok) {
    const error = new ApiError(
      response.status,
      result.error?.code ?? "REQUEST_FAILED",
      result.error?.message ?? "请求失败",
    );
    if (response.status === 401 && (scope === "employee" || scope === "admin"))
      window.dispatchEvent(
        new CustomEvent("session-expired", { detail: scope }),
      );
    throw error;
  }
  return result.data as T;
}
