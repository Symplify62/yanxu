<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { api } from "../services/api";
import { usePolling } from "../composables/usePolling";
import { sessions } from "../composables/session";
import { duration } from "../domain/presentation";
import MeetingStatus from "../components/MeetingStatus.vue";
import MeetingEditor from "../components/MeetingEditor.vue";
import SharingPanel from "../components/SharingPanel.vue";
const route = useRoute(),
  router = useRouter(),
  id = String(route.params.id),
  tab = ref("summary"),
  edit = ref(false),
  share = ref(false),
  snapshot = ref(false);
const {
    data: m,
    error,
    loading,
    refresh,
  } = usePolling(() => api.meetings.get(id)),
  own = computed(() => m.value?.owner === sessions.employee?.id);
const segments = ref<
    Array<{ id: string; time: string; speaker: string; text: string }>
  >([]),
  transcriptError = ref("");
watch([tab, () => m.value?.progress], async () => {
  if (tab.value === "transcript" && m.value && m.value.progress >= 2) {
    try {
      segments.value = await api.meetings.transcript(id);
      transcriptError.value = "";
    } catch (e) {
      transcriptError.value = (e as Error).message;
    }
  }
});
watch(error, (value) => {
  if (value) {
    edit.value = false;
    share.value = false;
    snapshot.value = false;
    segments.value = [];
  }
});
</script>
<template>
  <section class="employee-layout">
    <div class="mobile-surface detail-surface">
      <van-nav-bar
        title="会议资料"
        left-text="我的会议"
        left-arrow
        @click-left="router.push('/employee')"
      />
      <div v-if="loading" class="request-state">
        <van-loading vertical>正在加载</van-loading>
      </div>
      <van-empty
        v-else-if="error || !m"
        image="error"
        description="记录不可用或你没有查看权限"
        ><van-button size="small" @click="router.push('/employee')"
          >返回我的会议</van-button
        ></van-empty
      >
      <template v-else
        ><div class="meeting-heading">
          <p class="eyebrow">{{ own ? "我发起的会议" : "只读共享" }}</p>
          <h1>{{ m.title }}</h1>
          <p class="small muted">
            {{ duration(m.duration) }} · {{ m.createdAt.slice(0, 10) }} ·
            {{ m.department === "sales" ? "销售部" : "财务部" }}
          </p>
          <MeetingStatus :state="m.state" :manual="m.resolvedManually" mobile />
        </div>
        <van-tabs v-model:active="tab" shrink class="meeting-tabs"
          ><van-tab title="纪要" name="summary" /><van-tab
            title="逐字稿"
            name="transcript" /><van-tab title="事项" name="tasks" /><van-tab
            title="录音"
            name="audio" /><van-tab title="版本" name="versions"
        /></van-tabs>
        <div class="meeting-body">
          <template v-if="tab === 'summary'"
            ><template v-if="m.progress >= 3"
              ><h2>会议纪要</h2>
              <p class="meeting-summary">{{ m.summary }}</p>
              <van-notice-bar
                text="AI生成内容可能有误；未知事项如实标注，不阻断自动发送。"
                wrapable
              />
              <div class="version-tags">
                <van-tag plain>当前 v{{ m.version }}</van-tag
                ><van-tag v-if="m.publication" plain
                  >群快照 v{{ m.publication.version }}</van-tag
                >
              </div>
              <div v-if="own" class="mobile-action-row">
                <van-button plain @click="edit = true">主动更正</van-button
                ><van-button plain @click="share = true">共享查看权</van-button>
              </div></template
            ><van-empty
              v-else
              description="纪要正在自动整理，可先查看已完成的资料"
          /></template>
          <template v-if="tab === 'transcript'"
            ><h2>逐字稿</h2>
            <p class="small muted">AI转写合成样例 · 可追溯到原始片段</p>
            <van-notice-bar
              v-if="transcriptError"
              :text="transcriptError"
              wrapable
            /><van-empty v-if="m.progress < 2" description="逐字稿尚未生成" />
            <div
              v-else
              v-for="s in segments"
              :key="s.id"
              class="transcript-segment"
            >
              <span class="mono small">{{ s.time }} · {{ s.speaker }}</span>
              <p>{{ s.text }}</p>
            </div></template
          >
          <template v-if="tab === 'tasks'"
            ><h2>行动事项</h2>
            <van-empty
              v-if="m.progress < 3"
              description="事项正在自动整理"
            /><template v-else
              ><article
                v-for="task in m.tasks"
                :key="task.id"
                class="task-card"
              >
                <h3>{{ task.text }}</h3>
                <p>
                  {{ task.owner || "负责人未明确" }} ·
                  {{ task.due || "期限未明确" }}
                </p>
                <span class="small muted"
                  >依据 {{ task.evidence }} · 仅内容整理，不自动派单</span
                >
              </article>
              <van-button v-if="own" plain block @click="edit = true"
                >主动更正事项</van-button
              ></template
            ></template
          >
          <template v-if="tab === 'audio'"
            ><h2>原始录音</h2>
            <van-empty
              v-if="m.progress < 1"
              description="等待设备上传，尚未归档"
            /><template v-else
              ><p>{{ duration(m.duration) }} · 原件已归档（模拟）</p>
              <van-empty
                image="search"
                description="合成样例未附真实音频，不能播放"
              />
              <div class="mobile-action-row">
                <van-button disabled block>播放 · 无音频样本</van-button
                ><van-button disabled block>下载 · 需独立授权</van-button>
              </div></template
            ></template
          >
          <template v-if="tab === 'versions'"
            ><h2>内容与发送版本</h2>
            <article
              v-for="v in [...m.versions].reverse()"
              :key="v.version"
              class="version-card"
            >
              <h3>
                v{{ v.version }} ·
                {{ v.version === 1 ? "AI原稿" : "主动更正版" }}
              </h3>
              <p>{{ v.summary }}</p>
              <span class="small muted">{{ v.reason }}</span>
            </article>
            <van-button
              v-if="m.publication"
              plain
              block
              @click="snapshot = true"
              >查看自动发送快照</van-button
            ></template
          >
          <p v-if="m.progress < 4" class="small muted block-gap">
            系统继续推进处理。无法自动恢复的异常由管理员处理，员工无需补操作。
          </p>
        </div>
        <MeetingEditor
          v-model="edit"
          :meeting="m"
          @saved="refresh" /><SharingPanel
          v-model="share"
          :meeting="m"
          @changed="refresh" /><van-popup
          v-model:show="snapshot"
          position="bottom"
          round
          closeable
          class="snapshot-popup"
          ><h2>群消息快照 · 模拟</h2>
          <p class="small muted">
            {{ m.publication?.target }} · v{{ m.publication?.version }}
          </p>
          <p class="meeting-summary">{{ m.publication?.summary }}</p>
          <van-notice-bar
            text="保存更正不改写此快照，也不会重复发群。"
            wrapable /></van-popup
      ></template>
    </div>
    <aside class="employee-explanation">
      <p class="eyebrow">四类资料，各自就绪</p>
      <h2>有依据，<br />也保留不确定。</h2>
      <p class="lead muted">
        随时回到原始资料。更正与共享都是主动选择，不是自动流程的前置步骤。
      </p>
      <p class="small muted">
        数据来自独立的MSW模拟接口；正常/无权/版本冲突使用同一请求层处理。
      </p>
    </aside>
  </section>
</template>
