<script setup lang="ts">
import { computed, ref } from "vue";
import { BookOpen, Clipboard, FileText, UploadCloud } from "@lucide/vue";
import { sampleDocuments, type SampleDocument } from "./sampleDocuments";

const emit = defineEmits<{ open: [id: string]; back: [] }>();

const selectedId = ref(sampleDocuments[0]?.id || "");
const busyId = ref("");
const message = ref("");
const categories = computed(() => [
  "全部",
  ...Array.from(new Set(sampleDocuments.map((sample) => sample.category))),
]);
const activeCategory = ref("全部");
const filteredSamples = computed(() =>
  activeCategory.value === "全部"
    ? sampleDocuments
    : sampleDocuments.filter(
        (sample) => sample.category === activeCategory.value,
      ),
);
const selectedSample = computed(
  () =>
    sampleDocuments.find((sample) => sample.id === selectedId.value) ||
    filteredSamples.value[0] ||
    sampleDocuments[0],
);

function selectCategory(category: string) {
  activeCategory.value = category;
  selectedId.value =
    filteredSamples.value[0]?.id || sampleDocuments[0]?.id || "";
}

async function importSample(sample: SampleDocument) {
  busyId.value = sample.id;
  message.value = "";
  try {
    const response = await fetch("/api/text-recordings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: sample.title,
        text: sample.text,
        sourceName: `${sample.id}.md`,
        context: {
          meetingTime: sample.meetingTime,
          location: sample.location,
          weather: sample.weather,
        },
      }),
    });
    if (!response.ok) throw new Error("import");
    const data = await response.json();
    emit("open", data.id);
  } catch {
    message.value = "样本文档导入失败，请稍后重试。";
  } finally {
    busyId.value = "";
  }
}

async function copySample(sample: SampleDocument) {
  try {
    await navigator.clipboard.writeText(sample.text);
    message.value = "样本文档全文已复制";
  } catch {
    message.value = "复制未完成，请手动选择文本。";
  }
}
</script>

<template>
  <section class="p1-samples">
    <button class="p1-back" @click="$emit('back')">返回公共记录</button>
    <header class="p1-section-head">
      <div>
        <p class="p1-content-kicker">测试样本文档库</p>
        <h1>选择一份文字稿进行 AI 归档测试</h1>
        <p class="p1-secondary">
          样本文档会直接创建为公共记录，用于验证模板、板块组合、AI
          归档和导出流程。
        </p>
      </div>
    </header>

    <div class="p1-sample-categories" aria-label="样本文档分类">
      <button
        v-for="category in categories"
        :key="category"
        type="button"
        :class="{ active: activeCategory === category }"
        @click="selectCategory(category)"
      >
        {{ category }}
      </button>
    </div>

    <main class="p1-sample-grid">
      <aside class="p1-sample-list">
        <button
          v-for="sample in filteredSamples"
          :key="sample.id"
          type="button"
          :class="{ active: selectedSample?.id === sample.id }"
          @click="selectedId = sample.id"
        >
          <span>{{ sample.category }}</span>
          <strong>{{ sample.title }}</strong>
          <small>{{ sample.description }}</small>
        </button>
      </aside>

      <article v-if="selectedSample" class="p1-sample-preview">
        <div class="p1-sample-preview-head">
          <div>
            <p><BookOpen :size="15" />{{ selectedSample.category }}</p>
            <h2>{{ selectedSample.title }}</h2>
            <span
              >{{ selectedSample.meetingTime }} ·
              {{ selectedSample.location }} · {{ selectedSample.weather }}</span
            >
          </div>
          <div class="p1-sample-actions">
            <el-button @click="copySample(selectedSample)"
              ><Clipboard :size="15" />复制全文</el-button
            >
            <el-button
              type="primary"
              :loading="busyId === selectedSample.id"
              @click="importSample(selectedSample)"
              ><UploadCloud :size="15" />导入为记录</el-button
            >
          </div>
        </div>
        <div class="p1-sample-meta">
          <span
            ><FileText :size="14" />推荐模板：{{
              selectedSample.recommendedTemplate
            }}</span
          >
          <span>约 {{ selectedSample.text.length }} 字</span>
        </div>
        <pre>{{ selectedSample.text }}</pre>
        <p v-if="message" class="p1-sample-message" role="status">
          {{ message }}
        </p>
      </article>
    </main>
  </section>
</template>

<style>
.p1-samples {
  max-width: 1180px;
  margin: 0 auto;
}
.p1-sample-categories {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}
.p1-sample-categories button {
  border: 1px solid var(--p1-line);
  border-radius: 999px;
  background: white;
  color: var(--p1-muted);
  padding: 7px 12px;
  font-size: 12px;
}
.p1-sample-categories button.active {
  border-color: var(--p1-accent);
  background: #eef5e8;
  color: var(--p1-accent);
}
.p1-sample-grid {
  display: grid;
  grid-template-columns: 330px minmax(0, 1fr);
  gap: 22px;
}
.p1-sample-list {
  display: grid;
  gap: 10px;
  align-self: start;
}
.p1-sample-list button {
  border: 1px solid var(--p1-line);
  border-radius: 8px;
  background: white;
  text-align: left;
  padding: 14px;
  color: var(--p1-ink);
}
.p1-sample-list button.active {
  border-color: #bfd3b2;
  background: #f6faf2;
}
.p1-sample-list span {
  display: inline-block;
  color: var(--p1-accent);
  font-size: 11px;
  margin-bottom: 7px;
}
.p1-sample-list strong {
  display: block;
  font-size: 14px;
  margin-bottom: 7px;
  overflow-wrap: anywhere;
}
.p1-sample-list small {
  display: block;
  color: var(--p1-muted);
  font-size: 11px;
  line-height: 1.7;
}
.p1-sample-preview {
  border: 1px solid var(--p1-line);
  border-radius: 10px;
  background: white;
  padding: 22px;
  min-width: 0;
}
.p1-sample-preview-head {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--p1-line);
}
.p1-sample-preview-head p {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--p1-accent);
  font-size: 12px;
  margin: 0 0 7px;
}
.p1-sample-preview h2 {
  margin: 0 0 7px;
  font-size: 20px;
}
.p1-sample-preview-head span,
.p1-sample-meta span {
  color: var(--p1-muted);
  font-size: 12px;
}
.p1-sample-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}
.p1-sample-meta {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 13px 0;
}
.p1-sample-meta span:first-child {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--p1-accent);
}
.p1-sample-preview pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  border: 1px solid var(--p1-line);
  border-radius: 8px;
  background: #fbfcf8;
  padding: 16px;
  margin: 0;
  color: #53634e;
  font-family: inherit;
  font-size: 13px;
  line-height: 1.9;
  max-height: 560px;
  overflow: auto;
}
.p1-sample-message {
  margin: 14px 0 0;
  color: var(--p1-accent);
  font-size: 12px;
}
@media (max-width: 860px) {
  .p1-sample-grid {
    grid-template-columns: 1fr;
  }
  .p1-sample-preview-head {
    display: grid;
  }
  .p1-sample-actions {
    justify-content: flex-start;
  }
}
</style>
