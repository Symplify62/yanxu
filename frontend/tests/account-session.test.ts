import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Account } from "../src/account/types";

const storageKey = "yanxu-account-session-v1";
let storage: Map<string, string>;

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => {
    resolve = done;
  });
  return { promise, resolve };
}

function identity(username: string): Account {
  return {
    id: `account-${username}`,
    username,
    personId: `person-${username}`,
    displayName: username,
    permissions: username === "second" ? ["record"] : [],
  };
}

function jsonResponse(value: unknown, status = 200) {
  return new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  vi.resetModules();
  storage = new Map();
  vi.stubGlobal("sessionStorage", {
    getItem: (key: string) => storage.get(key) ?? null,
    setItem: (key: string, value: string) => storage.set(key, value),
    removeItem: (key: string) => storage.delete(key),
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("账号切换时延迟返回的响应正文", () => {
  it.each([401, 403, 200])(
    "旧请求的 %i 正文不得影响新账号会话或触发身份刷新",
    async (status) => {
      const body = deferred<unknown>();
      const readingBody = deferred<void>();
      const delayed = new Response(null, { status });
      vi.spyOn(delayed, "json").mockImplementation(() => {
        readingBody.resolve();
        return body.promise;
      });
      const fetchMock = vi.fn(async (path: string, init?: RequestInit) => {
        if (path === "/api/auth/login") {
          const { username } = JSON.parse(String(init?.body));
          return jsonResponse({
            accessToken: `token-${username}`,
            account: identity(username),
            expiresAt: 9999999999,
          });
        }
        if (path === "/api/auth/logout") return jsonResponse({ ok: true });
        if (path === "/api/auth/password") return delayed;
        if (path === "/api/auth/me") {
          // A stale 403 must not trigger even a new-account refresh.
          return jsonResponse({ ...identity("second"), permissions: [] });
        }
        throw new Error(`Unexpected request: ${path}`);
      });
      vi.stubGlobal("fetch", fetchMock);
      const api = await import("../src/account/api");
      const sessionCleared = vi.fn();
      api.onSessionClear(sessionCleared);
      await api.signIn("first", "fictional-password");
      const result = api
        .request("/api/auth/password", { method: "POST", body: "{}" })
        .then(
          (data) => ({ data, error: null }),
          (error: unknown) => ({ data: null, error }),
        );

      // Headers have arrived and passed the first session check; only JSON waits.
      await readingBody.promise;
      await api.signOut();
      await api.signIn("second", "fictional-password");
      const newToken = storage.get(storageKey);
      const cleanupCount = sessionCleared.mock.calls.length;
      expect(api.account.value).toEqual(identity("second"));
      body.resolve(status === 200 ? { ok: true } : { detail: "旧请求错误" });

      const response = await result;
      expect(api.account.value).toEqual(identity("second"));
      expect(storage.get(storageKey)).toBe(newToken);
      expect(newToken).toBe("token-second");
      expect(api.sessionNotice.value).toBe("");
      expect(sessionCleared).toHaveBeenCalledTimes(cleanupCount);
      expect(response.data).toBeNull();
      expect(response.error).toBeInstanceOf(api.ApiError);
      expect(response.error).toMatchObject({
        status: 401,
        message: "会话已切换",
      });
      expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
        "/api/auth/login",
        "/api/auth/password",
        "/api/auth/logout",
        "/api/auth/login",
      ]);
      const changeHeaders = new Headers(fetchMock.mock.calls[1]?.[1]?.headers);
      expect(changeHeaders.get("Authorization")).toBe("Bearer token-first");
    },
  );
});
