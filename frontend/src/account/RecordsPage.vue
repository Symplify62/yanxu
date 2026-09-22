<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { errorMessage, request } from "./api";
import type { Recording } from "./types";
import { stageLabels, type Stage } from "../records/model";
const items = ref<Recording[]>([]),
  selected = ref<Recording | null>(null),
  loading = ref(false),
  error = ref("");
const page = ref(1),
  total = ref(0);
const pageSize = 20;
const player = ref<HTMLAudioElement>();
let alive = true;
const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0")}`;
async function load() {
  loading.value = true;
  error.value = "";
  try {
    const response = await request<{ items: Recording[]; total: number }>(
      `/api/managed/recordings?limit=${pageSize}&offset=${(page.value - 1) * pageSize}`,
    );
    if (alive) {
      items.value = response.items;
      total.value = response.total;
    }
  } catch (e) {
    items.value = [];
    selected.value = null;
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function detail(record: Recording) {
  loading.value = true;
  error.value = "";
  try {
    const value = await request<Recording>(
      `/api/managed/recordings/${record.id}`,
    );
    if (alive) selected.value = value;
  } catch (e) {
    selected.value = null;
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function seek(time: number) {
  if (player.value) {
    player.value.currentTime = time;
    void player.value.play().catch(() => {
      error.value = "录音暂时无法播放，请稍后重试";
    });
  }
}
onMounted(load);
onUnmounted(() => {
  alive = false;
  player.value?.pause();
});
</script>
<template>
  <section aria-label="我的录音">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <div class="workspace-toolbar">
      <el-button v-if="selected" @click="selected = null">返回列表</el-button
      ><span class="toolbar-spacer" /><el-button
        :loading="loading"
        @click="selected ? detail(selected) : load()"
        >刷新</el-button
      >
    </div>
    <div
      v-if="selected"
      v-loading="loading"
      class="workspace-surface"
      style="padding: 24px"
    >
      <h2>{{ selected.title }}</h2>
      <p class="status-text">
        {{ stageLabels[selected.status as Stage] || selected.status }}
      </p>
      <audio
        ref="player"
        :src="`/api/recordings/${selected.id}/audio`"
        controls
        class="voice-audio"
      />
      <p v-if="selected.error" class="panel-note">{{ selected.error }}</p>
      <p v-if="selected.analysis?.summary" style="white-space: pre-wrap">
        {{ selected.analysis.summary }}
      </p>
      <h3>逐字稿</h3>
      <p
        v-if="selected.speakerStatus === 'waiting'"
        class="panel-note"
        role="status"
      >
        正在识别发言人
      </p>
      <p
        v-else-if="selected.speakerStatus === 'failed'"
        class="panel-note"
        role="status"
      >
        发言人识别未完成，逐字稿已保留
      </p>
      <template v-if="selected.transcript?.segments.length"
        ><article
          v-for="(segment, index) in selected.transcript.segments"
          :key="segment.id || index"
          class="transcript-segment"
        >
          <header>
            <strong>{{ segment.speaker || "未识别" }}</strong
            ><el-button text @click="seek(segment.start)">{{
              clock(segment.start)
            }}</el-button>
          </header>
          <p>{{ segment.text }}</p>
        </article></template
      ><el-empty v-else description="逐字稿尚未生成" :image-size="60" />
    </div>
    <div v-else v-loading="loading" class="workspace-surface">
      <ul class="record-links">
        <li v-for="record in items" :key="record.id">
          <button :data-record-id="record.id" @click="detail(record)">
            <span
              ><strong>{{ record.title }}</strong
              ><small
                >{{
                  new Date(record.createdAt).toLocaleString("zh-CN", {
                    hour12: false,
                  })
                }}
                · {{ clock(record.duration) }}</small
              ></span
            ><span class="status-text"
              >{{
                stageLabels[record.status as Stage] || record.status
              }}
              ↗</span
            >
          </button>
        </li>
      </ul>
      <el-empty
        v-if="!items.length && !loading"
        description="暂无录音"
        :image-size="60"
      />
    </div>
    <div
      v-if="!selected && total > pageSize"
      class="workspace-toolbar"
      style="justify-content: center; margin-top: 20px"
    >
      <el-button
        :disabled="page === 1 || loading"
        @click="
          page--;
          load();
        "
        >上一页</el-button
      >
      <span class="status-text"
        >{{ page }} / {{ Math.ceil(total / pageSize) }}</span
      >
      <el-button
        :disabled="page * pageSize >= total || loading"
        @click="
          page++;
          load();
        "
        >下一页</el-button
      >
    </div>
  </section>
</template>
