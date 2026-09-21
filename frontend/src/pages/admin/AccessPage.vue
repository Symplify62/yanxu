<script setup lang="ts">
import { ref } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import type { Role, Group } from "../../domain/types";
import RequestState from "../../components/RequestState.vue";
const props = defineProps<{ kind: "roles" | "groups" }>(),
  { data, error, loading, refresh } = usePolling(api.admin.get),
  role = ref<Role>(),
  group = ref<Group>(),
  members = ref<string[]>([]),
  drawer = ref(false),
  dialog = ref(false),
  busy = ref(false),
  mutationError = ref("");
function edit(id: string) {
  const g = data.value!.groups.find((g) => g.id === id)!;
  group.value = { ...g, members: [...g.members] };
  members.value = [...g.members];
  mutationError.value = "";
  dialog.value = true;
}
async function save() {
  if (!group.value) return;
  busy.value = true;
  try {
    await api.admin.group(group.value.id, members.value, group.value.version);
    dialog.value = false;
    await refresh();
  } catch (e) {
    mutationError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page-heading">
    <div>
      <p class="eyebrow">身份与资料访问</p>
      <h1>{{ kind === "roles" ? "角色权限" : "业务访问组" }}</h1>
      <p class="muted">角色决定功能，会议范围决定可操作对象。</p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><template v-else-if="data"
    ><template v-if="kind === 'roles'"
      ><el-alert
        title="当前迁移预置角色目录。完整自定义角色与委派编辑仍按页面规格后续实现。"
        type="info"
        :closable="false"
      /><el-table :data="data.roles" class="block-gap"
        ><el-table-column
          prop="name"
          label="角色"
          min-width="180"
        /><el-table-column label="权限" min-width="280"
          ><template #default="{ row }"
            ><el-tag v-for="p in row.permissions" :key="p" class="tag-gap">{{
              p
            }}</el-tag></template
          ></el-table-column
        ><el-table-column label="操作" width="150"
          ><template #default="{ row }"
            ><el-button
              size="small"
              @click="
                role = data!.roles.find((r) => r.id === String(row.id));
                drawer = true;
              "
              >查看权限</el-button
            ></template
          ></el-table-column
        ></el-table
      ></template
    ><el-table v-else :data="data.groups"
      ><el-table-column
        prop="name"
        label="访问组"
        min-width="180"
      /><el-table-column label="成员" min-width="220"
        ><template #default="{ row }">{{
          row.members
            .map((id: string) => data?.people.find((u) => u.id === id)?.name)
            .join("、") || "暂无成员"
        }}</template></el-table-column
      ><el-table-column label="操作" width="140"
        ><template #default="{ row }"
          ><el-button size="small" @click="edit(String(row.id))"
            >维护成员</el-button
          ></template
        ></el-table-column
      ></el-table
    ></template
  >
  <el-drawer v-model="drawer" title="角色权限" size="min(420px,100vw)"
    ><h2>{{ role?.name }}</h2>
    <el-tag v-if="role?.protected" type="warning">保护角色</el-tag
    ><el-descriptions :column="1" border class="block-gap"
      ><el-descriptions-item label="功能">{{
        role?.permissions.join("、")
      }}</el-descriptions-item
      ><el-descriptions-item label="会议范围"
        >由本人归属或独立授权决定，不因角色名自动读全公司。</el-descriptions-item
      ></el-descriptions
    ></el-drawer
  >
  <el-dialog
    v-model="dialog"
    title="维护业务组成员"
    width="min(520px,94vw)"
    :close-on-click-modal="false"
    ><el-alert
      title="成员变更可能影响该组已有共享记录；不改变部门归属或管理员资格。"
      type="warning"
      :closable="false"
    /><el-form label-position="top" class="block-gap"
      ><el-form-item label="有效公司员工"
        ><el-select
          v-model="members"
          multiple
          filterable
          aria-label="访问组成员"
          ><el-option
            v-for="u in data?.people.filter((u) => u.active && !u.admin)"
            :key="u.id"
            :value="u.id"
            :label="u.name" /></el-select></el-form-item></el-form
    ><el-alert
      v-if="mutationError"
      :title="mutationError"
      type="error"
      :closable="false"
    /><template #footer
      ><el-button @click="dialog = false">取消</el-button
      ><el-button type="primary" :loading="busy" @click="save"
        >确认成员变更</el-button
      ></template
    ></el-dialog
  >
</template>
