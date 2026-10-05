<script setup lang="ts">
import { onMounted, onUnmounted, ref } from "vue";
import { errorMessage, request } from "./api";
import type { AdminRecording } from "./types";
import { stageLabels, type Stage } from "../records/model";

const items = ref<AdminRecording[]>([]);
const selected = ref<AdminRecording | null>(null);
const searchText = ref(""),
  query = ref(""),
  source = ref("all"),
  status = ref("all");
const page = ref(1),
  total = ref(0),
  loading = ref(false),
  error = ref("");
const player = ref<HTMLAudioElement>();
const pageSize = 20;
let alive = true;
const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0")}:${Math.floor(seconds % 60)
    .toString()
    .padStart(2, "0")}`;
const statusName = (value: string) => stageLabels[value as Stage] || value;
const ownerName = (record: AdminRecording) =>
  record.source === "guest"
    ? "访客录音"
    : record.ownerName || record.ownerUsername || "账号录音";
const audioUrl = (id: string, download = false) =>
  `/api/recordings/${id}/audio${download ? "?download=true" : ""}`;

async function load() {
  loading.value = true;
  error.value = "";
  try {
    const params = new URLSearchParams({
      q: query.value,
      source: source.value,
      status: status.value,
      limit: String(pageSize),
      offset: String((page.value - 1) * pageSize),
    });
    const response = await request<{ items: AdminRecording[]; total: number }>(
      `/api/admin/recordings?${params}`,
    );
    if (!alive) return;
    items.value = response.items;
    total.value = response.total;
  } catch (e) {
    items.value = [];
    total.value = 0;
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
async function detail(item: AdminRecording) {
  loading.value = true;
  error.value = "";
  try {
    const response = await request<AdminRecording>(
      `/api/admin/recordings/${item.id}`,
    );
    if (alive) selected.value = response;
  } catch (e) {
    error.value = errorMessage(e);
  } finally {
    loading.value = false;
  }
}
function search() {
  query.value = searchText.value.trim();
  page.value = 1;
  void load();
}
function filter() {
  page.value = 1;
  void load();
}
function back() {
  player.value?.pause();
  selected.value = null;
}
function seek(seconds: number) {
  if (!player.value) return;
  player.value.currentTime = seconds;
  void player.value.play().catch(() => {
    error.value = "录音暂时无法播放";
  });
}
onMounted(load);
onUnmounted(() => {
  alive = false;
  player.value?.pause();
});
</script>
<template>
  <section aria-label="所有录音">
    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      show-icon
    />
    <template v-if="selected">
      <div class="workspace-toolbar">
        <el-button @click="back">返回列表</el-button
        ><span class="toolbar-spacer" /><el-button
          :loading="loading"
          @click="detail(selected)"
          >刷新</el-button
        >
      </div>
      <div class="workspace-surface admin-record-detail" v-loading="loading">
        <div class="admin-record-title">
          <div>
            <h2>{{ selected.title }}</h2>
            <p class="status-text">
              {{ ownerName(selected) }} ·
              {{
                new Date(selected.createdAt).toLocaleString("zh-CN", {
                  hour12: false,
                })
              }}
            </p>
          </div>
          <el-tag>{{ statusName(selected.status) }}</el-tag>
        </div>
        <div class="admin-record-facts">
          <span>时长 {{ clock(selected.duration) }}</span
          ><span v-if="selected.participants?.length"
            >参会
            {{ selected.participants.map((p) => p.name).join("、") }}</span
          ><span v-if="selected.interrupted">录制中断</span>
        </div>
        <el-alert
          v-if="selected.error"
          :title="selected.error"
          type="warning"
          :closable="false"
        />
        <div v-if="selected.hasAudio" class="admin-record-audio">
          <audio
            ref="player"
            :src="audioUrl(selected.id)"
            controls
            preload="metadata"
          /><a :href="audioUrl(selected.id, true)">下载录音</a>
        </div>
        <p v-else class="panel-note">录音文件尚未就绪</p>
        <section class="admin-record-section">
          <h3>AI 分析</h3>
          <template v-if="selected.analysis"
            ><p class="admin-record-summary">{{ selected.analysis.summary }}</p>
            <template v-if="selected.analysis.points?.length"
              ><h4>讨论重点</h4>
              <ul>
                <li v-for="point in selected.analysis.points" :key="point">
                  {{ point }}
                </li>
              </ul></template
            ><template v-if="selected.analysis.decisions?.length"
              ><h4>主要决定</h4>
              <ul>
                <li
                  v-for="decision in selected.analysis.decisions"
                  :key="decision"
                >
                  {{ decision }}
                </li>
              </ul></template
            ><template v-if="selected.analysis.tasks?.length"
              ><h4>行动事项</h4>
              <ul>
                <li
                  v-for="(task, index) in selected.analysis.tasks"
                  :key="index"
                >
                  {{ task.text
                  }}<span v-if="task.owner"> · {{ task.owner }}</span
                  ><span v-if="task.due"> · {{ task.due }}</span>
                </li>
              </ul></template
            ></template
          >
          <p v-else class="status-text">尚未生成</p>
        </section>
        <section class="admin-record-section">
          <h3>逐字稿</h3>
          <p v-if="selected.speakerStatus === 'waiting'" class="status-text">
            正在识别发言人
          </p>
          <p v-if="selected.speakerStatus === 'failed'" class="status-text">
            发言人识别未完成
          </p>
          <template v-if="selected.transcript?.segments.length"
            ><article
              v-for="(segment, index) in selected.transcript.segments"
              :key="segment.id || index"
              class="transcript-segment"
            >
              <header>
                <strong>{{ segment.speaker || "未识别" }}</strong
                ><el-button
                  text
                  :disabled="!selected.hasAudio"
                  @click="seek(segment.start)"
                  >{{ clock(segment.start) }}</el-button
                >
              </header>
              <p>{{ segment.text }}</p>
            </article></template
          >
          <p v-else class="status-text">尚未生成</p>
        </section>
        <details class="admin-record-technical">
          <summary>记录信息</summary>
          <p>记录 ID：{{ selected.id }}</p>
          <p v-if="selected.sha256">SHA-256：{{ selected.sha256 }}</p>
          <p v-if="selected.ownerUsername">
            录制账号：{{ selected.ownerUsername }}
          </p>
        </details>
      </div>
    </template>
    <template v-else>
      <div class="workspace-toolbar admin-record-filters">
        <el-input
          v-model="searchText"
          aria-label="搜索录音"
          placeholder="搜索标题或录制人"
          clearable
          @keyup.enter="search"
        />
        <el-select v-model="source" aria-label="录音来源" @change="filter"
          ><el-option label="全部来源" value="all" /><el-option
            label="访客录音"
            value="guest" /><el-option label="账号录音" value="account"
        /></el-select>
        <el-select v-model="status" aria-label="录音状态" @change="filter"
          ><el-option label="全部状态" value="all" /><el-option
            label="处理中"
            value="processing" /><el-option
            label="已完成"
            value="complete" /><el-option label="异常" value="failed"
        /></el-select>
        <el-button @click="search">搜索</el-button
        ><span class="toolbar-spacer" /><el-button
          :loading="loading"
          @click="load"
          >刷新</el-button
        >
      </div>
      <div class="workspace-surface desktop-people" v-loading="loading">
        <el-table :data="items" empty-text="暂无录音"
          ><el-table-column
            prop="title"
            label="录音"
            min-width="210"
          /><el-table-column label="录制人" min-width="120"
            ><template #default="{ row }">{{
              ownerName(row as AdminRecording)
            }}</template></el-table-column
          ><el-table-column label="时间" min-width="165"
            ><template #default="{ row }">{{
              new Date(row.createdAt).toLocaleString("zh-CN", { hour12: false })
            }}</template></el-table-column
          ><el-table-column label="时长" width="90"
            ><template #default="{ row }">{{
              clock(row.duration)
            }}</template></el-table-column
          ><el-table-column label="状态" width="110"
            ><template #default="{ row }">{{
              statusName(row.status)
            }}</template></el-table-column
          ><el-table-column label="操作" width="110"
            ><template #default="{ row }"
              ><el-button
                text
                type="primary"
                @click="detail(row as AdminRecording)"
                >查看</el-button
              ></template
            ></el-table-column
          ></el-table
        >
      </div>
      <div class="workspace-surface mobile-people" v-loading="loading">
        <div v-if="!items.length && !loading" class="mobile-person status-text">
          暂无录音
        </div>
        <button
          v-for="item in items"
          :key="item.id"
          class="admin-record-mobile"
          @click="detail(item)"
        >
          <strong>{{ item.title }}</strong
          ><span>{{ ownerName(item) }} · {{ statusName(item.status) }}</span
          ><small
            >{{
              new Date(item.createdAt).toLocaleString("zh-CN", {
                hour12: false,
              })
            }}
            · {{ clock(item.duration) }}</small
          >
        </button>
      </div>
      <div v-if="total > pageSize" class="workspace-toolbar admin-record-pages">
        <el-button
          :disabled="page === 1 || loading"
          @click="
            page--;
            load();
          "
          >上一页</el-button
        ><span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span
        ><el-button
          :disabled="page * pageSize >= total || loading"
          @click="
            page++;
            load();
          "
          >下一页</el-button
        >
      </div>
      <p class="panel-note">共 {{ total }} 条录音</p>
    </template>
  </section>
</template>
