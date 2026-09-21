import { computed, ref, watch } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import { accounts } from "./account";
import { isException, statusLabels } from "../../domain/presentation";
import type { AdminData, Employee, Role, Group } from "../../domain/types";
import type { Column } from "./context";
export const sections = [
  ["overview", "自动处理概览"],
  ["people", "用户与身份"],
  ["organization", "组织部门"],
  ["roles", "角色权限"],
  ["groups", "业务访问组"],
  ["routes", "部门与接收群"],
  ["exceptions", "异常处理"],
  ["audit", "操作记录"],
  ["devices", "设备与存储"],
];
export function useAdminModel() {
  const section = ref("overview"),
    query = ref(""),
    department = ref("company"),
    modal = ref(""),
    busy = ref(false),
    message = ref(""),
    mutationError = ref("");
  const { data, error, loading, refresh } = usePolling(
    () => (accounts.admin ? api.admin.get() : Promise.resolve(null)),
    1200,
  );
  const { data: device } = usePolling(
    () => (accounts.admin ? api.device.get() : Promise.resolve(null)),
    1500,
  );
  watch(
    () => accounts.admin?.id,
    () => {
      modal.value = "";
      data.value = null;
      void refresh();
    },
  );
  watch(section, () => {
    query.value = "";
    message.value = "";
  });
  const deptName = (id: string) =>
    data.value?.departments.find((d) => d.id === id)?.name || id;
  const peopleName = (id: string) =>
    data.value?.people.find((p) => p.id === id)?.name || id;
  const metrics = computed(() => [
    { label: "会议记录", value: data.value?.jobs.length || 0 },
    {
      label: "自动完成",
      value: data.value?.jobs.filter((j) => j.state === "ACCEPTED").length || 0,
    },
    {
      label: "处理中",
      value:
        data.value?.jobs.filter(
          (j) => j.state !== "ACCEPTED" && !isException(j.state),
        ).length || 0,
    },
    {
      label: "需要关注",
      value: data.value?.jobs.filter((j) => isException(j.state)).length || 0,
    },
  ]);
  const columns = computed<Column[]>(() => {
    if (section.value === "people" || section.value === "organization")
      return [
        { key: "name", label: "员工", width: 150 },
        { key: "departmentName", label: "所属部门" },
        { key: "registeredLabel", label: "开户状态", width: 170 },
        { key: "status", label: "账号状态", width: 105 },
        { key: "action", label: "操作", width: 110 },
      ];
    if (section.value === "roles")
      return [
        { key: "name", label: "角色", width: 180 },
        { key: "permissionsLabel", label: "功能权限", width: 320 },
        { key: "action", label: "操作", width: 130 },
      ];
    if (section.value === "groups")
      return [
        { key: "name", label: "访问组", width: 180 },
        { key: "membersLabel", label: "组内成员", width: 320 },
        { key: "action", label: "操作", width: 130 },
      ];
    if (section.value === "routes")
      return [
        { key: "name", label: "会议归属", width: 160 },
        { key: "target", label: "接收群", width: 240 },
        { key: "mode", label: "发送方式", width: 180 },
        { key: "action", label: "操作", width: 140 },
      ];
    if (section.value === "audit")
      return [
        { key: "timeLabel", label: "时间", width: 130 },
        { key: "action", label: "动作", width: 200 },
        { key: "detail", label: "对象与说明", width: 350 },
      ];
    return [
      { key: "id", label: "记录编号", width: 150 },
      { key: "departmentName", label: "会议归属", width: 130 },
      { key: "status", label: "处理状态", width: 220 },
      { key: "attempts", label: "自动尝试", width: 110 },
      {
        key: section.value === "exceptions" ? "action" : "sendCount",
        label: section.value === "exceptions" ? "处理" : "发送次数",
        width: 170,
      },
    ];
  });
  const rows = computed<Record<string, unknown>[]>(() => {
    if (!data.value) return [];
    if (section.value === "people" || section.value === "organization")
      return data.value.people
        .filter(
          (p) =>
            (section.value !== "organization" ||
              department.value === "company" ||
              p.department === department.value) &&
            p.name.includes(query.value),
        )
        .map((p) => ({
          ...p,
          departmentName: deptName(p.department),
          registeredLabel: p.registered ? "已自动开户" : "首次登录自动开通",
          status: p.active ? "正常" : "已停用",
        }));
    if (section.value === "roles")
      return data.value.roles.map((r) => ({
        ...r,
        permissionsLabel: r.permissions.join("、"),
      }));
    if (section.value === "groups")
      return data.value.groups.map((g) => ({
        ...g,
        membersLabel: g.members.map(peopleName).join("、") || "暂无成员",
      }));
    if (section.value === "routes")
      return data.value.departments
        .filter((d) => d.id !== "ops")
        .map((d) => ({
          ...d,
          target: data.value!.settings.routes[d.id] || "未配置",
          mode: "自动发送 · 无需核对",
        }));
    if (section.value === "audit")
      return data.value.audit.map((e) => ({
        ...e,
        timeLabel: new Date(e.time).toLocaleTimeString("zh-CN"),
      }));
    return data.value.jobs
      .filter((j) => section.value !== "exceptions" || isException(j.state))
      .map((j) => ({
        ...j,
        departmentName: deptName(j.department),
        status: statusLabels[j.state],
      }));
  });
  const person = ref<Employee>(),
    role = ref<Role>(),
    group = ref<Group>(),
    job = ref<AdminData["jobs"][number]>(),
    members = ref<string[]>([]),
    routeDept = ref(""),
    target = ref(""),
    version = ref(0),
    reason = ref("");
  function open(kind: string, id = "") {
    mutationError.value = "";
    modal.value = kind;
    if (kind === "person")
      person.value = data.value?.people.find((p) => p.id === id);
    if (kind === "role")
      role.value = data.value?.roles.find((p) => p.id === id);
    if (kind === "group") {
      const g = data.value!.groups.find((g) => g.id === id)!;
      group.value = { ...g };
      members.value = [...g.members];
    }
    if (kind === "route") {
      routeDept.value = id;
      target.value = data.value!.settings.routes[id] || "";
      version.value = data.value!.settings.routeVersion;
    }
    if (kind === "recover") {
      job.value = data.value?.jobs.find((j) => j.id === id);
      reason.value = "";
    }
  }
  async function mutate(fn: () => Promise<unknown>, success = "变更已保存") {
    if (busy.value) return;
    busy.value = true;
    mutationError.value = "";
    try {
      await fn();
      modal.value = "";
      message.value = success;
      await refresh();
    } catch (e) {
      mutationError.value = (e as Error).message;
    } finally {
      busy.value = false;
    }
  }
  async function save() {
    if (modal.value === "person")
      await mutate(() => api.admin.toggle(person.value!.id));
    if (modal.value === "group")
      await mutate(() =>
        api.admin.group(group.value!.id, members.value, group.value!.version),
      );
    if (modal.value === "route")
      await mutate(() =>
        api.admin.route(routeDept.value, target.value, version.value),
      );
    if (modal.value === "pause")
      await mutate(() => api.admin.pause(!data.value!.settings.paused));
    if (modal.value === "recover") {
      if (!reason.value.trim()) {
        mutationError.value = "请填写处理依据";
        return;
      }
      await mutate(
        () => api.admin.recover(job.value!.id, reason.value),
        "处理依据已记录，系统继续推进任务",
      );
    }
  }
  const modalTitle = computed(
    () =>
      ({
        person: "变更账号状态",
        role: "角色权限",
        group: "维护业务组成员",
        route: "配置部门接收群",
        pause: "全局发送开关",
        recover: "管理员处理异常",
      })[modal.value] || "",
  );
  return {
    section,
    query,
    department,
    modal,
    busy,
    message,
    mutationError,
    data,
    error,
    loading,
    refresh,
    device,
    deptName,
    metrics,
    columns,
    rows,
    person,
    role,
    group,
    job,
    members,
    routeDept,
    target,
    reason,
    open,
    mutate,
    save,
    modalTitle,
  };
}
