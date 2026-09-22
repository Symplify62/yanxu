<script setup lang="ts">
import { computed, ref } from "vue";
import {
  Mic,
  Plus,
  Pause,
  Play,
  Square,
  ChevronRight,
  AudioLines,
  Check,
  Settings2,
} from "@lucide/vue";
import { ElInput } from "element-plus";
import PersonTile from "./PersonTile.vue";
import PeopleSelectionControl from "./PeopleSelectionControl.vue";
import Dialog from "../design-lab/kits/ElementDialog.vue";
import Button from "../design-lab/kits/ElementButton.vue";
import { clock, type PrototypeModel } from "./model";
const props = defineProps<{ model: PrototypeModel }>();
const emit = defineEmits<{
  picker: [];
  enroll: [id: string];
  start: [];
  finish: [];
  settings: [];
}>();
const { phase, title, seconds, selected, pending, available, activeMeeting } =
  props.model;
const live = computed(
  () => phase.value === "recording" || phase.value === "paused",
);
const choices = computed(() =>
  live.value ? selected.value : available.value.slice(0, 7),
);
const ending = ref(false);
</script>
<template>
  <main class="recorder-page">
    <div class="record-heading">
      <div>
        <span class="section-eyebrow">言序 / 录音</span>
        <h1>会议录音</h1>
      </div>
      <button class="text-action" @click="emit('settings')">
        <Settings2 :size="16" />录音设置
      </button>
    </div>
    <section class="record-canvas" aria-label="录音控制">
      <div class="canvas-title">
        <span class="canvas-state" :class="{ running: phase === 'recording' }"
          ><i></i
          >{{
            phase === "recording"
              ? "正在录音"
              : phase === "paused"
                ? "已暂停"
                : "准备就绪"
          }}</span
        ><ElInput
          v-if="!live"
          v-model="title"
          aria-label="会议名称"
          maxlength="60"
          placeholder="会议名称"
          class="meeting-title-input"
        /><span v-else class="running-title">{{ activeMeeting?.title }}</span>
      </div>
      <div class="recorder-clock">{{ clock(seconds) }}</div>
      <div
        class="recorder-wave"
        :class="{ moving: phase === 'recording' }"
        aria-hidden="true"
      >
        <i
          v-for="n in 49"
          :key="n"
          :style="{ '--bar': ((n * 13) % 29) + 5, '--n': n }"
        ></i>
      </div>
      <div class="record-button-area">
        <template v-if="!live"
          ><button
            class="record-primary"
            :disabled="!selected.length || !model.can('record')"
            aria-label="开始录音"
            @click="emit('start')"
          >
            <Mic :size="28" /></button
          ><strong>开始录音</strong
          ><small>{{
            !model.can("record")
              ? "当前身份没有发起会议权限"
              : selected.length
                ? `${selected.length} 人已加入本场`
                : "点选下方头像，加入参会者"
          }}</small></template
        >
        <template v-else
          ><div class="live-controls">
            <button
              class="control-secondary"
              :aria-label="phase === 'paused' ? '继续录音' : '暂停录音'"
              @click="phase = phase === 'paused' ? 'recording' : 'paused'"
            >
              <Play v-if="phase === 'paused'" :size="23" /><Pause
                v-else
                :size="23"
              /></button
            ><button
              class="record-primary finish"
              aria-label="结束录音"
              @click="ending = true"
            >
              <Square :size="22" />
            </button>
          </div>
          <small>结束后自动整理</small></template
        >
      </div>
      <div class="canvas-foot">
        <span
          ><Mic :size="13" />{{
            model.state.value.preferences.microphone
          }}</span
        ><span>录音演示 · 未开启麦克风</span>
      </div>
    </section>
    <section class="participants-section" aria-label="常用参会者">
      <div class="participants-title">
        <h2>
          {{ live ? "本场参会者" : "谁在现场"
          }}<span>{{ selected.length }} 人</span>
        </h2>
        <div class="participants-actions">
          <PeopleSelectionControl
            :model="model"
            :people="choices"
            scope="current"
          />
          <button class="text-action" @click="emit('picker')">
            {{ live ? "添加参会者" : "按部门选人" }}<ChevronRight :size="15" />
          </button>
        </div>
      </div>
      <div class="avatar-options">
        <PersonTile
          v-for="person in choices"
          :key="person.id"
          :person="person"
          :selected="model.selectedIds.value.includes(person.id)"
          :locked="live || !model.can('record')"
          :voice-blocked="model.voiceEnrollmentBlock(person)"
          @toggle="model.toggle(person.id)"
          @enroll="emit('enroll', person.id)"
        /><button
          class="add-person-tile"
          :disabled="!model.can('record')"
          @click="emit('picker')"
        >
          <span><Plus :size="25" /></span
          ><strong>{{ live ? "添加" : "更多人员" }}</strong
          ><small>{{ live ? "加入本场" : "搜索 / 来宾" }}</small>
        </button>
      </div>
      <div v-if="pending.length && !live" class="pending-voices">
        <AudioLines :size="16" /><span>待录入声音</span
        ><button
          v-for="person in pending"
          :key="person.id"
          @click="emit('enroll', person.id)"
        >
          {{ person.name }}<ChevronRight :size="13" />
        </button>
      </div>
      <p v-else-if="selected.length && !live" class="ready-note">
        <Check :size="14" />本场声音档案已就绪
      </p>
    </section>
    <Dialog
      :model-value="ending"
      title="结束本场录音？"
      @update:model-value="ending = false"
      ><p>录音结束后自动生成逐字稿和会议纪要。</p>
      <template #footer
        ><Button secondary @click="ending = false">继续会议</Button
        ><Button
          @click="
            ending = false;
            emit('finish');
          "
          >结束并整理</Button
        ></template
      ></Dialog
    >
  </main>
</template>
