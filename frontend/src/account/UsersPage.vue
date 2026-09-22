<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { errorMessage, hasPermission, request } from "./api";
import type { Department, Person, Role } from "./types";
const people = ref<Person[]>([]),
  departments = ref<Department[]>([]),
  roles = ref<Role[]>([]);
const query = ref(""),
  error = ref(""),
  formError = ref(""),
  loading = ref(false),
  saving = ref(false),
  open = ref(false);
const editing = ref<Person | null>(null),
  allowLogin = ref(false);
const form = reactive({
  name: "",
  detail: "",
  departmentId: "",
  active: true,
  username: "",
  password: "",
  roleId: "member",
});
const filtered = computed(() =>
  people.value.filter((p) =>
    `${p.name} ${p.detail} ${p.username || ""} ${p.departmentName || ""}`
      .toLowerCase()
      .includes(query.value.toLowerCase()),
  ),
);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const users = await request<{ items: Person[] }>("/api/admin/users");
    people.value = users.items;
    const directory = await request<{ departments: Department[] }>(
      "/api/people",
    );
    departments.value = directory.departments;
    if (hasPermission("roles"))
      roles.value = (
        await request<{ items: Role[] }>("/api/admin/roles")
      ).items;
  } catch (e) {
    people.value = [];
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function edit(person: Person | null) {
  editing.value = person;
  allowLogin.value = Boolean(person?.username);
  formError.value = "";
  Object.assign(form, {
    name: person?.name || "",
    detail: person?.detail || "",
    departmentId: person?.departmentId || "",
    active: person?.active ?? true,
    username: person?.username || "",
    password: "",
    roleId: person?.roleId || "member",
  });
  open.value = true;
}
async function save() {
  if (saving.value) return;
  if (!form.name.trim()) {
    formError.value = "请填写姓名";
    return;
  }
  if (
    allowLogin.value &&
    (!form.username.trim() ||
      (!editing.value?.accountId && form.password.length < 12))
  ) {
    formError.value = "请填写账号和至少12位密码";
    return;
  }
  saving.value = true;
  formError.value = "";
  const data: Record<string, unknown> = {
    name: form.name.trim(),
    detail: form.detail,
    departmentId: form.departmentId || null,
    active: form.active,
  };
  if (allowLogin.value) {
    data.username = form.username.trim();
    data.roleId = form.roleId;
    if (form.password) data.password = form.password;
  }
  try {
    await request(
      `/api/admin/users${editing.value ? `/${editing.value.id}` : ""}`,
      { method: editing.value ? "PATCH" : "POST", body: JSON.stringify(data) },
    );
    form.password = "";
    open.value = false;
    await load();
  } catch (e) {
    formError.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
async function remove(person: Person) {
  try {
    await ElMessageBox.confirm(
      `归档“${person.name}”？该人员将无法登录或加入新的会议。`,
      "归档用户",
      { confirmButtonText: "归档", cancelButtonText: "取消", type: "warning" },
    );
  } catch {
    return;
  }
  try {
    await request(`/api/admin/users/${person.id}`, { method: "DELETE" });
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function close(done: () => void) {
  if (saving.value) return;
  if (form.name || form.username || form.password) {
    try {
      await ElMessageBox.confirm("放弃本次编辑？", "关闭编辑", {
        confirmButtonText: "放弃",
        cancelButtonText: "继续编辑",
      });
    } catch {
      return;
    }
  }
  form.password = "";
  done();
}
onMounted(load);
</script>
<template>
  <section aria-label="用户管理">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div class="workspace-toolbar">
      <el-input
        v-model="query"
        placeholder="搜索姓名、部门或账号"
        aria-label="搜索用户"
        clearable
      /><span class="toolbar-spacer" /><el-button
        :loading="loading"
        @click="load"
        >刷新</el-button
      ><el-button type="primary" @click="edit(null)">新增用户</el-button>
    </div>
    <div class="workspace-surface">
      <el-table v-loading="loading" :data="filtered" empty-text="暂无用户">
        <el-table-column label="人员" min-width="190"
          ><template #default="{ row }"
            ><div class="person-cell">
              <span class="account-avatar">{{ row.name.slice(0, 1) }}</span>
              <div>
                <strong>{{ row.name }}</strong
                ><small>{{ row.detail || "—" }}</small>
              </div>
            </div></template
          ></el-table-column
        >
        <el-table-column prop="departmentName" label="部门" min-width="130"
          ><template #default="{ row }">{{
            row.departmentName || "未分配"
          }}</template></el-table-column
        >
        <el-table-column label="登录账号" min-width="150"
          ><template #default="{ row }">{{
            row.username || "无需登录"
          }}</template></el-table-column
        >
        <el-table-column label="状态" width="90"
          ><template #default="{ row }"
            ><span
              class="status-text"
              :class="row.active ? 'ready' : 'revoked'"
              >{{ row.active ? "启用" : "停用" }}</span
            ></template
          ></el-table-column
        >
        <el-table-column label="操作" width="155" fixed="right"
          ><template #default="{ row }"
            ><el-button text type="primary" @click="edit(row as Person)"
              >编辑</el-button
            ><el-button text @click="remove(row as Person)"
              >归档</el-button
            ></template
          ></el-table-column
        >
      </el-table>
    </div>
    <el-dialog
      v-model="open"
      :title="editing ? '编辑用户' : '新增用户'"
      width="480px"
      class="account-dialog"
      :close-on-click-modal="false"
      :before-close="close"
      destroy-on-close
    >
      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
      />
      <el-form label-position="top" @submit.prevent="save">
        <el-form-item label="姓名" required
          ><el-input v-model="form.name" aria-label="姓名" maxlength="80"
        /></el-form-item>
        <el-form-item label="部门"
          ><el-select
            v-model="form.departmentId"
            aria-label="部门"
            clearable
            placeholder="未分配"
            ><el-option
              v-for="d in departments"
              :key="d.id"
              :value="d.id"
              :label="d.name" /></el-select
        ></el-form-item>
        <el-form-item label="备注"
          ><el-input v-model="form.detail" aria-label="备注" maxlength="200"
        /></el-form-item>
        <el-form-item
          ><el-switch v-model="form.active" active-text="启用用户"
        /></el-form-item>
        <el-checkbox
          v-model="allowLogin"
          :disabled="Boolean(editing?.accountId) || !hasPermission('roles')"
          >允许账号登录</el-checkbox
        >
        <template v-if="allowLogin"
          ><el-form-item label="账号" required
            ><el-input
              v-model="form.username"
              aria-label="登录账号"
              autocomplete="off" /></el-form-item
          ><el-form-item
            :label="
              editing?.accountId ? '重置密码（留空保留）' : '密码（至少12位）'
            "
            ><el-input
              v-model="form.password"
              aria-label="用户密码"
              type="password"
              show-password
              autocomplete="new-password" /></el-form-item
          ><el-form-item label="角色"
            ><el-select
              v-model="form.roleId"
              aria-label="用户角色"
              :disabled="!hasPermission('roles')"
              ><el-option
                v-for="r in roles"
                :key="r.id"
                :label="r.name"
                :value="r.id" /></el-select></el-form-item
        ></template>
      </el-form>
      <template #footer
        ><el-button :disabled="saving" @click="close(() => (open = false))"
          >取消</el-button
        ><el-button type="primary" :loading="saving" @click="save"
          >保存</el-button
        ></template
      >
    </el-dialog>
  </section>
</template>
