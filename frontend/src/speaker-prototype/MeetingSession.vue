<script setup lang="ts">
import { computed, ref } from "vue";
import {
  AudioLines,
  Pause,
  Play,
  Square,
  Check,
  ArrowRight,
  Mic,
  Users,
  LoaderCircle,
} from "@lucide/vue";
import Button from "../design-lab/kits/ElementButton.vue";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import sample from "./assets/sample.wav";
import { clock, voiceReady, type Meeting } from "./model";
const props = defineProps<{
  phase: string;
  meeting: Meeting;
  seconds: number;
}>();
const emit = defineEmits<{ pause: []; resume: []; finish: []; next: [] }>();
const ending = ref(false);
const playingId = ref(-1);
const audio = ref<HTMLAudioElement>();
const resultTab = ref("transcript");
const phrases = [
  "我们先把这周的进展过一下，重点看交付安排。",
  "核心流程已经跑通，剩下的联调计划在周四完成。",
  "我会同步调整页面细节，明天下午给出修改版本。",
  "好的，遇到阻塞及时沟通，我们按这个安排推进。",
];
const rows = computed(() => {
  const people = props.meeting.people;
  return Array.from({ length: Math.max(4, people.length) }, (_, i) => {
    const p = people[i % people.length]!;
    return {
      name: voiceReady(p) ? p.name : `说话人 ${people.indexOf(p) + 1}`,
      known: voiceReady(p),
      text: phrases[i % phrases.length]!,
      at: [12, 38, 62, 94][i % 4]! + Math.floor(i / 4) * 110,
    };
  });
});
async function play(i: number) {
  playingId.value = i;
  if (audio.value) {
    audio.value.currentTime = 0;
    try {
      await audio.value.play();
    } catch {
      playingId.value = -1;
    }
  }
}
</script>
<template>
  <section
    v-if="phase === 'recording' || phase === 'paused'"
    class="meeting-live"
  >
    <div class="live-eyebrow">
      <span :class="['record-dot', { paused: phase === 'paused' }]"></span
      >{{ phase === "paused" ? "已暂停" : "会议录音中" }}
    </div>
    <h1>{{ meeting.title }}</h1>
    <div class="meeting-clock">{{ clock(seconds) }}</div>
    <div
      class="sound-bars meeting-bars"
      :class="{ stopped: phase === 'paused' }"
    >
      <i v-for="n in 41" :key="n" :style="{ '--n': n }"></i>
    </div>
    <p class="quiet-note">
      {{ meeting.people.length }} 人参会 ·
      {{ meeting.people.filter((p) => p.voice).length }} 人已录入声音
    </p>
    <div class="meeting-people">
      <span v-for="p in meeting.people" :key="p.id"
        ><span class="person-avatar small">{{ p.name.slice(-2) }}</span
        >{{ p.name }}</span
      >
    </div>
    <div class="meeting-actions">
      <Button
        secondary
        @click="phase === 'paused' ? emit('resume') : emit('pause')"
        ><Play v-if="phase === 'paused'" :size="18" /><Pause
          v-else
          :size="18"
        />{{ phase === "paused" ? "继续录音" : "暂停" }}</Button
      ><Button @click="ending = true"><Square :size="16" />结束会议</Button>
    </div>
    <p class="simulation-note">录音计时为演示，未采集会议音频。</p>
    <Dialog
      :model-value="ending"
      title="结束本场会议？"
      @update:model-value="ending = false"
    >
      <p>结束后自动生成逐字稿和会议纪要。</p>
      <template #footer
        ><Button secondary @click="ending = false">继续会议</Button
        ><Button
          @click="
            ending = false;
            emit('finish');
          "
          >结束并整理</Button
        ></template
      >
    </Dialog>
  </section>
  <section
    v-else-if="phase === 'processing'"
    class="meeting-processing"
    role="status"
  >
    <LoaderCircle :size="32" class="spin" />
    <h1>正在整理会议</h1>
    <p>转写文字 · 匹配说话人 · 生成纪要</p>
    <small>正在生成演示结果</small>
  </section>
  <section v-else class="meeting-result">
    <div class="result-heading">
      <div>
        <span class="result-status"
          ><Check :size="15" />整理完成 · 示例结果</span
        >
        <h1>{{ meeting.title }}</h1>
        <p>
          <Users :size="15" />{{ meeting.people.length }}
          位参会者<span>•</span>演示逐字稿
        </p>
      </div>
      <Button secondary @click="emit('next')"
        >下一场会议<ArrowRight :size="16"
      /></Button>
    </div>
    <div class="result-tabs" role="tablist" aria-label="会议结果">
      <button
        role="tab"
        :aria-selected="resultTab === 'transcript'"
        @click="resultTab = 'transcript'"
      >
        逐字稿</button
      ><button
        role="tab"
        :aria-selected="resultTab === 'summary'"
        @click="resultTab = 'summary'"
      >
        会议纪要
      </button>
    </div>
    <div v-if="resultTab === 'transcript'" class="transcript-list">
      <article
        v-for="(row, i) in rows"
        :key="i"
        class="transcript-row"
        :class="{ playing: playingId === i }"
      >
        <span class="person-avatar" :class="{ guest: !row.known }">{{
          row.known ? row.name.slice(-2) : "?"
        }}</span>
        <div>
          <div class="transcript-speaker">
            <strong>{{ row.name }}</strong
            ><span>{{ clock(row.at) }}</span
            ><span v-if="!row.known" class="unknown-tag">未匹配姓名</span>
          </div>
          <p>{{ row.text }}</p>
        </div>
        <button
          :aria-label="`回听第${i + 1}段示例`"
          class="play-segment"
          @click="play(i)"
        >
          <AudioLines v-if="playingId === i" :size="17" /><Play
            v-else
            :size="17"
          />
        </button>
      </article>
      <div class="example-audio">
        <Mic :size="14" /><span>内容与时间均为示例，回听播放合成音频。</span
        ><audio
          ref="audio"
          :src="sample"
          @ended="playingId = -1"
          @error="playingId = -1"
        ></audio>
      </div>
    </div>
    <div v-else class="summary-content">
      <h2>本次讨论</h2>
      <p>
        本周工作围绕核心流程联调与页面细节优化展开，计划周四完成联调，并提前同步页面修改版本。
      </p>
      <h2>行动事项</h2>
      <div>
        <Check :size="17" /><span>完成核心流程联调</span
        ><small>负责人未明确 · 周四</small>
      </div>
      <div>
        <Check :size="17" /><span>同步页面修改版本</span
        ><small>负责人未明确 · 明天下午</small>
      </div>
      <p class="quiet-note">示例纪要。发言人不会自动成为任务负责人。</p>
    </div>
  </section>
</template>
