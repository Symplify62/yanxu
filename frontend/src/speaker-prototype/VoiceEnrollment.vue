<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from "vue";
import { Mic, RotateCcw, Check, AudioLines, ArrowRight } from "@lucide/vue";
import Button from "../design-lab/kits/ElementButton.vue";
import Input from "../design-lab/kits/ElementInput.vue";
import Checkbox from "../design-lab/kits/ElementCheckbox.vue";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import SamplePlayer from "./SamplePlayer.vue";
import { clock, type Person } from "./model";

const props = defineProps<{
  person: Person | null;
  nextName?: string;
  error?: string;
}>();
const emit = defineEmits<{
  close: [];
  save: [name: string, seconds: number, consent: boolean, next: boolean];
}>();
const stage = ref<"ready" | "recording" | "review">("ready");
const name = ref("");
const seconds = ref(0);
const confirmed = ref(false);
const consent = ref(false);
const discard = ref(false);
let timer: ReturnType<typeof setInterval> | undefined;
function stopTimer() {
  clearInterval(timer);
}
watch(
  () => props.person?.id,
  () => {
    stopTimer();
    stage.value = "ready";
    name.value = props.person?.name || "";
    seconds.value = 0;
    confirmed.value = false;
    consent.value = props.person?.voice?.consent || false;
    discard.value = false;
  },
  { immediate: true },
);
watch(name, () => {
  confirmed.value = false;
});
onUnmounted(stopTimer);
function record() {
  seconds.value = 0;
  stage.value = "recording";
  confirmed.value = false;
  timer = setInterval(() => (seconds.value += 1), 1000);
}
function stop() {
  stopTimer();
  stage.value = "review";
  seconds.value = Math.max(seconds.value, 1);
}
function close() {
  if (stage.value !== "ready") {
    discard.value = true;
    return;
  }
  emit("close");
}
function cancel() {
  stopTimer();
  emit("close");
}
const savable = computed(
  () =>
    stage.value === "review" &&
    name.value.trim() &&
    confirmed.value &&
    (props.person?.scope === "guest" || consent.value),
);
function save(next: boolean) {
  if (!savable.value) return;
  emit("save", name.value.trim(), seconds.value, consent.value, next);
}
</script>

<template>
  <Dialog :model-value="!!person" title="录入声音" @update:model-value="close">
    <div v-if="person" class="voice-enrollment">
      <div class="voice-person">
        <span class="person-avatar large">{{ person.name.slice(-2) }}</span>
        <div>
          <strong>{{ person.name }}</strong>
          <p>{{ person.detail || "本场来宾" }}</p>
        </div>
        <span class="scope-tag">{{
          person.scope === "member" ? "成员档案" : "仅本场"
        }}</span>
      </div>

      <template v-if="stage === 'ready'">
        <div class="voice-prompt">
          <Mic :size="26" />
          <p>请 {{ person.name }} 本人说</p>
          <blockquote>
            “我是{{ person.name }}，<br />今天和大家一起讨论项目进展。”
          </blockquote>
        </div>
        <p class="quiet-note">保持正常音量，其他人暂时安静。</p>
        <p v-if="person.voice" class="quiet-note">
          确认新录音前，原声音档案仍保留。
        </p>
      </template>

      <div
        v-else-if="stage === 'recording'"
        class="voice-prompt is-recording"
        role="status"
      >
        <div class="sound-bars">
          <i v-for="n in 19" :key="n" :style="{ '--n': n }"></i>
        </div>
        <strong class="voice-clock">{{ clock(seconds) }}</strong>
        <p>{{ person.name }}，请继续说完这句话</p>
      </div>

      <template v-else>
        <div class="recording-preview">
          <div>
            <AudioLines :size="19" /><strong>试听录音</strong
            ><span>合成示例</span>
          </div>
          <SamplePlayer />
        </div>
        <label class="field-label" for="confirmed-name">确认姓名</label>
        <Input id="confirmed-name" v-model="name" label="确认姓名" />
        <div class="voice-checks">
          <Checkbox
            v-model="confirmed"
            label="本人确认：姓名正确，录音是我的声音"
          />
          <Checkbox
            v-if="person.scope === 'member'"
            v-model="consent"
            label="同意保存声音，用于下次会议识别"
          />
          <p v-else class="quiet-note">仅用于本场会议，不进入长期声音档案。</p>
        </div>
      </template>
      <p v-if="error" class="form-error" role="alert">{{ error }}</p>
      <p class="simulation-note">
        本原型模拟收声，试听为合成音频，不会开启麦克风。
      </p>
    </div>
    <template #footer>
      <div class="voice-footer">
        <Button secondary @click="close">取消</Button>
        <Button v-if="stage === 'ready'" @click="record"
          ><Mic :size="16" />开始录入</Button
        >
        <Button v-else-if="stage === 'recording'" @click="stop"
          >结束录入</Button
        >
        <template v-else>
          <Button secondary @click="record"
            ><RotateCcw :size="15" />重录</Button
          >
          <Button :disabled="!savable" @click="save(false)"
            ><Check :size="16" />确认保存</Button
          >
        </template>
      </div>
      <button
        v-if="stage === 'review' && nextName"
        class="next-person-button"
        :disabled="!savable"
        @click="save(true)"
      >
        保存并录入 {{ nextName }}<ArrowRight :size="15" />
      </button>
    </template>
  </Dialog>
  <Dialog
    :model-value="discard"
    title="放弃这次录入？"
    @update:model-value="discard = false"
  >
    <p>本次未保存的录音将丢弃，原有声音档案不变。</p>
    <template #footer
      ><Button secondary @click="discard = false">继续录入</Button
      ><Button @click="cancel">放弃录入</Button></template
    >
  </Dialog>
</template>
