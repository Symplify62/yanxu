import { reactive } from "vue";
import type { Employee } from "../domain/types";
import { api } from "../services/api";
import { credentials } from "../services/http";
export const sessions = reactive<{
  employee: Employee | null;
  admin: Employee | null;
}>({ employee: null, admin: null });
export async function login(userId: string, scope: "employee" | "admin") {
  const result = await api.auth.login(userId);
  if (scope === "admin" && !result.user.admin)
    throw new Error("该身份没有管理员资格");
  credentials[scope] = result.token;
  sessions[scope] = result.user;
  sessionStorage.setItem("yanxu-" + scope, result.token);
}
export function clearSession(scope: "employee" | "admin") {
  credentials[scope] = "";
  sessions[scope] = null;
  sessionStorage.removeItem("yanxu-" + scope);
}
export async function logout(scope: "employee" | "admin") {
  try {
    await api.auth.logout(scope);
  } finally {
    clearSession(scope);
  }
}
export async function restore() {
  for (const scope of ["employee", "admin"] as const) {
    credentials[scope] = sessionStorage.getItem("yanxu-" + scope) || "";
    if (credentials[scope])
      try {
        sessions[scope] = await api.auth.me(scope);
      } catch {
        clearSession(scope);
      }
  }
}
