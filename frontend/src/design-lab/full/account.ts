import { reactive } from "vue";
import type { Employee } from "../../domain/types";
import { api } from "../../services/api";
import { credentials } from "../../services/http";
export const accounts = reactive<{
  employee: Employee | null;
  admin: Employee | null;
}>({ employee: null, admin: null });
export async function signIn(id: string, scope: "employee" | "admin") {
  const result = await api.auth.login(id);
  if (scope === "admin" && !result.user.admin)
    throw new Error("该身份没有管理员资格");
  credentials[scope] = result.token;
  accounts[scope] = result.user;
}
export async function signOut(scope: "employee" | "admin") {
  try {
    await api.auth.logout(scope);
  } finally {
    credentials[scope] = "";
    accounts[scope] = null;
  }
}
export function clearAccounts() {
  credentials.employee = "";
  credentials.admin = "";
  accounts.employee = null;
  accounts.admin = null;
}
window.addEventListener("session-expired", (e) => {
  const scope = (e as CustomEvent).detail as "employee" | "admin";
  credentials[scope] = "";
  accounts[scope] = null;
});
