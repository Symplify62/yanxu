<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessageBox } from "element-plus";
import { errorMessage, request } from "./api";
import type { Department } from "./types";
const items = ref<Department[]>([]),
  selected = ref<Department | null>(null),
  loading = ref(false),
  saving = ref(false),
  open = ref(false),
  error = ref(""),
  formError = ref("");
const editing = ref<Department | null>(null),
  form = reactive({ name: "", parentId: "" });
interface Node extends Department {
  children: Node[];
}
const tree = computed(() => {
  const map = new Map<string, Node>(
    items.value.map((d) => [d.id, { ...d, children: [] }]),
  );
  const roots: Node[] = [];
  for (const node of map.values()) {
    if (node.parentId && map.has(node.parentId))
      map.get(node.parentId)!.children.push(node);
    else roots.push(node);
  }
  return roots;
});
const parentOptions = computed(() =>
  items.value.filter((d) => {
    let current: Department | undefined = d;
    const visited = new Set<string>();
    while (current) {
      if (current.id === editing.value?.id || visited.has(current.id))
        return false;
      visited.add(current.id);
      current = items.value.find((p) => p.id === current!.parentId);
    }
    return true;
  }),
);
async function load() {
  loading.value = true;
  error.value = "";
  try {
    items.value = (
      await request<{ items: Department[] }>("/api/admin/departments")
    ).items;
    selected.value =
      items.value.find((d) => d.id === selected.value?.id) ||
      items.value[0] ||
      null;
  } catch (e) {
    items.value = [];
    selected.value = null;
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function edit(department: Department | null, parentId = "") {
  editing.value = department;
  Object.assign(form, {
    name: department?.name || "",
    parentId: department?.parentId || parentId,
  });
  formError.value = "";
  open.value = true;
}
async function save() {
  if (saving.value) return;
  if (!form.name.trim()) {
    formError.value = "请填写部门名称";
    return;
  }
  saving.value = true;
  formError.value = "";
  try {
    const result = await request<Department>(
      `/api/admin/departments${editing.value ? `/${editing.value.id}` : ""}`,
      {
        method: editing.value ? "PATCH" : "POST",
        body: JSON.stringify({
          name: form.name.trim(),
          parentId: form.parentId || null,
        }),
      },
    );
    selected.value = result;
    open.value = false;
    await load();
  } catch (e) {
    formError.value = errorMessage(e);
  } finally {
    saving.value = false;
  }
}
async function remove() {
  const item = selected.value;
  if (!item) return;
  try {
    await ElMessageBox.confirm(
      `删除“${item.name}”？部门内有人员或子部门时无法删除。`,
      "删除部门",
      { confirmButtonText: "删除", cancelButtonText: "取消", type: "warning" },
    );
  } catch {
    return;
  }
  try {
    await request(`/api/admin/departments/${item.id}`, { method: "DELETE" });
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
  <section aria-label="部门管理">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div class="workspace-toolbar">
      <span class="status-text">{{ items.length }} 个部门</span
      ><span class="toolbar-spacer" /><el-button
        :loading="loading"
        @click="load"
        >刷新</el-button
      ><el-button type="primary" @click="edit(null)">新增部门</el-button>
    </div>
    <div class="department-layout" v-loading="loading">
      <div class="workspace-surface">
        <el-tree
          :data="tree"
          node-key="id"
          :props="{ label: 'name', children: 'children' }"
          default-expand-all
          highlight-current
          :current-node-key="selected?.id"
          empty-text="暂无部门"
          @node-click="selected = $event"
        />
      </div>
      <div class="workspace-surface department-detail">
        <template v-if="selected"
          ><h2>{{ selected.name }}</h2>
          <p class="status-text">
            上级部门：{{
              items.find((d) => d.id === selected?.parentId)?.name || "无"
            }}
          </p>
          <el-button @click="edit(selected)">编辑部门</el-button
          ><el-button @click="edit(null, selected.id)">添加子部门</el-button
          ><el-button text type="danger" @click="remove"
            >删除</el-button
          ></template
        ><el-empty v-else description="添加第一个部门" :image-size="60" />
      </div>
    </div>
    <el-dialog
      v-model="open"
      :title="editing ? '编辑部门' : '新增部门'"
      width="440px"
      class="account-dialog"
      :before-close="close"
      :close-on-click-modal="false"
      destroy-on-close
      ><el-alert
        v-if="formError"
        :title="formError"
        type="error"
        :closable="false"
      /><el-form label-position="top"
        ><el-form-item label="部门名称" required
          ><el-input
            v-model="form.name"
            aria-label="部门名称"
            maxlength="80" /></el-form-item
        ><el-form-item label="上级部门"
          ><el-select
            v-model="form.parentId"
            aria-label="上级部门"
            clearable
            placeholder="无"
            ><el-option
              v-for="d in parentOptions"
              :key="d.id"
              :value="d.id"
              :label="d.name" /></el-select></el-form-item></el-form
      ><template #footer
        ><el-button :disabled="saving" @click="close(() => (open = false))"
          >取消</el-button
        ><el-button type="primary" :loading="saving" @click="save"
          >保存</el-button
        ></template
      ></el-dialog
    >
  </section>
</template>
