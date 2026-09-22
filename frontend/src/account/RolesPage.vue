<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { errorMessage, request } from "./api";
import { permissionLabels, type Permission, type Role } from "./types";
const roles = ref<Role[]>([]),
  loading = ref(false),
  saving = ref(false),
  open = ref(false),
  error = ref(""),
  formError = ref("");
const editing = ref<Role | null>(null),
  form = reactive({
    name: "",
    description: "",
    permissions: [] as Permission[],
  });
async function load() {
  loading.value = true;
  error.value = "";
  try {
    roles.value = (await request<{ items: Role[] }>("/api/admin/roles")).items;
  } catch (e) {
    roles.value = [];
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function edit(role: Role | null) {
  editing.value = role;
  Object.assign(form, {
    name: role?.name || "",
    description: role?.description || "",
    permissions: [...(role?.permissions || [])],
  });
  formError.value = "";
  open.value = true;
}
async function save() {
  if (saving.value) return;
  if (!form.name.trim()) {
    formError.value = "请填写角色名称";
    return;
  }
  saving.value = true;
  formError.value = "";
  try {
    const payload = editing.value?.builtin
      ? { description: form.description }
      : { ...form };
    await request(
      `/api/admin/roles${editing.value ? `/${editing.value.id}` : ""}`,
      {
        method: editing.value ? "PATCH" : "POST",
        body: JSON.stringify(payload),
      },
    );
    open.value = false;
    await load();
  } catch (e) {
    formError.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
async function remove(role: Role) {
  try {
    await ElMessageBox.confirm(`删除角色“${role.name}”？`, "删除角色", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await request(`/api/admin/roles/${role.id}`, { method: "DELETE" });
    await load();
  } catch (e) {
    error.value = errorMessage(e);
  }
}
async function close(done: () => void) {
  if (saving.value) return;
  try {
    await ElMessageBox.confirm("放弃本次编辑？", "关闭编辑", {
      confirmButtonText: "放弃",
      cancelButtonText: "继续编辑",
    });
    done();
  } catch {
    /* Keep draft. */
  }
}
onMounted(load);
</script>
<template>
  <section aria-label="角色管理">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div class="workspace-toolbar">
      <span class="status-text">{{ roles.length }} 个角色</span
      ><span class="toolbar-spacer" /><el-button
        :loading="loading"
        @click="load"
        >刷新</el-button
      ><el-button type="primary" @click="edit(null)">新增角色</el-button>
    </div>
    <div class="workspace-surface">
      <el-table v-loading="loading" :data="roles" empty-text="暂无角色"
        ><el-table-column label="角色" min-width="180"
          ><template #default="{ row }"
            ><strong>{{ row.name }}</strong
            ><small v-if="row.builtin" class="status-text">
              · 内置</small
            ></template
          ></el-table-column
        ><el-table-column label="权限" min-width="280"
          ><template #default="{ row }">{{
            row.permissions
              .map((p: Permission) => permissionLabels[p])
              .join("、") || "本人声音档案"
          }}</template></el-table-column
        ><el-table-column
          prop="description"
          label="说明"
          min-width="180"
        /><el-table-column label="操作" width="150" fixed="right"
          ><template #default="{ row }"
            ><el-button text type="primary" @click="edit(row as Role)"
              >编辑</el-button
            ><el-button
              text
              :disabled="row.builtin"
              @click="remove(row as Role)"
              >删除</el-button
            ></template
          ></el-table-column
        ></el-table
      >
    </div>
    <el-dialog
      v-model="open"
      :title="editing ? '编辑角色' : '新增角色'"
      class="account-dialog"
      width="480px"
      :close-on-click-modal="false"
      :before-close="close"
      destroy-on-close
    >
      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
      /><el-form label-position="top"
        ><el-form-item label="角色名称" required
          ><el-input
            v-model="form.name"
            aria-label="角色名称"
            :disabled="editing?.builtin"
            maxlength="80" /></el-form-item
        ><el-form-item label="说明"
          ><el-input
            v-model="form.description"
            aria-label="角色说明"
            maxlength="200" /></el-form-item
        ><el-form-item label="操作权限"
          ><el-checkbox-group
            v-model="form.permissions"
            class="permission-list"
            :disabled="editing?.builtin"
            ><el-checkbox
              v-for="(label, permission) in permissionLabels"
              :key="permission"
              :value="permission"
              >{{ label }}</el-checkbox
            ></el-checkbox-group
          ></el-form-item
        ></el-form
      >
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
