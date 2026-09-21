<script setup lang="ts">
import { ref, watch, computed } from "vue";
import type { Meeting, Employee, Group } from "../domain/types";
import { api } from "../services/api";
import { sessions } from "../composables/session";
const visible = defineModel<boolean>({ default: false }),
  props = defineProps<{ meeting: Meeting }>(),
  emit = defineEmits<{ changed: [] }>();
const people = ref<Employee[]>([]),
  groups = ref<Group[]>([]),
  selected = ref(""),
  picker = ref(false),
  error = ref(""),
  busy = ref(false);
const options = computed(() => [
  ...people.value
    .filter((u) => u.id !== props.meeting.owner)
    .map((u) => ({ text: u.name, value: u.id })),
  ...groups.value.map((g) => ({
    text: g.name + "（组）",
    value: "group:" + g.id,
  })),
]);
const name = (id: string) =>
  id.startsWith("group:")
    ? groups.value.find((g) => g.id === id.slice(6))?.name
    : people.value.find((u) => u.id === id)?.name;
watch(visible, async (v) => {
  if (v) {
    error.value = "";
    try {
      const result = await api.meetings.people();
      people.value = result.people;
      groups.value = result.groups;
      selected.value = options.value[0]?.value || "";
    } catch (e) {
      error.value = (e as Error).message;
    }
  }
});
async function add() {
  busy.value = true;
  error.value = "";
  try {
    await api.meetings.share(props.meeting.id, selected.value);
    emit("changed");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
async function revoke(id: string) {
  busy.value = true;
  error.value = "";
  try {
    await api.meetings.revoke(props.meeting.id, id);
    emit("changed");
  } catch (e) {
    error.value = (e as Error).message;
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <van-popup
    v-model:show="visible"
    position="bottom"
    round
    closeable
    class="mobile-edit-popup"
    ><h2 class="popup-heading">共享会议查看权</h2>
    <van-notice-bar
      text="仅查看资料和在线回听；不授编辑、下载或管理权，也不发送群消息。"
      wrapable /><van-field
      :model-value="options.find((o) => o.value === selected)?.text"
      label="授权对象"
      readonly
      is-link
      @click="picker = true" />
    <div class="popup-actions">
      <van-button
        block
        type="primary"
        :loading="busy"
        :disabled="!selected"
        @click="add"
        >添加只读授权</van-button
      >
    </div>
    <van-cell-group title="当前授权"
      ><van-cell
        v-for="grant in meeting.grants.filter((g) => g.active)"
        :key="grant.id"
        :title="name(grant.subject) || grant.subject"
        label="只读 · 含在线回听"
        ><template #right-icon
          ><van-button
            v-if="grant.grantedBy === sessions.employee?.id"
            size="small"
            plain
            :disabled="busy"
            @click="revoke(grant.id)"
            >撤销</van-button
          ><van-tag v-else plain>其他授权来源</van-tag></template
        ></van-cell
      ><van-empty
        v-if="!meeting.grants.some((g) => g.active)"
        description="尚未共享"
        image-size="60" /></van-cell-group
    ><van-notice-bar
      v-if="error"
      :text="error"
      wrapable
      color="#a33f37"
      background="#fff0ee" /><van-popup
      v-model:show="picker"
      position="bottom"
      round
      ><van-picker
        title="选择查看者"
        :columns="options"
        @confirm="
          ({ selectedValues }: any) => {
            selected = String(selectedValues[0]);
            picker = false;
          }
        "
        @cancel="picker = false" /></van-popup
  ></van-popup>
</template>
