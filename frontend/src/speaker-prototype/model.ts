import { computed, onUnmounted, ref, watch } from "vue";

export type Permission =
  "record" | "users" | "roles" | "departments" | "voices";
export const permissionNames: Record<Permission, string> = {
  record: "发起会议",
  users: "用户管理",
  roles: "角色管理",
  departments: "部门管理",
  voices: "声纹管理",
};
export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
}
export interface Department {
  id: string;
  name: string;
  parentId: string | null;
}
export interface Voice {
  recordedAt: string;
  seconds: number;
  consent: boolean;
  kind: "demo";
  status: "generating" | "ready" | "review" | "revoked";
}
export interface Person {
  id: string;
  name: string;
  detail: string;
  scope: "member" | "guest";
  voice: Voice | null;
  departmentId: string;
  roleId: string;
  active: boolean;
}
export interface Meeting {
  id: string;
  title: string;
  people: Person[];
  seconds: number;
  date: string;
}
export const voiceLabels = {
  none: "未录入",
  generating: "生成中",
  ready: "可用",
  review: "需重录",
  revoked: "已撤回",
};
export const voiceState = (p: Person) => p.voice?.status || "none";
export const voiceReady = (p: Person) =>
  p.voice?.status === "ready" && (p.scope === "guest" || p.voice.consent);
const KEY = "yanxu-speaker-prototype-v2";
const DRAFT = "yanxu-speaker-prototype-draft-v2";
const clone = <T>(v: T): T => JSON.parse(JSON.stringify(v));
const demoVoice = (status: Voice["status"] = "ready"): Voice => ({
  recordedAt: "2026-09-22",
  seconds: 8,
  consent: true,
  kind: "demo",
  status,
});
function seed() {
  const roles: Role[] = [
    {
      id: "admin",
      name: "管理员",
      description: "维护组织与人员配置",
      permissions: ["record", "users", "roles", "departments", "voices"],
    },
    {
      id: "host",
      name: "会议组织者",
      description: "发起会议与维护本场参会者",
      permissions: ["record"],
    },
    {
      id: "member",
      name: "普通成员",
      description: "查看会议、维护本人声音",
      permissions: [],
    },
  ];
  const departments: Department[] = [
    { id: "company", name: "嘉谏", parentId: null },
    { id: "product", name: "产品部", parentId: "company" },
    { id: "tech", name: "研发部", parentId: "company" },
    { id: "design", name: "设计部", parentId: "product" },
    { id: "operations", name: "运营部", parentId: "company" },
    { id: "supply", name: "供应链", parentId: "company" },
  ];
  const members: Person[] = [
    {
      id: "lin",
      name: "林晓",
      detail: "项目负责人",
      scope: "member",
      departmentId: "product",
      roleId: "admin",
      active: true,
      voice: demoVoice(),
    },
    {
      id: "chen",
      name: "陈默",
      detail: "技术负责人",
      scope: "member",
      departmentId: "tech",
      roleId: "host",
      active: true,
      voice: demoVoice(),
    },
    {
      id: "zhou",
      name: "周宁",
      detail: "体验设计",
      scope: "member",
      departmentId: "design",
      roleId: "member",
      active: true,
      voice: null,
    },
    {
      id: "xu",
      name: "许言",
      detail: "内容运营",
      scope: "member",
      departmentId: "operations",
      roleId: "member",
      active: true,
      voice: null,
    },
    {
      id: "wang",
      name: "王璐",
      detail: "供应商管理",
      scope: "member",
      departmentId: "supply",
      roleId: "host",
      active: true,
      voice: demoVoice(),
    },
    {
      id: "zhang",
      name: "张伟",
      detail: "排产协调",
      scope: "member",
      departmentId: "supply",
      roleId: "member",
      active: true,
      voice: demoVoice("review"),
    },
  ];
  return {
    version: 2,
    roles,
    departments,
    members,
    history: [] as Meeting[],
    preferences: {
      microphone: "内置麦克风",
      quality: "标准",
      rememberPeople: false,
    },
  };
}
export function useSpeakerPrototype() {
  const storageError = ref("");
  let initial = seed();
  try {
    const value = JSON.parse(localStorage.getItem(KEY) || "null");
    if (
      value?.version === 2 &&
      ["members", "roles", "departments", "history"].every((k) =>
        Array.isArray(value[k]),
      ) &&
      value.members.every(
        (p: Person) => typeof p.id === "string" && typeof p.name === "string",
      )
    )
      initial = value;
  } catch {
    storageError.value = "演示数据未恢复，已载入示例。";
  }
  const state = ref(initial);
  const actorId = ref("lin");
  try {
    const savedActor = sessionStorage.getItem(
      "yanxu-speaker-prototype-actor-v2",
    );
    if (state.value.members.some((p) => p.id === savedActor && p.active))
      actorId.value = savedActor!;
  } catch {
    /* Demo identity remains the initial administrator. */
  }
  watch(actorId, (id) => {
    try {
      sessionStorage.setItem("yanxu-speaker-prototype-actor-v2", id);
    } catch {
      storageError.value = "演示身份未保存，刷新后将恢复管理员。";
    }
  });
  const actor = computed(() =>
    state.value.members.find((p) => p.id === actorId.value),
  );
  const can = (permission: Permission) =>
    !!actor.value?.active &&
    !!state.value.roles
      .find((r) => r.id === actor.value?.roleId)
      ?.permissions.includes(permission);
  const members = computed(() => state.value.members);
  const departments = computed(() => state.value.departments);
  const roles = computed(() => state.value.roles);
  const guests = ref<Person[]>([]);
  const selectedIds = ref<string[]>(["lin", "chen"]);
  const title = ref("项目例会");
  try {
    const d = JSON.parse(sessionStorage.getItem(DRAFT) || "null");
    if (d && Array.isArray(d.ids) && Array.isArray(d.guests)) {
      selectedIds.value = d.ids.filter((id: unknown) => typeof id === "string");
      guests.value = d.guests.filter(
        (p: Person) =>
          p.scope === "guest" &&
          typeof p.id === "string" &&
          typeof p.name === "string",
      );
      title.value = typeof d.title === "string" ? d.title : "项目例会";
    }
  } catch {
    storageError.value = "本场名单未恢复。";
  }
  const people = computed(() => [...members.value, ...guests.value]);
  const available = computed(() => people.value.filter((p) => p.active));
  const selected = computed(() =>
    available.value.filter((p) => selectedIds.value.includes(p.id)),
  );
  const pending = computed(() => selected.value.filter((p) => !voiceReady(p)));
  const phase = ref<"setup" | "recording" | "paused" | "processing" | "result">(
    "setup",
  );
  const seconds = ref(0);
  const result = ref<Meeting | null>(null);
  const activeMeeting = ref<Meeting | null>(null);
  const timers = new Set<ReturnType<typeof setTimeout>>();
  function later(callback: () => void, ms = 1000) {
    const id = setTimeout(() => {
      timers.delete(id);
      callback();
    }, ms);
    timers.add(id);
  }
  const tick = setInterval(() => {
    if (phase.value === "recording") seconds.value++;
  }, 1000);
  onUnmounted(() => {
    clearInterval(tick);
    timers.forEach(clearTimeout);
  });
  // Resume unfinished simulated generation if the review page was refreshed.
  for (const p of people.value)
    if (p.voice?.status === "generating")
      later(() => {
        if (p.voice?.status === "generating") p.voice.status = "ready";
      });
  watch(
    state,
    (v) => {
      try {
        localStorage.setItem(KEY, JSON.stringify(v));
      } catch {
        storageError.value = "无法保存演示档案，刷新可能丢失。";
      }
    },
    { deep: true },
  );
  watch(
    [guests, selectedIds, title],
    () => {
      try {
        sessionStorage.setItem(
          DRAFT,
          JSON.stringify({
            guests: guests.value,
            ids: selectedIds.value,
            title: title.value,
          }),
        );
      } catch {
        storageError.value = "本场草稿未保存。";
      }
    },
    { deep: true },
  );
  const departmentName = (id: string) =>
    departments.value.find((d) => d.id === id)?.name || "外部来宾";
  const roleName = (id: string) =>
    roles.value.find((r) => r.id === id)?.name || "无角色";
  function toggle(id: string) {
    if (!can("record")) return;
    const person = available.value.find((p) => p.id === id);
    if (!person) return;
    if (selectedIds.value.includes(id)) {
      if (phase.value !== "setup") return;
      selectedIds.value = selectedIds.value.filter((x) => x !== id);
    } else {
      selectedIds.value.push(id);
      if (activeMeeting.value && ["recording", "paused"].includes(phase.value))
        activeMeeting.value.people.push(clone(person));
    }
  }
  function setPeopleSelected(ids: string[], checked: boolean) {
    if (
      !can("record") ||
      !["setup", "recording", "paused"].includes(phase.value)
    )
      return;
    if (!checked && phase.value !== "setup") return;
    const activeIds = new Set(available.value.map((p) => p.id));
    const targets = new Set(ids.filter((id) => activeIds.has(id)));
    if (checked) {
      for (const id of targets) if (!selectedIds.value.includes(id)) toggle(id);
    } else {
      selectedIds.value = selectedIds.value.filter((id) => !targets.has(id));
    }
  }
  function savePerson(
    input: Partial<Person> & { name: string; detail: string },
    invite = false,
  ): string {
    const existing = members.value.find((p) => p.id === input.id);
    const scope = input.scope || "member";
    if (scope === "member" && !can("users"))
      throw new Error("当前身份不能管理用户。");
    if (scope === "guest" && !can("record"))
      throw new Error("当前身份不能添加来宾。");
    if (!input.name.trim() || input.name.trim().length > 20)
      throw new Error("请填写 1–20 字姓名。");
    if (
      people.value.some(
        (p) =>
          p.id !== input.id &&
          p.name === input.name.trim() &&
          p.departmentId === (input.departmentId || "") &&
          p.detail === input.detail.trim(),
      )
    )
      throw new Error("已有同名同部门人员，请补充备注区分。");
    if (
      scope === "member" &&
      (!departments.value.some((d) => d.id === input.departmentId) ||
        !roles.value.some((r) => r.id === input.roleId))
    )
      throw new Error("请选择有效部门和角色。");
    if (existing?.id === actorId.value && input.active === false)
      throw new Error("不能停用当前演示账号。");
    if (existing?.id === "lin" && input.roleId !== "admin")
      throw new Error("示例管理员需保留管理员角色。");
    const p: Person = {
      id: existing?.id || crypto.randomUUID(),
      name: input.name.trim(),
      detail: input.detail.trim(),
      scope,
      departmentId: input.departmentId || "",
      roleId: input.roleId || "member",
      active: input.active ?? true,
      voice: existing?.voice || null,
    };
    if (existing) Object.assign(existing, p);
    else (scope === "member" ? state.value.members : guests.value).push(p);
    if (invite) toggle(p.id);
    return p.id;
  }
  function setActive(p: Person) {
    if (!can("users")) throw new Error("没有用户管理权限。");
    if (p.id === actorId.value || p.id === "lin")
      throw new Error("不能停用当前账号或示例管理员。");
    p.active = !p.active;
    if (!p.active)
      selectedIds.value = selectedIds.value.filter((id) => id !== p.id);
  }
  function voiceEnrollmentBlock(p: Person) {
    if (!p.active || !actor.value?.active) return "用户已停用，不能录制声纹";
    if (["recording", "paused", "processing"].includes(phase.value))
      return "结束本场会议后可录制声纹";
    if (p.voice?.status === "generating") return "声纹正在生成，请稍候";
    // Enrollment is independent of the meeting roster; it does not select this person.
    if (can("voices") || can("record") || actorId.value === p.id) return "";
    return "仅本人、会议组织者或声纹管理员可录制";
  }
  function saveVoice(
    id: string,
    name: string,
    length: number,
    consent: boolean,
  ) {
    const p = people.value.find((x) => x.id === id);
    if (!p) throw new Error("人员不存在。");
    const blocked = voiceEnrollmentBlock(p);
    if (blocked) throw new Error(blocked);
    if (!name.trim() || name.trim().length > 20)
      throw new Error("姓名需为 1–20 字。");
    if (p.scope === "member" && !consent)
      throw new Error("请先确认长期保存声音。");
    p.name = name.trim();
    const voice: Voice = {
      recordedAt: new Date().toLocaleDateString("sv-SE"),
      seconds: length,
      consent,
      kind: "demo",
      status: "generating",
    };
    p.voice = voice;
    later(() => {
      const current = people.value.find((x) => x.id === id);
      if (current?.voice?.status === "generating")
        current.voice.status = "ready";
    }, 1200);
    return true;
  }
  function changeVoice(id: string, status: "revoked" | "review") {
    const p = people.value.find((x) => x.id === id);
    if (!p || !(can("voices") || actorId.value === id))
      throw new Error("没有声纹管理权限。");
    if (!p.voice) return;
    p.voice.status = status;
    if (status === "revoked") p.voice.consent = false;
  }
  function saveRole(input: Role) {
    if (!can("roles")) throw new Error("没有角色管理权限。");
    if (
      !input.name.trim() ||
      roles.value.some((r) => r.id !== input.id && r.name === input.name.trim())
    )
      throw new Error("角色名称不能为空或重复。");
    if (input.id === "admin") throw new Error("示例管理员角色为系统内置。");
    const r = {
      ...input,
      id: input.id || crypto.randomUUID(),
      name: input.name.trim(),
    };
    const old = roles.value.find((x) => x.id === r.id);
    if (old) Object.assign(old, r);
    else state.value.roles.push(r);
  }
  function deleteRole(id: string) {
    if (!can("roles")) throw new Error("没有角色管理权限。");
    if (["admin", "host", "member"].includes(id))
      throw new Error("内置角色不能删除。");
    if (members.value.some((p) => p.roleId === id))
      throw new Error("该角色已分配给用户，请先调整用户角色。");
    state.value.roles = roles.value.filter((r) => r.id !== id);
  }
  function saveDepartment(input: Department) {
    if (!can("departments")) throw new Error("没有部门管理权限。");
    if (!input.name.trim()) throw new Error("请填写部门名称。");
    if (input.id === "company") throw new Error("示例根部门不可修改。");
    if (
      !input.parentId ||
      !departments.value.some((d) => d.id === input.parentId)
    )
      throw new Error("请选择有效的上级部门。");
    let cursor: string | null = input.parentId;
    while (cursor) {
      if (cursor === input.id)
        throw new Error("不能将部门移动到自己或子部门下。");
      cursor = departments.value.find((d) => d.id === cursor)?.parentId || null;
    }
    if (
      departments.value.some(
        (d) =>
          d.id !== input.id &&
          d.name === input.name.trim() &&
          d.parentId === input.parentId,
      )
    )
      throw new Error("同一上级部门下名称不能重复。");
    const d = {
      ...input,
      id: input.id || crypto.randomUUID(),
      name: input.name.trim(),
    };
    const old = departments.value.find((x) => x.id === d.id);
    if (old) Object.assign(old, d);
    else state.value.departments.push(d);
  }
  function deleteDepartment(id: string) {
    if (!can("departments")) throw new Error("没有部门管理权限。");
    if (
      id === "company" ||
      departments.value.some((d) => d.parentId === id) ||
      members.value.some((p) => p.departmentId === id)
    )
      throw new Error("请先移走成员和子部门，再删除此部门。");
    state.value.departments = departments.value.filter((d) => d.id !== id);
  }
  function start() {
    if (!can("record") || !selected.value.length) return;
    activeMeeting.value = clone({
      id: crypto.randomUUID(),
      title: title.value.trim() || "未命名会议",
      people: selected.value,
      seconds: 0,
      date: new Date().toLocaleString("zh-CN"),
    });
    seconds.value = 0;
    phase.value = "recording";
  }
  function finish() {
    if (!activeMeeting.value || !["recording", "paused"].includes(phase.value))
      return;
    phase.value = "processing";
    result.value = clone({ ...activeMeeting.value, seconds: seconds.value });
    later(() => {
      if (!result.value) return;
      state.value.history.unshift(clone(result.value));
      phase.value = "result";
    }, 1200);
  }
  function nextMeeting() {
    guests.value = [];
    selectedIds.value = state.value.preferences.rememberPeople
      ? selectedIds.value.filter((id) =>
          members.value.some((p) => p.id === id && p.active),
        )
      : [];
    activeMeeting.value = null;
    result.value = null;
    seconds.value = 0;
    phase.value = "setup";
    title.value = "项目例会";
  }
  function reset() {
    timers.forEach(clearTimeout);
    timers.clear();
    state.value = seed();
    actorId.value = "lin";
    nextMeeting();
    selectedIds.value = ["lin", "chen"];
  }
  return {
    state,
    members,
    departments,
    roles,
    actorId,
    actor,
    can,
    guests,
    people,
    available,
    selectedIds,
    selected,
    pending,
    title,
    phase,
    seconds,
    activeMeeting,
    result,
    storageError,
    departmentName,
    roleName,
    toggle,
    setPeopleSelected,
    savePerson,
    setActive,
    saveVoice,
    voiceEnrollmentBlock,
    changeVoice,
    saveRole,
    deleteRole,
    saveDepartment,
    deleteDepartment,
    start,
    finish,
    nextMeeting,
    reset,
  };
}
export type PrototypeModel = ReturnType<typeof useSpeakerPrototype>;
export function clock(s: number) {
  return `${Math.floor(s / 60)
    .toString()
    .padStart(2, "0")}:${(s % 60).toString().padStart(2, "0")}`;
}
