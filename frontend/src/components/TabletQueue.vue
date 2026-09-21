<script setup lang="ts">
import type { DeviceView } from "../domain/types";
import { duration } from "../domain/presentation";
import MeetingStatus from "./MeetingStatus.vue";
defineProps<{ queue: DeviceView["queue"] }>();
</script>
<template>
  <div class="device-queue">
    <h3>设备处理队列</h3>
    <p v-if="!queue.length" class="small muted">当前没有待传记录</p>
    <div v-for="job in queue.slice(-3)" :key="job.id" class="queue-row">
      <span class="mono">{{ job.id }} · {{ duration(job.duration) }}</span
      ><MeetingStatus :state="job.state" />
    </div>
  </div>
</template>
