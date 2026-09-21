<script setup lang="ts">
import {
  Mic,
  Pause,
  Play,
  Square,
  ArrowUpRight,
  Check,
  AudioLines,
  RefreshCw,
} from "@lucide/vue";
import { duration } from "../domain/presentation";
defineProps<{ phase: string; elapsed: number; notice: string }>();
defineEmits<{
  start: [];
  pause: [];
  resume: [];
  finish: [];
  retry: [];
  next: [];
  view: [];
}>();
</script>
<template>
  <section class="p1-record-page">
    <h1 class="p1-record-title">快速录音</h1>
    <div class="p1-rec-layout">
      <div class="p1-rec-card" aria-live="polite">
        <template v-if="phase === 'idle'"
          ><div class="p1-mic-mark"><Mic :size="32" :stroke-width="1.6" /></div>
          <div class="p1-timer">00:00:00</div>

          <el-button
            type="primary"
            size="large"
            class="p1-primary-record"
            @click="$emit('start')"
            ><Mic :size="17" />开始录音</el-button
          > </template
        ><template v-else-if="phase === 'recording' || phase === 'paused'"
          ><div
            class="p1-record-status"
            :class="{ paused: phase === 'paused' }"
          >
            <i></i>{{ phase === "paused" ? "录音已暂停" : "正在录音 · 演示" }}
          </div>
          <div class="p1-timer">{{ duration(elapsed) }}</div>
          <AudioLines :size="62" :stroke-width="1" class="p1-audio-lines" />
          <div class="p1-rec-actions">
            <el-button
              size="large"
              @click="phase === 'paused' ? $emit('resume') : $emit('pause')"
              ><Play v-if="phase === 'paused'" :size="16" /><Pause
                v-else
                :size="16"
              />{{ phase === "paused" ? "继续录音" : "暂停录音" }}</el-button
            ><el-button type="primary" size="large" @click="$emit('finish')"
              ><Square :size="14" />结束并保存</el-button
            >
          </div> </template
        ><template v-else-if="phase === 'saving'"
          ><RefreshCw :size="35" class="p1-spin" />
          <h2>正在保存本次录音</h2>

          <el-button size="large" loading disabled
            >正在保存</el-button
          ></template
        ><template v-else-if="phase === 'save-error'"
          ><div class="p1-failure-mark">!</div>
          <h2>录音尚未保存成功</h2>
          <p class="p1-secondary">请勿关闭页面，重试保存。</p>
          <el-button type="primary" size="large" @click="$emit('retry')"
            >重试保存（演示）</el-button
          ></template
        ><template v-else
          ><div class="p1-mic-mark success"><Check :size="30" /></div>
          <h2>已保存</h2>
          <p class="p1-secondary">正在自动处理。</p>
          <el-button type="primary" size="large" @click="$emit('view')"
            >查看本次结果<ArrowUpRight :size="16" /></el-button
          ><el-button text class="p1-next" @click="$emit('next')"
            >开始下一段录音</el-button
          ></template
        >
        <p v-if="notice" role="alert" class="p1-error">{{ notice }}</p>
      </div>
    </div>
  </section>
</template>
