<script setup lang="ts">
import { ref } from "vue";
import {
  Fingerprint,
  Mic,
  SlidersHorizontal,
  Check,
  ChevronRight,
} from "@lucide/vue";
import { ElSelect, ElOption, ElSwitch } from "element-plus";
import Button from "../design-lab/kits/ElementButton.vue";
import {
  voiceLabels,
  voiceState,
  type PrototypeModel,
  type Person,
} from "./model";
const props = defineProps<{ model: PrototypeModel }>();
defineEmits<{ enroll: [id: string]; voice: [p: Person] }>();
const saved = ref(false),
  testStatus = ref("");
function testMic() {
  testStatus.value = "演示检测完成 · 麦克风未实际启用";
}
</script>
<template>
  <main class="settings-page">
    <div class="record-heading">
      <div>
        <span class="section-eyebrow">言序 / 设置</span>
        <h1>个人与设备设置</h1>
      </div>
    </div>
    <section class="settings-section">
      <div class="settings-section-title">
        <Fingerprint :size="21" />
        <h2>我的声音</h2>
      </div>
      <div v-if="model.actor.value" class="personal-voice">
        <span class="person-avatar large">{{
          model.actor.value.name.slice(-2)
        }}</span>
        <div>
          <strong>{{ model.actor.value.name }}</strong>
          <p>
            {{ model.departmentName(model.actor.value.departmentId) }} ·
            {{ voiceLabels[voiceState(model.actor.value)] }}
          </p>
        </div>
        <button class="text-action" @click="$emit('voice', model.actor.value)">
          管理<ChevronRight :size="15" />
        </button>
      </div>
      <Button
        secondary
        :disabled="!model.actor.value?.active"
        @click="$emit('enroll', model.actorId.value)"
        >{{
          model.actor.value?.voice ? "重新录入声音" : "录入我的声音"
        }}</Button
      >
    </section>
    <section class="settings-section">
      <div class="settings-section-title">
        <Mic :size="21" />
        <h2>录音设备</h2>
      </div>
      <div class="setting-row">
        <div>
          <strong>麦克风</strong>
          <p>本页为设备配置演示</p>
        </div>
        <ElSelect
          v-model="model.state.value.preferences.microphone"
          aria-label="麦克风"
          ><ElOption value="内置麦克风" label="内置麦克风" /><ElOption
            value="会议麦克风（示例）"
            label="会议麦克风（示例）"
        /></ElSelect>
      </div>
      <div class="setting-row">
        <div>
          <strong>录音品质</strong>
          <p>正式设备接入后生效</p>
        </div>
        <ElSelect
          v-model="model.state.value.preferences.quality"
          aria-label="录音品质"
          ><ElOption value="标准" label="标准" /><ElOption
            value="高品质"
            label="高品质"
        /></ElSelect>
      </div>
      <Button secondary @click="testMic">体验拾音检测</Button>
      <p v-if="testStatus" class="quiet-note" role="status">{{ testStatus }}</p>
    </section>
    <section class="settings-section">
      <div class="settings-section-title">
        <SlidersHorizontal :size="21" />
        <h2>会议偏好</h2>
      </div>
      <div class="setting-row">
        <div>
          <strong>记住本场成员</strong>
          <p>下一场沿用已选成员，临时来宾除外</p>
        </div>
        <ElSwitch
          v-model="model.state.value.preferences.rememberPeople"
          aria-label="记住本场成员"
        />
      </div>
    </section>
    <p class="settings-saved"><Check :size="14" />设置自动保存在本浏览器</p>
  </main>
</template>
