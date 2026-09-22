<script setup lang="ts">
import { onBeforeUnmount, ref } from "vue";
import { Play, Pause, AudioLines } from "@lucide/vue";
import sample from "./assets/sample.wav";
const audio = ref<HTMLAudioElement>();
const playing = ref(false);
const error = ref("");
async function toggle() {
  if (!audio.value) return;
  if (playing.value) audio.value.pause();
  else {
    try {
      await audio.value.play();
      error.value = "";
    } catch {
      error.value = "示例音频播放失败，请重试。";
    }
  }
}
onBeforeUnmount(() => audio.value?.pause());
</script>
<template>
  <div class="sample-player">
    <button
      :aria-label="playing ? '暂停示例录音' : '播放示例录音'"
      @click="toggle"
    >
      <Pause v-if="playing" :size="17" /><Play v-else :size="17" />
    </button>
    <AudioLines :size="24" /><span>{{
      playing ? "正在播放合成示例" : "试听合成示例"
    }}</span>
    <audio
      ref="audio"
      :src="sample"
      preload="metadata"
      @play="playing = true"
      @pause="playing = false"
      @ended="playing = false"
      @error="error = '示例音频暂不可用。'"
    />
  </div>
  <p v-if="error" class="form-error" role="alert">{{ error }}</p>
</template>
