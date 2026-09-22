<script setup lang="ts">
import { computed } from "vue";
import { Check, UserRound, AudioLines, Mic, RotateCcw } from "@lucide/vue";
import { voiceLabels, voiceState, type Person } from "./model";
const props = defineProps<{
  person: Person;
  selected?: boolean;
  locked?: boolean;
  voiceBlocked?: string;
}>();
defineEmits<{ toggle: []; enroll: [] }>();
const color = computed(
  () =>
    ["sage", "sand", "blue", "lavender"][
      Array.from(props.person.id).reduce((s, c) => s + c.charCodeAt(0), 0) % 4
    ],
);
</script>
<template>
  <div class="person-option" :data-person-id="person.id">
    <button
      class="person-tile"
      :class="[{ chosen: selected }, color]"
      :aria-label="`${selected ? '取消选择' : '选择'}${person.name}`"
      :aria-pressed="!!selected"
      :disabled="locked"
      @click="$emit('toggle')"
    >
      <span class="tile-face"
        ><span>{{ person.name.slice(-2) }}</span
        ><span v-if="selected" class="tile-check"><Check :size="12" /></span
      ></span>
      <strong>{{ person.name }}</strong>
      <span class="tile-status" :class="voiceState(person)"
        ><AudioLines
          v-if="voiceState(person) === 'ready'"
          :size="11"
        /><UserRound v-if="person.scope === 'guest'" :size="11" />{{
          person.scope === "guest"
            ? "本场来宾"
            : voiceLabels[voiceState(person)] === "未录入"
              ? "待录入"
              : `声纹${voiceLabels[voiceState(person)]}`
        }}</span
      >
    </button>
    <button
      class="tile-voice-action"
      :disabled="!!voiceBlocked || voiceState(person) === 'generating'"
      :title="
        voiceBlocked ||
        (voiceState(person) === 'ready'
          ? '重新录制并确认后替换原档案'
          : '录入声音，不改变本场选择')
      "
      :aria-label="`${voiceState(person) === 'ready' ? '重录' : '录制'}${person.name}的声纹`"
      @click="$emit('enroll')"
    >
      <RotateCcw v-if="voiceState(person) === 'ready'" :size="12" />
      <Mic v-else :size="12" />
      {{
        voiceState(person) === "generating"
          ? "生成中"
          : voiceBlocked?.includes("结束本场")
            ? "会后录制"
            : voiceState(person) === "ready"
              ? "重录声纹"
              : "录制声纹"
      }}
    </button>
  </div>
</template>
