<script setup lang="ts">
import { ref, watch } from "vue";
import type { Meeting, RevisionInput } from "../domain/types";
import { api } from "../services/api";
const visible = defineModel<boolean>({ default: false }),
  props = defineProps<{ meeting: Meeting }>(),
  emit = defineEmits<{ saved: [] }>();
const draft = ref<RevisionInput>({
    expectedVersion: 1,
    summary: "",
    tasks: [],
    reason: "",
  }),
  error = ref(""),
  busy = ref(false);
watch(visible, (v) => {
  if (v) {
    draft.value = {
      expectedVersion: props.meeting.version,
      summary: props.meeting.summary,
      tasks: structuredClone(props.meeting.tasks),
      reason: "",
    };
    error.value = "";
  }
});
async function save() {
  busy.value = true;
  error.value = "";
  try {
    await api.meetings.revise(props.meeting.id, draft.value);
    visible.value = false;
    emit("saved");
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
    :close-on-click-overlay="false"
    class="mobile-edit-popup"
    ><h2 class="popup-heading">主动更正纪要与事项</h2>
    <van-notice-bar
      text="保存新版本，不重复发群；AI原稿和已发送快照保留。"
      wrapable
    /><van-form @submit="save"
      ><van-cell-group inset
        ><van-field
          v-model="draft.summary"
          name="summary"
          label="纪要"
          type="textarea"
          rows="4"
          autosize
          :rules="[{ required: true, message: '请填写纪要内容' }]"
      /></van-cell-group>
      <div v-for="(task, i) in draft.tasks" :key="task.id" class="task-editor">
        <h3>事项 {{ i + 1 }}</h3>
        <van-cell-group inset
          ><van-field
            v-model="task.text"
            :name="'task-text-' + i"
            label="事项说明"
            type="textarea"
            rows="2"
            :rules="[
              { required: true, message: '事项说明不能为空' },
            ]" /><van-field
            v-model="task.owner"
            :name="'task-owner-' + i"
            label="负责人"
            placeholder="未明确可留空" /><van-field
            v-model="task.due"
            :name="'task-due-' + i"
            label="期限原文"
            placeholder="未明确可留空"
        /></van-cell-group>
        <p class="small muted inset-copy">
          依据 {{ task.evidence }} · 不自动派单或解析不明确日期
        </p>
      </div>
      <van-cell-group inset
        ><van-field
          v-model="draft.reason"
          name="reason"
          label="更正原因"
          placeholder="说明核对依据"
          :rules="[
            { required: true, message: '请填写更正原因' },
          ]" /></van-cell-group
      ><van-notice-bar
        v-if="error"
        :text="error"
        wrapable
        color="#a33f37"
        background="#fff0ee"
      />
      <div class="popup-actions">
        <van-button block type="primary" native-type="submit" :loading="busy"
          >保存更正，不重发</van-button
        ><van-button block @click="visible = false">取消修改</van-button>
      </div></van-form
    ></van-popup
  >
</template>
