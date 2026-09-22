import { ref } from "vue";
import type { Account } from "./types";

const storageKey = "yanxu-account-session-v1";
const token = ref(sessionStorage.getItem(storageKey) || "");
export const account = ref<Account | null>(null);
export const sessionNotice = ref("");
let generation = 0;
const cleanups = new Set<() => void>();
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export function onSessionClear(fn: () => void) {
  cleanups.add(fn);
  return () => cleanups.delete(fn);
}
export function clearSession(message = "") {
  generation++;
  token.value = "";
  account.value = null;
  sessionStorage.removeItem(storageKey);
  sessionNotice.value = message;
  for (const cleanup of cleanups) cleanup();
}
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const version = generation;
  const headers = new Headers(init.headers);
  if (token.value) headers.set("Authorization", `Bearer ${token.value}`);
  if (typeof init.body === "string")
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers,
      cache: "no-store",
      credentials: "omit",
    });
  } catch {
    throw new ApiError("网络未连接，请稍后重试", 0);
  }
  if (version !== generation) throw new ApiError("会话已切换", 401);
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as {
      detail?: string | { msg: string }[];
    };
    if (response.status === 401 && path !== "/api/auth/login")
      clearSession("登录已失效，请重新登录");
    if (response.status === 403 && path !== "/api/auth/me" && account.value) {
      try {
        account.value = await request<Account>("/api/auth/me");
      } catch {
        /* An expired session is cleared by the shared request path. */
      }
    }
    const message =
      typeof body.detail === "string"
        ? body.detail
        : body.detail?.map((e) => e.msg).join("；");
    throw new ApiError(
      message || `请求未完成（${response.status}）`,
      response.status,
    );
  }
  if (init.headers && new Headers(init.headers).get("Accept") === "audio/wav") {
    const blob = await response.blob();
    if (version !== generation) throw new ApiError("会话已切换", 401);
    return blob as T;
  }
  const data = (await response.json()) as T;
  if (version !== generation) throw new ApiError("会话已切换", 401);
  return data;
}
export async function signIn(username: string, password: string) {
  clearSession();
  const data = await request<{
    accessToken: string;
    expiresAt: number;
    account: Account;
  }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  generation++;
  token.value = data.accessToken;
  sessionStorage.setItem(storageKey, data.accessToken);
  account.value = data.account;
}
export async function restoreSession() {
  if (!token.value) return;
  try {
    account.value = await request<Account>("/api/auth/me");
  } catch (error) {
    clearSession(error instanceof Error ? error.message : "登录未完成");
  }
}
export async function signOut() {
  const current = token.value;
  clearSession();
  const version = generation;
  try {
    const response = await fetch("/api/auth/logout", {
      method: "POST",
      headers: { Authorization: `Bearer ${current}` },
      cache: "no-store",
      credentials: "omit",
    });
    if (!response.ok) throw new Error();
  } catch {
    if (generation === version)
      sessionNotice.value = "本机已退出；服务端会话撤销尚未确认";
  }
}
export const hasPermission = (permission: string) =>
  account.value?.permissions.some((p) => p === permission) ?? false;
export const errorMessage = (error: unknown) =>
  error instanceof Error ? error.message : "操作未完成，请重试";
