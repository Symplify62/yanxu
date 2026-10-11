<script setup lang="ts">
import { computed, ref, watch } from "vue";
import {
  ArrowDown,
  ArrowUp,
  Archive,
  Clipboard,
  Download,
  FileText,
  RefreshCw,
  RotateCcw,
  Settings2,
  Sparkles,
} from "@lucide/vue";
import {
  briefingSectionOptions,
  defaultBriefingTemplates,
  generatePersonalizedBriefing,
  toMarkdown,
  type ArchivedBriefing,
  type BriefingContext,
  type BriefingSectionId,
  type BriefingTemplate,
  type GeneratedBriefingSection,
} from "./briefing";

const props = defineProps<{
  context: BriefingContext;
  recordId?: string;
  live?: boolean;
  templates?: BriefingTemplate[];
}>();
const context = computed(() => props.context);
const templateList = computed(() =>
  props.templates?.length ? props.templates : defaultBriefingTemplates,
);
const selectedTemplateId = ref(templateList.value[0]?.id || "");
const selectedTemplate = computed(() =>
  templateList.value.find(
    (template) => template.id === selectedTemplateId.value,
  ),
);
const selected = ref<BriefingSectionId[]>(
  templateList.value[0]?.sections ||
    briefingSectionOptions
      .filter((option) => option.defaultSelected)
      .map((option) => option.id),
);
const copyMessage = ref("");
const refreshedAt = ref(Date.now());
const remoteSections = ref<GeneratedBriefingSection[] | null>(null);
const remoteEngine = ref("");
const archivedBriefings = ref<ArchivedBriefing[]>([]);
const archiveListBusy = ref(false);
const busy = ref(false);
const archivedId = ref("");

const localSections = computed(() => {
  refreshedAt.value;
  return generatePersonalizedBriefing(props.context, selected.value);
});
const generated = computed(() => remoteSections.value || localSections.value);
const markdown = computed(
  () => `# ${props.context.title}\n\n${toMarkdown(generated.value)}`,
);
const orderedSelectedOptions = computed(() =>
  selected.value
    .map((id) => briefingSectionOptions.find((option) => option.id === id))
    .filter((option): option is (typeof briefingSectionOptions)[number] =>
      Boolean(option),
    ),
);
const selectedSectionNames = computed(() =>
  orderedSelectedOptions.value.map((option) => option.label),
);
const templateSectionNames = computed(() =>
  selectedTemplate.value
    ? selectedTemplate.value.sections.map(sectionLabel).filter(Boolean)
    : [],
);
const templateAdjusted = computed(() => {
  const template = selectedTemplate.value;
  if (!template) return false;
  return (
    template.sections.length !== selected.value.length ||
    template.sections.some((id, index) => selected.value[index] !== id)
  );
});
const templateStatus = computed(() =>
  templateAdjusted.value ? "已按当前记录调整" : "使用模板默认组合",
);
const activeTemplateName = computed(() => {
  if (!selectedTemplate.value) return "自定义组合";
  return templateAdjusted.value
    ? `${selectedTemplate.value.name}（已调整）`
    : selectedTemplate.value.name;
});

watch(
  templateList,
  (value) => {
    if (!value.length) return;
    const current = value.find(
      (template) => template.id === selectedTemplateId.value,
    );
    if (!current) selectedTemplateId.value = value[0].id;
  },
  { immediate: true },
);

watch(selectedTemplateId, (id) => {
  const template = templateList.value.find((item) => item.id === id);
  if (!template) return;
  selected.value = [...template.sections];
  remoteSections.value = null;
  remoteEngine.value = "";
  archivedId.value = "";
  copyMessage.value = `已应用模板：${template.name}`;
});

watch(
  () => props.recordId,
  () => {
    remoteSections.value = null;
    remoteEngine.value = "";
    archivedId.value = "";
    copyMessage.value = "";
    void loadArchivedBriefings();
  },
  { immediate: true },
);

function toggle(id: BriefingSectionId) {
  copyMessage.value = "";
  clearGeneratedState();
  if (selected.value.includes(id)) {
    if (selected.value.length === 1) return;
    selected.value = selected.value.filter((value) => value !== id);
  } else selected.value = [...selected.value, id];
}

function move(id: BriefingSectionId, delta: -1 | 1) {
  const index = selected.value.indexOf(id);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= selected.value.length) return;
  const next = [...selected.value];
  [next[index], next[target]] = [next[target], next[index]];
  selected.value = next;
  clearGeneratedState();
  copyMessage.value = "";
}

function clearGeneratedState() {
  remoteSections.value = null;
  remoteEngine.value = "";
  archivedId.value = "";
}

function sectionLabel(id: BriefingSectionId) {
  return briefingSectionOptions.find((option) => option.id === id)?.label || id;
}

function resetToTemplate() {
  if (!selectedTemplate.value) return;
  selected.value = [...selectedTemplate.value.sections];
  clearGeneratedState();
  copyMessage.value = `已恢复模板：${selectedTemplate.value.name}`;
}

function selectDefaultSections() {
  selected.value = briefingSectionOptions
    .filter((option) => option.defaultSelected)
    .map((option) => option.id);
  selectedTemplateId.value = "";
  clearGeneratedState();
  copyMessage.value = "已切换为推荐基础组合";
}

function briefingRequestBody() {
  return {
    sections: selected.value,
    context: {
      meetingTime: props.context.meetingTime,
      location: props.context.location,
      weather: props.context.weather,
    },
    templateId: selectedTemplate.value?.id || "",
    templateName: activeTemplateName.value,
    templateDescription: selectedTemplate.value?.description || "",
  };
}

function generatedMessage(action: "预览" | "归档") {
  return remoteEngine.value.startsWith("ai-briefing")
    ? `已由 AI 按当前模板生成${action}`
    : `已由后端按当前板块生成${action}`;
}

function engineLabel(engine: string) {
  return engine.startsWith("ai-briefing") ? "AI 纪要" : "规则纪要";
}

function templateLabel(briefing: ArchivedBriefing) {
  return briefing.context.template?.name || "未记录模板";
}

function sectionLabels(briefing: ArchivedBriefing) {
  return briefing.sections
    .map((section) => {
      const option = briefingSectionOptions.find(
        (item) => item.id === section.id,
      );
      return option?.label || section.title;
    })
    .join(" / ");
}

function safeFilename(value: string) {
  return (
    value
      .trim()
      .replace(/[\\/:*?"<>|]+/g, "-")
      .replace(/\s+/g, "-")
      .slice(0, 80) || "会议纪要"
  );
}

function downloadText(
  content: string,
  filename: string,
  type = "text/markdown",
) {
  const blob = new Blob([content], { type: `${type};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function loadArchivedBriefings() {
  if (!props.live || !props.recordId) {
    archivedBriefings.value = [];
    return;
  }
  archiveListBusy.value = true;
  try {
    const response = await fetch(
      `/api/recordings/${encodeURIComponent(props.recordId)}/briefings`,
    );
    if (!response.ok) throw new Error("briefings");
    const data = await response.json();
    archivedBriefings.value = Array.isArray(data.items) ? data.items : [];
  } catch {
    archivedBriefings.value = [];
  } finally {
    archiveListBusy.value = false;
  }
}

function viewArchived(briefing: ArchivedBriefing) {
  remoteSections.value = briefing.sections;
  remoteEngine.value = briefing.engine;
  archivedId.value = briefing.id;
  selected.value = briefing.sections.map((section) => section.id);
  copyMessage.value = `已打开归档纪要：${new Date(
    briefing.createdAt,
  ).toLocaleString("zh-CN")}`;
}

async function copyArchived(briefing: ArchivedBriefing) {
  try {
    await navigator.clipboard.writeText(briefing.markdown);
    copyMessage.value = "归档纪要 Markdown 已复制";
  } catch {
    copyMessage.value = "复制未完成，请手动选择归档纪要内容。";
  }
}

function exportArchived(briefing: ArchivedBriefing) {
  const createdAt = new Date(briefing.createdAt).toISOString().slice(0, 10);
  downloadText(
    briefing.markdown,
    `${safeFilename(templateLabel(briefing))}-${createdAt}.md`,
  );
  copyMessage.value = "归档纪要 Markdown 已导出";
}

async function regenerate() {
  refreshedAt.value = Date.now();
  remoteSections.value = null;
  remoteEngine.value = "";
  archivedId.value = "";
  if (!props.live || !props.recordId) {
    copyMessage.value = "已按当前板块重新生成";
    return;
  }
  busy.value = true;
  try {
    const response = await fetch(
      `/api/recordings/${encodeURIComponent(props.recordId)}/briefings/preview`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(briefingRequestBody()),
      },
    );
    if (!response.ok) throw new Error("preview");
    const data = await response.json();
    remoteSections.value = data.sections;
    remoteEngine.value = data.engine || "";
    copyMessage.value = generatedMessage("预览");
  } catch {
    copyMessage.value = "后端预览暂不可用，已保留前端演示结果。";
  } finally {
    busy.value = false;
  }
}

async function archiveBriefing() {
  if (!props.live || !props.recordId) {
    archivedId.value = "demo";
    copyMessage.value = "演示归档完成；真实保存将在后端接口中完成。";
    return;
  }
  busy.value = true;
  try {
    const response = await fetch(
      `/api/recordings/${encodeURIComponent(props.recordId)}/briefings`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(briefingRequestBody()),
      },
    );
    if (!response.ok) throw new Error("archive");
    const data = await response.json();
    remoteSections.value = data.sections;
    remoteEngine.value = data.engine || "";
    archivedId.value = data.id;
    copyMessage.value = generatedMessage("归档");
    await loadArchivedBriefings();
  } catch {
    copyMessage.value = "归档暂未完成，请稍后重试。";
  } finally {
    busy.value = false;
  }
}

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(markdown.value);
    copyMessage.value = "纪要 Markdown 已复制";
  } catch {
    copyMessage.value = "复制未完成，请手动选择纪要内容。";
  }
}

function exportMarkdown() {
  downloadText(markdown.value, `${safeFilename(props.context.title)}-纪要.md`);
  copyMessage.value = "当前纪要 Markdown 已导出";
}
</script>

<template>
  <section class="p1-briefing" aria-label="个性化纪要生成">
    <header class="p1-briefing-head">
      <div>
        <p class="p1-content-kicker">个性化纪要</p>
        <h2>选择需要生成的摘要板块</h2>
        <p class="p1-secondary">
          {{
            live
              ? "真实记录会请求后端按当前模板生成；后端配置 DeepSeek 后将使用 AI 分析转写文本。"
              : "当前为前端演示生成：使用模拟逐字稿、会议时间、地点和天气信息，不调用真实录音或 AI 服务。"
          }}
        </p>
      </div>
      <div class="p1-briefing-actions">
        <el-button :loading="busy" @click="regenerate"
          ><RefreshCw :size="15" />预览纪要</el-button
        >
        <el-button :disabled="busy" @click="archiveBriefing"
          ><Archive :size="15" />归档纪要</el-button
        >
        <el-button type="primary" @click="copyMarkdown"
          ><Clipboard :size="15" />复制纪要</el-button
        >
        <el-button @click="exportMarkdown"
          ><Download :size="15" />导出 Markdown</el-button
        >
      </div>
    </header>

    <div class="p1-briefing-layout">
      <aside class="p1-briefing-picker" aria-label="纪要板块选项">
        <div class="p1-briefing-picker-title">
          <Settings2 :size="16" />
          <span>板块选项</span>
        </div>
        <label class="p1-briefing-template-select">
          <span>套用模板</span>
          <el-select v-model="selectedTemplateId" aria-label="选择纪要模板">
            <el-option
              v-for="template in templateList"
              :key="template.id"
              :label="template.name"
              :value="template.id"
            />
          </el-select>
        </label>
        <div class="p1-briefing-template-summary">
          <div class="p1-briefing-template-summary-head">
            <div>
              <strong>{{ selectedTemplate?.name || "自定义组合" }}</strong>
              <span>{{ templateStatus }}</span>
            </div>
            <el-button
              size="small"
              :disabled="!selectedTemplate || !templateAdjusted"
              @click="resetToTemplate"
              ><RotateCcw :size="13" />恢复</el-button
            >
          </div>
          <p>
            {{
              selectedTemplate?.description ||
              "使用当前勾选板块生成一次性的纪要组合。"
            }}
          </p>
          <div
            v-if="templateSectionNames.length"
            class="p1-briefing-template-tags"
          >
            <span v-for="name in templateSectionNames" :key="name">{{
              name
            }}</span>
          </div>
        </div>
        <div class="p1-briefing-current-flow">
          <div>
            <strong>当前生成组合</strong>
            <span>{{ selected.length }} 个板块</span>
          </div>
          <p>{{ selectedSectionNames.join(" → ") }}</p>
          <button type="button" @click="selectDefaultSections">
            恢复推荐基础组合
          </button>
        </div>
        <button
          v-for="option in briefingSectionOptions"
          :key="option.id"
          type="button"
          class="p1-briefing-option"
          :class="{ selected: selected.includes(option.id) }"
          :aria-pressed="selected.includes(option.id)"
          @click="toggle(option.id)"
        >
          <span class="p1-briefing-check">{{
            selected.includes(option.id) ? "✓" : ""
          }}</span>
          <span>
            <strong>{{ option.label }}</strong>
            <small>{{ option.description }}</small>
          </span>
        </button>
        <div class="p1-briefing-order">
          <p>生成顺序</p>
          <div
            v-for="(option, index) in orderedSelectedOptions"
            :key="option.id"
            class="p1-briefing-order-row"
          >
            <span>{{ index + 1 }}. {{ option.label }}</span>
            <span>
              <button
                type="button"
                :disabled="index === 0"
                aria-label="上移板块"
                @click.stop="move(option.id, -1)"
              >
                <ArrowUp :size="13" />
              </button>
              <button
                type="button"
                :disabled="index === orderedSelectedOptions.length - 1"
                aria-label="下移板块"
                @click.stop="move(option.id, 1)"
              >
                <ArrowDown :size="13" />
              </button>
            </span>
          </div>
        </div>
      </aside>

      <main class="p1-briefing-preview">
        <div class="p1-briefing-preview-title">
          <FileText :size="17" />
          <div>
            <strong>{{ context.title }}</strong>
            <span>{{ context.meetingTime }} · {{ context.location }}</span>
          </div>
        </div>
        <article
          v-for="section in generated"
          :key="section.id"
          class="p1-briefing-section"
        >
          <h3><Sparkles :size="15" />{{ section.title }}</h3>
          <ul>
            <li v-for="line in section.lines" :key="line">{{ line }}</li>
          </ul>
        </article>
        <p v-if="archivedId" class="p1-briefing-archived" role="status">
          已归档：{{ archivedId === "demo" ? "演示纪要" : archivedId }}
        </p>
        <p v-if="copyMessage" class="p1-briefing-message" role="status">
          {{ copyMessage }}
        </p>
      </main>
    </div>
    <section v-if="live" class="p1-briefing-archive-list">
      <div class="p1-briefing-archive-head">
        <div>
          <h3>已归档纪要</h3>
          <p>
            {{
              archiveListBusy
                ? "正在读取归档"
                : archivedBriefings.length
                  ? `${archivedBriefings.length} 份历史纪要`
                  : "暂无归档纪要"
            }}
          </p>
        </div>
        <el-button
          size="small"
          :loading="archiveListBusy"
          @click="loadArchivedBriefings"
          >刷新</el-button
        >
      </div>
      <article
        v-for="briefing in archivedBriefings"
        :key="briefing.id"
        class="p1-briefing-archive-card"
      >
        <div>
          <strong>{{ templateLabel(briefing) }}</strong>
          <span>{{
            new Date(briefing.createdAt).toLocaleString("zh-CN")
          }}</span>
        </div>
        <p>{{ sectionLabels(briefing) }}</p>
        <small
          >{{ engineLabel(briefing.engine) }} · {{ briefing.engine }}</small
        >
        <div class="p1-briefing-archive-actions">
          <el-button size="small" @click="viewArchived(briefing)"
            >查看</el-button
          >
          <el-button size="small" @click="copyArchived(briefing)"
            ><Clipboard :size="13" />复制</el-button
          >
          <el-button size="small" @click="exportArchived(briefing)"
            ><Download :size="13" />导出</el-button
          >
        </div>
      </article>
    </section>
  </section>
</template>
