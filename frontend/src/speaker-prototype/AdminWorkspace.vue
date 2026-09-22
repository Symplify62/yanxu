<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  Users,
  ShieldCheck,
  Network,
  Fingerprint,
  Plus,
  Search,
  ChevronRight,
  ArrowLeft,
  Pencil,
  Trash2,
  Check,
} from "@lucide/vue";
import {
  ElTable,
  ElTableColumn,
  ElInput,
  ElSelect,
  ElOption,
  ElCheckbox,
  ElTree,
} from "element-plus";
import Button from "../design-lab/kits/ElementButton.vue";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import UserEditor from "./UserEditor.vue";
import {
  permissionNames,
  voiceState,
  voiceLabels,
  type PrototypeModel,
  type Permission,
  type Person,
  type Role,
  type Department,
} from "./model";
const props = defineProps<{ model: PrototypeModel; section: Permission }>();
const emit = defineEmits<{
  navigate: [section: Permission];
  back: [];
  voice: [person: Person];
  enroll: [id: string];
}>();
const { members, departments, roles } = props.model;
const modules = [
  { id: "users" as Permission, name: "用户管理", icon: Users },
  { id: "roles" as Permission, name: "角色管理", icon: ShieldCheck },
  { id: "departments" as Permission, name: "部门管理", icon: Network },
  { id: "voices" as Permission, name: "声纹管理", icon: Fingerprint },
];
const query = ref(""),
  deptFilter = ref(""),
  status = ref("all"),
  notice = ref(""),
  error = ref("");
const editingUser = ref(false),
  user = ref<Person>();
const roleId = ref("host"),
  roleDraft = ref<Role>({ id: "", name: "", description: "", permissions: [] }),
  roleDialog = ref(false);
const deptId = ref("product"),
  deptDialog = ref(false),
  deptDraft = ref<Department>({ id: "", name: "", parentId: "company" });
const confirm = ref<{ title: string; body: string; action: () => void } | null>(
  null,
);
watch(
  () => props.section,
  () => {
    query.value = "";
    deptFilter.value = "";
    status.value = "all";
    notice.value = "";
    error.value = "";
  },
);
watch(
  [roleId, roles],
  () => {
    const r = roles.value.find((r) => r.id === roleId.value);
    if (r) roleDraft.value = JSON.parse(JSON.stringify(r));
  },
  { immediate: true, deep: true },
);
watch(roleDialog, (open) => {
  if (!open) {
    const r = roles.value.find((r) => r.id === roleId.value);
    if (r) roleDraft.value = JSON.parse(JSON.stringify(r));
  }
});
const filtered = computed(() =>
  members.value.filter(
    (p) =>
      `${p.name} ${p.detail}`.includes(query.value.trim()) &&
      (!deptFilter.value || p.departmentId === deptFilter.value) &&
      (status.value === "all" ||
        (props.section === "voices"
          ? voiceState(p) === status.value
          : status.value === "active"
            ? p.active
            : !p.active)),
  ),
);
const currentDept = computed(() =>
  departments.value.find((d) => d.id === deptId.value),
);
const deptPeople = computed(() =>
  members.value.filter((p) => p.departmentId === deptId.value),
);
function nodes(
  parent: string | null,
): Array<{ id: string; label: string; children: ReturnType<typeof nodes> }> {
  return departments.value
    .filter((d) => d.parentId === parent)
    .map((d) => ({ id: d.id, label: d.name, children: nodes(d.id) }));
}
const tree = computed(() => nodes(null));
function action(fn: () => void, message: string) {
  try {
    fn();
    error.value = "";
    notice.value = message;
  } catch (e) {
    error.value = (e as Error).message;
  }
}
function editUser(p?: Person) {
  user.value = p;
  editingUser.value = true;
}
function newRole() {
  roleDraft.value = {
    id: "",
    name: "",
    description: "",
    permissions: ["record"],
  };
  roleDialog.value = true;
  error.value = "";
}
function saveRole() {
  action(() => {
    props.model.saveRole(roleDraft.value);
    if (!roleDraft.value.id) roleId.value = roles.value.at(-1)!.id;
    roleDialog.value = false;
  }, "角色配置已保存");
}
function editDept(add = false) {
  deptDraft.value = add
    ? { id: "", name: "", parentId: deptId.value }
    : JSON.parse(JSON.stringify(currentDept.value));
  error.value = "";
  deptDialog.value = true;
}
function saveDept() {
  action(() => {
    const isNew = !deptDraft.value.id;
    props.model.saveDepartment(deptDraft.value);
    if (isNew) deptId.value = departments.value.at(-1)!.id;
    deptDialog.value = false;
  }, "部门已保存");
}
function confirmAction() {
  if (!confirm.value) return;
  const fn = confirm.value.action;
  confirm.value = null;
  action(fn, "操作已完成");
}
</script>
<template>
  <div class="admin-layout">
    <aside class="admin-rail">
      <div class="rail-label">
        <ShieldCheck :size="18" /><strong>管理后台</strong>
      </div>
      <nav aria-label="后台模块">
        <button
          v-for="item in modules.filter((x) => model.can(x.id))"
          :key="item.id"
          :class="{ active: section === item.id }"
          @click="emit('navigate', item.id)"
        >
          <component :is="item.icon" :size="18" />{{ item.name
          }}<ChevronRight v-if="section === item.id" :size="14" />
        </button>
      </nav>
      <button class="rail-back" @click="emit('back')">
        <ArrowLeft :size="16" />返回录音
      </button>
    </aside>
    <main class="admin-main">
      <template v-if="!model.can(section)"
        ><div class="empty-state">
          <ShieldCheck :size="34" />
          <h1>当前身份无此权限</h1>
          <p>请联系管理员，或切换演示身份。</p>
          <Button secondary @click="emit('back')">返回录音</Button>
        </div></template
      >
      <template v-else>
        <div class="admin-heading">
          <div>
            <div class="section-eyebrow">
              管理后台 / {{ permissionNames[section] }}
            </div>
            <h1>{{ permissionNames[section] }}</h1>
            <p>
              {{
                section === "users"
                  ? "维护组织成员与账号状态"
                  : section === "roles"
                    ? "为不同职责配置操作权限"
                    : section === "departments"
                      ? "维护部门层级与成员归属"
                      : "管理声音登记与识别状态"
              }}
            </p>
          </div>
          <Button v-if="section === 'users'" @click="editUser()"
            ><Plus :size="16" />添加用户</Button
          ><Button v-if="section === 'roles'" @click="newRole"
            ><Plus :size="16" />新建角色</Button
          ><Button v-if="section === 'departments'" @click="editDept(true)"
            ><Plus :size="16" />新增部门</Button
          >
        </div>
        <p v-if="notice" class="admin-notice" role="status">
          <Check :size="15" />{{ notice }}
        </p>
        <p
          v-if="error && !roleDialog && !deptDialog"
          class="form-error admin-error"
          role="alert"
        >
          {{ error }}
        </p>

        <section
          v-if="section === 'users' || section === 'voices'"
          class="admin-table-surface"
        >
          <div class="admin-toolbar">
            <div class="admin-search">
              <Search :size="16" /><ElInput
                v-model="query"
                aria-label="搜索用户"
                placeholder="搜索姓名或备注"
                clearable
              />
            </div>
            <ElSelect
              v-model="deptFilter"
              aria-label="筛选部门"
              placeholder="全部部门"
              clearable
              ><ElOption
                v-for="d in departments"
                :key="d.id"
                :label="d.name"
                :value="d.id" /></ElSelect
            ><ElSelect
              v-if="section === 'users'"
              v-model="status"
              aria-label="账号状态"
              ><ElOption label="全部状态" value="all" /><ElOption
                label="启用中"
                value="active" /><ElOption
                label="已停用"
                value="inactive" /></ElSelect
            ><span class="toolbar-count">{{ filtered.length }} 人</span>
          </div>
          <div v-if="section === 'voices'" class="voice-filter-tabs">
            <button :aria-pressed="status === 'all'" @click="status = 'all'">
              全部</button
            ><button
              v-for="(label, key) in voiceLabels"
              :key="key"
              :aria-pressed="status === key"
              @click="status = key"
            >
              {{ label }}
              <span>{{
                members.filter((p) => voiceState(p) === key).length
              }}</span>
            </button>
          </div>
          <ElTable
            :data="filtered"
            class="management-table"
            empty-text="没有匹配的成员"
            row-key="id"
          >
            <ElTableColumn label="用户" min-width="180"
              ><template #default="{ row }"
                ><div class="table-person">
                  <span class="person-avatar">{{ row.name.slice(-2) }}</span>
                  <div>
                    <strong>{{ row.name }}</strong
                    ><small>{{ row.detail }}</small>
                    <small class="mobile-user-status">{{
                      section === "voices"
                        ? voiceLabels[voiceState(row as Person)]
                        : row.active
                          ? "启用中"
                          : "已停用"
                    }}</small>
                  </div>
                </div></template
              ></ElTableColumn
            >
            <ElTableColumn label="部门" min-width="110"
              ><template #default="{ row }">{{
                model.departmentName(row.departmentId)
              }}</template></ElTableColumn
            >
            <ElTableColumn
              v-if="section === 'users'"
              label="角色"
              min-width="130"
              ><template #default="{ row }"
                ><span class="neutral-tag">{{
                  model.roleName(row.roleId)
                }}</span></template
              ></ElTableColumn
            >
            <ElTableColumn
              v-if="section === 'users'"
              label="账号"
              min-width="90"
              ><template #default="{ row }"
                ><span
                  class="status-tag"
                  :class="row.active ? 'ready' : 'revoked'"
                  >{{ row.active ? "启用中" : "已停用" }}</span
                ></template
              ></ElTableColumn
            >
            <ElTableColumn label="声纹" min-width="100"
              ><template #default="{ row }"
                ><span class="status-tag" :class="voiceState(row as Person)">{{
                  voiceLabels[voiceState(row as Person)]
                }}</span></template
              ></ElTableColumn
            >
            <ElTableColumn
              v-if="section === 'voices'"
              label="最近登记"
              min-width="130"
              ><template #default="{ row }">{{
                row.voice?.recordedAt || "—"
              }}</template></ElTableColumn
            >
            <ElTableColumn label="操作" width="160" fixed="right"
              ><template #default="{ row }"
                ><div class="table-actions">
                  <template v-if="section === 'users'"
                    ><button
                      :aria-label="`编辑${row.name}`"
                      @click="editUser(row as Person)"
                    >
                      编辑</button
                    ><button
                      :disabled="
                        row.id === 'lin' || row.id === model.actorId.value
                      "
                      :aria-label="`${row.active ? '停用' : '启用'}${row.name}`"
                      @click="
                        confirm = {
                          title: row.active ? '停用该用户？' : '启用该用户？',
                          body: row.active
                            ? '停用后不能选入新会议，历史记录保留。'
                            : '启用后可重新加入会议。',
                          action: () => model.setActive(row as Person),
                        }
                      "
                    >
                      {{ row.active ? "停用" : "启用" }}
                    </button></template
                  ><template v-else
                    ><button
                      :aria-label="`查看${row.name}的声纹`"
                      @click="emit('voice', row as Person)"
                    >
                      详情</button
                    ><button
                      :disabled="
                        !row.active ||
                        voiceState(row as Person) === 'generating'
                      "
                      :aria-label="`为${row.name}登记声纹`"
                      @click="emit('enroll', row.id)"
                    >
                      {{
                        voiceState(row as Person) === "ready" ? "更新" : "录入"
                      }}
                    </button></template
                  >
                </div></template
              ></ElTableColumn
            >
          </ElTable>
          <div class="table-footer">
            共 {{ filtered.length }} 位成员<span>{{
              section === "voices"
                ? "登记状态与本人确认分开管理"
                : "账号停用不会删除历史会议"
            }}</span>
          </div>
        </section>

        <section v-if="section === 'roles'" class="role-layout">
          <div class="role-list" aria-label="角色列表">
            <button
              v-for="r in roles"
              :key="r.id"
              :class="{ active: r.id === roleId }"
              @click="roleId = r.id"
            >
              <ShieldCheck :size="19" />
              <div>
                <strong>{{ r.name }}</strong
                ><small
                  >{{
                    members.filter((p) => p.roleId === r.id).length
                  }}
                  位用户</small
                >
              </div>
              <ChevronRight :size="15" />
            </button>
          </div>
          <div class="role-editor">
            <div class="role-title">
              <div>
                <h2>{{ roleDraft.name }}</h2>
                <p>{{ roleDraft.description }}</p>
              </div>
              <span class="neutral-tag">{{
                roleId === "admin" ? "系统内置" : "自定义权限"
              }}</span>
              <button
                v-if="roleId !== 'admin'"
                class="text-action"
                @click="roleDialog = true"
              >
                编辑角色
              </button>
            </div>
            <h3>操作权限</h3>
            <div class="permissions-grid">
              <ElCheckbox
                v-for="(label, key) in permissionNames"
                :key="key"
                :model-value="roleDraft.permissions.includes(key)"
                :disabled="roleId === 'admin'"
                @change="
                  (v) =>
                    (roleDraft.permissions = v
                      ? [...roleDraft.permissions, key]
                      : roleDraft.permissions.filter((p) => p !== key))
                "
                >{{ label }}</ElCheckbox
              >
            </div>
            <p class="quiet-note">
              原型演示操作权限。正式数据范围由后端独立校验。
            </p>
            <div class="role-actions">
              <button
                v-if="!['admin', 'host', 'member'].includes(roleId)"
                class="danger-text"
                @click="
                  confirm = {
                    title: '删除角色？',
                    body: '已分配给用户的角色不能直接删除。',
                    action: () => {
                      model.deleteRole(roleId);
                      roleId = 'host';
                    },
                  }
                "
              >
                <Trash2 :size="15" />删除角色</button
              ><Button :disabled="roleId === 'admin'" @click="saveRole"
                >保存权限</Button
              >
            </div>
          </div>
        </section>

        <section v-if="section === 'departments'" class="department-layout">
          <div class="department-tree">
            <div class="subsection-title">组织架构</div>
            <ElTree
              :data="tree"
              node-key="id"
              :current-node-key="deptId"
              default-expand-all
              highlight-current
              :expand-on-click-node="false"
              @node-click="(d: { id: string }) => (deptId = d.id)"
            />
          </div>
          <div class="department-detail">
            <div class="department-heading">
              <div>
                <h2>{{ currentDept?.name }}</h2>
                <p>
                  {{ deptPeople.length }} 位直属成员 ·
                  {{ departments.filter((d) => d.parentId === deptId).length }}
                  个子部门
                </p>
              </div>
              <div class="table-actions">
                <button
                  :disabled="deptId === 'company'"
                  @click="editDept(false)"
                >
                  <Pencil :size="14" />编辑</button
                ><button
                  :disabled="deptId === 'company'"
                  @click="
                    confirm = {
                      title: '删除部门？',
                      body: '部门中仍有成员或子部门时不能删除。',
                      action: () => {
                        model.deleteDepartment(deptId);
                        deptId = 'company';
                      },
                    }
                  "
                >
                  <Trash2 :size="14" />删除
                </button>
              </div>
            </div>
            <ElTable :data="deptPeople" empty-text="该部门暂无直属成员"
              ><ElTableColumn
                label="姓名"
                prop="name"
                min-width="130"
              /><ElTableColumn
                label="职位 / 备注"
                prop="detail"
                min-width="150"
              /><ElTableColumn label="角色" min-width="120"
                ><template #default="{ row }">{{
                  model.roleName(row.roleId)
                }}</template></ElTableColumn
              ></ElTable
            >
          </div>
        </section>
      </template>
    </main>
    <UserEditor
      :model="model"
      :open="editingUser"
      :person="user"
      @close="editingUser = false"
      @saved="notice = '用户已保存，录音选人列表已同步'"
    />
    <Dialog
      :model-value="roleDialog"
      :title="roleDraft.id ? '编辑角色' : '新建角色'"
      @update:model-value="roleDialog = false"
      ><div class="editor-form">
        <label
          >角色名称<ElInput
            v-model="roleDraft.name"
            aria-label="角色名称"
            maxlength="30" /></label
        ><label
          >职责说明<ElInput
            v-model="roleDraft.description"
            aria-label="职责说明"
            maxlength="100"
        /></label>
        <p class="quiet-note">创建后在右侧配置操作权限。</p>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      </div>
      <template #footer
        ><Button secondary @click="roleDialog = false">取消</Button
        ><Button @click="saveRole">{{
          roleDraft.id ? "保存角色" : "创建角色"
        }}</Button></template
      ></Dialog
    >
    <Dialog
      :model-value="deptDialog"
      :title="deptDraft.id ? '编辑部门' : '新增部门'"
      @update:model-value="deptDialog = false"
      ><div class="editor-form">
        <label
          >部门名称<ElInput
            v-model="deptDraft.name"
            aria-label="部门名称"
            maxlength="30" /></label
        ><label
          >上级部门<ElSelect v-model="deptDraft.parentId" aria-label="上级部门"
            ><ElOption
              v-for="d in departments"
              :key="d.id"
              :value="d.id"
              :label="d.name" /></ElSelect
        ></label>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      </div>
      <template #footer
        ><Button secondary @click="deptDialog = false">取消</Button
        ><Button @click="saveDept">保存部门</Button></template
      ></Dialog
    >
    <Dialog
      :model-value="!!confirm"
      :title="confirm?.title"
      @update:model-value="confirm = null"
      ><p>{{ confirm?.body }}</p>
      <template #footer
        ><Button secondary @click="confirm = null">取消</Button
        ><Button @click="confirmAction">确认操作</Button></template
      ></Dialog
    >
  </div>
</template>
