<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { api } from "../services/api";
import { sessions, logout } from "../composables/session";
import { usePolling } from "../composables/usePolling";
import { duration } from "../domain/presentation";
import MeetingStatus from "../components/MeetingStatus.vue";
import RequestState from "../components/RequestState.vue";
const router = useRouter(),
  filter = ref("all"),
  query = ref(""),
  { data, error, loading, refresh } = usePolling(() =>
    api.meetings.list(query.value),
  );
const records = computed(
  () =>
    data.value?.filter(
      (m) =>
        filter.value === "all" ||
        (filter.value === "mine" && m.owner === sessions.employee?.id) ||
        (filter.value === "shared" && m.owner !== sessions.employee?.id),
    ) ?? [],
);
async function signOut() {
  await logout("employee");
  await router.replace("/employee/login");
}
</script>
<template>
  <section class="employee-layout">
    <div class="mobile-surface">
      <van-nav-bar title="我的会议" right-text="退出" @click-right="signOut" />
      <div class="mobile-welcome">
        <p class="eyebrow">{{ sessions.employee?.name }}</p>
        <h1>会议资料</h1>
        <p class="muted small">自动整理，按完成进度即时可见。</p>
      </div>
      <van-search
        v-model="query"
        placeholder="搜索有权查看的会议"
        @search="refresh"
        @clear="refresh"
      /><van-tabs v-model:active="filter" shrink
        ><van-tab title="全部" name="all" /><van-tab
          title="我发起的"
          name="mine" /><van-tab title="分享给我" name="shared" /></van-tabs
      ><RequestState
        v-if="loading || error || !records.length"
        :loading="loading"
        :error="error"
        :empty="!records.length"
        mobile
        message="暂无可查看的会议"
        @retry="refresh"
      />
      <div v-else class="meeting-list">
        <button
          v-for="m in records"
          :key="m.id"
          class="meeting-list-item"
          @click="router.push('/employee/meetings/' + m.id)"
        >
          <div class="meeting-list-heading">
            <h3>{{ m.title }}</h3>
            <van-icon name="arrow" />
          </div>
          <p class="small muted">
            {{ m.owner === sessions.employee?.id ? "我发起" : "只读共享" }} ·
            {{ duration(m.duration) }}
          </p>
          <MeetingStatus :state="m.state" :manual="m.resolvedManually" mobile />
        </button>
      </div>
    </div>
    <aside class="employee-explanation">
      <p class="eyebrow">录完就走</p>
      <h2>资料陆续生成，<br />无需等待核对。</h2>
      <p class="muted lead">
        原录音、逐字稿、纪要、行动事项完成哪一项，就可以查看哪一项。
      </p>
      <p class="small muted">
        手机端使用 Vant
        组件。当前所有记录为合成样例；查看范围由模拟接口统一判断。
      </p>
    </aside>
  </section>
</template>
