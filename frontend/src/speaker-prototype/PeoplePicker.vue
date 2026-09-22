<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { ElDrawer, ElInput } from "element-plus";
import { Search, Plus, X } from "@lucide/vue";
import PersonTile from "./PersonTile.vue";
import PeopleSelectionControl from "./PeopleSelectionControl.vue";
import Button from "../design-lab/kits/ElementButton.vue";
import type { PrototypeModel } from "./model";
const props = defineProps<{ model: PrototypeModel; open: boolean }>();
defineEmits<{ close: []; add: []; enroll: [id: string] }>();
const query = ref(""),
  dept = ref("");
const { selected, available, departments, selectedIds, phase } = props.model;
watch(
  () => props.open,
  (open) => {
    if (open) {
      query.value = "";
      dept.value = "";
    }
  },
);
const people = computed(() =>
  available.value.filter(
    (p) =>
      (!dept.value || p.departmentId === dept.value) &&
      `${p.name} ${p.detail}`.includes(query.value.trim()),
  ),
);
</script>
<template>
  <ElDrawer
    :model-value="open"
    title="选择参会者"
    size="min(560px, 100vw)"
    class="people-drawer"
    @close="$emit('close')"
  >
    <div class="picker-search">
      <Search :size="18" /><ElInput
        v-model="query"
        aria-label="搜索参会者"
        placeholder="搜索姓名或备注"
        clearable
      />
    </div>
    <div class="department-chips" aria-label="部门筛选">
      <button :aria-pressed="!dept" @click="dept = ''">全部</button
      ><button
        v-for="d in departments.filter((d) => d.parentId)"
        :key="d.id"
        :aria-pressed="dept === d.id"
        @click="dept = d.id"
      >
        {{ d.name }}
      </button>
    </div>
    <div class="picker-selection-toolbar">
      <PeopleSelectionControl
        :model="model"
        :people="people"
        scope="filtered"
      />
      <span>当前 {{ people.length }} 人</span>
    </div>
    <div class="picker-grid">
      <PersonTile
        v-for="p in people"
        :key="p.id"
        :person="p"
        :selected="selectedIds.includes(p.id)"
        :locked="
          !model.can('record') ||
          (phase !== 'setup' && selectedIds.includes(p.id))
        "
        :voice-blocked="model.voiceEnrollmentBlock(p)"
        @toggle="model.toggle(p.id)"
        @enroll="$emit('enroll', p.id)"
      />
    </div>
    <div v-if="!people.length" class="empty-state">
      <Search :size="25" />
      <h3>没有找到这位同事</h3>
      <p>可以直接添加一位本场来宾。</p>
    </div>
    <button class="add-guest-inline" @click="$emit('add')">
      <Plus :size="18" />添加临时来宾<span>仅用于本场</span>
    </button>
    <template #footer
      ><div class="picker-footer">
        <span>已选 {{ selected.length }} 人</span
        ><Button @click="$emit('close')">完成选择</Button>
      </div></template
    >
  </ElDrawer>
</template>
