import { createRouter, createWebHistory } from "vue-router";
import { sessions, clearSession } from "./composables/session";
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", redirect: "/tablet" },
    { path: "/tablet", component: () => import("./pages/TabletPage.vue") },
    {
      path: "/employee/login",
      component: () => import("./pages/LoginPage.vue"),
      props: { scope: "employee" },
    },
    {
      path: "/employee",
      component: () => import("./pages/MeetingListPage.vue"),
      meta: { scope: "employee" },
    },
    {
      path: "/employee/meetings/:id",
      component: () => import("./pages/MeetingDetailPage.vue"),
      meta: { scope: "employee" },
    },
    {
      path: "/admin/login",
      component: () => import("./pages/LoginPage.vue"),
      props: { scope: "admin" },
    },
    {
      path: "/admin",
      component: () => import("./pages/admin/AdminShell.vue"),
      meta: { scope: "admin" },
      children: [
        { path: "", redirect: "/admin/overview" },
        {
          path: "overview",
          component: () => import("./pages/admin/OverviewPage.vue"),
        },
        {
          path: "people",
          component: () => import("./pages/admin/PeoplePage.vue"),
        },
        {
          path: "organization",
          component: () => import("./pages/admin/PeoplePage.vue"),
          props: { organization: true },
        },
        {
          path: "roles",
          component: () => import("./pages/admin/AccessPage.vue"),
          props: { kind: "roles" },
        },
        {
          path: "groups",
          component: () => import("./pages/admin/AccessPage.vue"),
          props: { kind: "groups" },
        },
        {
          path: "routes",
          component: () => import("./pages/admin/RoutingPage.vue"),
        },
        {
          path: "exceptions",
          component: () => import("./pages/admin/OperationsPage.vue"),
        },
        {
          path: "audit",
          component: () => import("./pages/admin/AuditPage.vue"),
        },
        {
          path: "devices",
          component: () => import("./pages/admin/DevicesPage.vue"),
        },
      ],
    },
    {
      path: "/components",
      component: () => import("./pages/ComponentsPage.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/tablet" },
  ],
});
router.beforeEach((to) => {
  const scope = to.meta.scope as "employee" | "admin" | undefined;
  if (scope && !sessions[scope])
    return { path: "/" + scope + "/login", query: { returnTo: to.fullPath } };
});
window.addEventListener("session-expired", (event) => {
  const scope = (event as CustomEvent).detail as "employee" | "admin";
  clearSession(scope);
  if (router.currentRoute.value.meta.scope === scope)
    void router.replace({
      path: "/" + scope + "/login",
      query: { expired: "1" },
    });
});
