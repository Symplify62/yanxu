<script setup lang="ts">
import { AudioLines, ChevronRight, Check, Mic } from "@lucide/vue";
import { ElCheckbox } from "element-plus";
import type { Person } from "./model";
defineProps<{ people: Person[]; selectedIds: string[]; directory?: boolean }>();
defineEmits<{
  toggle: [id: string];
  enroll: [person: Person];
  profile: [person: Person];
}>();
</script>
<template>
  <div class="person-list">
    <article
      v-for="person in people"
      :key="person.id"
      class="person-row"
      :class="{ selected: !directory && selectedIds.includes(person.id) }"
      :data-testid="`person-${person.id}`"
    >
      <ElCheckbox
        v-if="!directory"
        :model-value="selectedIds.includes(person.id)"
        :aria-label="`选择${person.name} ${person.detail}`"
        @change="$emit('toggle', person.id)"
      />
      <button
        class="person-identity"
        :aria-label="`查看${person.name}的档案`"
        @click="$emit('profile', person)"
      >
        <span
          class="person-avatar"
          :class="{ guest: person.scope === 'guest' }"
          >{{ person.name.slice(-2) }}</span
        >
        <span class="person-info"
          ><strong
            >{{ person.name
            }}<span v-if="person.scope === 'guest'" class="guest-label"
              >来宾</span
            ></strong
          ><small>{{ person.detail || "仅本场参会" }}</small></span
        >
      </button>
      <div class="person-voice">
        <button
          v-if="person.voice"
          class="voice-state ready"
          :aria-label="`查看${person.name}的声音档案`"
          @click="$emit('profile', person)"
        >
          <AudioLines :size="15" /><span>声音已录入</span><Check :size="13" />
        </button>
        <button
          v-else
          class="voice-state missing"
          :aria-label="`录入${person.name}的声音`"
          @click="$emit('enroll', person)"
        >
          <Mic :size="15" /><span>录入声音</span><ChevronRight :size="13" />
        </button>
      </div>
    </article>
    <div v-if="!people.length" class="empty-state">
      <strong>没有找到成员</strong>
      <p>换个关键词，或添加新成员。</p>
    </div>
  </div>
</template>
