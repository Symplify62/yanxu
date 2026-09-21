<script setup lang="ts">
import { ref, computed } from "vue";
import { api } from "../../services/api";
import { usePolling } from "../../composables/usePolling";
import type { Employee } from "../../domain/types";
import RequestState from "../../components/RequestState.vue";
const props = defineProps<{ organization?: boolean }>(),
  { data, error, loading, refresh } = usePolling(api.admin.get),
  search = ref(""),
  department = ref("sales"),
  selected = ref<Employee>(),
  confirm = ref(false),
  busy = ref(false),
  mutationError = ref(""),
  synced = ref(false);
const people = computed(
  () => data.value?.people.filter((u) => u.name.includes(search.value)) ?? [],
);
const tree = computed(() => [
  {
    id: "company",
    label: "示例公司",
    children:
      data.value?.departments.map((d) => ({ id: d.id, label: d.name })) ?? [],
  },
]);
async function toggle() {
  if (!selected.value) return;
  busy.value = true;
  mutationError.value = "";
  try {
    await api.admin.toggle(selected.value.id);
    confirm.value = false;
    await refresh();
  } catch (e) {
    mutationError.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function sync() {
  busy.value = true;
  try {
    await api.admin.sync();
    synced.value = true;
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
      <p class="eyebrow">企业身份</p>
      <h1>{{ organization ? "组织部门" : "用户与身份" }}</h1>
      <p class="muted">
        有效员工首次登录自动开户，组织归属和会议可见范围分别管理。
      </p>
    </div>
  </div>
  <RequestState
    v-if="loading || error"
    :loading="loading"
    :error="error"
    @retry="refresh"
  /><template v-else-if="data"
    ><template v-if="organization"
      ><div class="organization-layout">
        <el-card shadow="never"
          ><el-tree
            :data="tree"
            default-expand-all
            node-key="id"
            highlight-current
            @node-click="(node: any) => (department = node.id)" /></el-card
        ><el-card shadow="never"
          ><template #header
            ><div class="heading-actions">
              <strong>{{
                data.departments.find((d) => d.id === department)?.name ||
                "示例公司"
              }}</strong
              ><el-button :loading="busy" @click="sync">模拟同步组织</el-button>
            </div></template
          ><el-alert
            v-if="synced"
            title="已完成模拟同步，未访问企业微信。"
            type="success"
            :closable="false"
          /><el-table
            :data="
              data.people.filter(
                (u) => department === 'company' || u.department === department,
              )
            "
            ><el-table-column prop="name" label="人员" /><el-table-column
              label="账号状态"
              ><template #default="{ row }"
                ><el-tag :type="row.active ? 'success' : 'danger'">{{
                  row.active ? "正常" : "停用"
                }}</el-tag></template
              ></el-table-column
            ></el-table
          >
          <p class="small muted block-gap">
            组织同步不改写历史会议，也不会给全部门开放访问权。
          </p></el-card
        >
      </div></template
    ><template v-else
      ><div class="table-toolbar">
        <el-input
          v-model="search"
          placeholder="搜索员工姓名"
          clearable
          class="search-input"
        /><span class="small muted">{{ people.length }} 位公司人员</span>
      </div>
      <el-table :data="people" stripe
        ><el-table-column
          prop="name"
          label="员工"
          min-width="140"
        /><el-table-column label="部门" min-width="120"
          ><template #default="{ row }">{{
            data.departments.find((d) => d.id === row.department)?.name
          }}</template></el-table-column
        ><el-table-column label="开户状态" min-width="170"
          ><template #default="{ row }">{{
            row.registered ? "已自动开户" : "首次登录时自动开通"
          }}</template></el-table-column
        ><el-table-column label="状态" width="100"
          ><template #default="{ row }"
            ><el-tag :type="row.active ? 'success' : 'danger'">{{
              row.active ? "正常" : "已停用"
            }}</el-tag></template
          ></el-table-column
        ><el-table-column label="操作" width="110"
          ><template #default="{ row }"
            ><el-button
              size="small"
              :disabled="row.admin"
              @click="
                selected = data!.people.find((u) => u.id === String(row.id));
                mutationError = '';
                confirm = true;
              "
              >{{ row.active ? "停用" : "启用" }}</el-button
            ></template
          ></el-table-column
        ></el-table
      ></template
    ></template
  >
  <el-dialog v-model="confirm" title="变更账号状态" width="min(460px,94vw)"
    ><el-alert
      :title="
        selected?.active
          ? '停用将撤销现有演示会话，保留原会议和操作记录。'
          : '重新启用后仍需要登录，并按现有授权判断访问。'
      "
      type="warning"
      :closable="false"
    />
    <p class="block-gap">人员：{{ selected?.name }}</p>
    <el-alert
      v-if="mutationError"
      :title="mutationError"
      type="error"
      :closable="false"
    /><template #footer
      ><el-button @click="confirm = false">取消</el-button
      ><el-button type="primary" :loading="busy" @click="toggle"
        >确认变更</el-button
      ></template
    ></el-dialog
  >
</template>
