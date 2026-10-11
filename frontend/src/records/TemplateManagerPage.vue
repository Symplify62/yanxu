<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue";
import { Copy, FileText, Plus, RotateCcw, Save, Trash2 } from "@lucide/vue";
import {
  briefingSectionOptions,
  defaultBriefingTemplates,
  normalizeTemplateSections,
  type BriefingSectionId,
  type BriefingTemplate,
} from "./briefing";

const props = defineProps<{ templates: BriefingTemplate[]; live?: boolean }>();
const emit = defineEmits<{ update: [templates: BriefingTemplate[]] }>();

const editingId = ref("");
const message = ref("");
const busy = ref(false);
const form = reactive({
  name: "",
  description: "",
  sections: [] as BriefingSectionId[],
});

const customTemplates = computed(() =>
  props.templates.filter((template) => template.source === "custom"),
);
const selectedOptions = computed(() =>
  form.sections
    .map((id) => briefingSectionOptions.find((option) => option.id === id))
    .filter((option): option is (typeof briefingSectionOptions)[number] =>
      Boolean(option),
    ),
);

watch(
  () => props.templates,
  () => {
    if (!form.sections.length) startNew();
  },
  { immediate: true },
);

function startNew() {
  editingId.value = "";
  form.name = "";
  form.description = "";
  form.sections = ["meta", "summary", "plans", "tasks"];
  message.value = "";
}

function edit(template: BriefingTemplate, duplicate = false) {
  editingId.value =
    duplicate || template.source === "builtin" ? "" : template.id;
  form.name =
    duplicate || template.source === "builtin"
      ? `${template.name} 副本`
      : template.name;
  form.description = template.description;
  form.sections = [...template.sections];
  message.value =
    duplicate || template.source === "builtin" ? "已复制为可编辑草稿" : "";
}

function toggle(id: BriefingSectionId) {
  if (form.sections.includes(id)) {
    if (form.sections.length === 1) return;
    form.sections = form.sections.filter((value) => value !== id);
  } else form.sections = [...form.sections, id];
}

function move(id: BriefingSectionId, delta: -1 | 1) {
  const index = form.sections.indexOf(id);
  const target = index + delta;
  if (index < 0 || target < 0 || target >= form.sections.length) return;
  const next = [...form.sections];
  [next[index], next[target]] = [next[target], next[index]];
  form.sections = next;
}

function normalizeRemoteTemplate(value: unknown): BriefingTemplate | null {
  if (!value || typeof value !== "object") return null;
  const item = value as Record<string, unknown>;
  if (
    typeof item.id !== "string" ||
    typeof item.name !== "string" ||
    !Array.isArray(item.sections)
  )
    return null;
  const sections = normalizeTemplateSections(item.sections);
  if (!sections.length) return null;
  return {
    id: item.id,
    name: item.name,
    description: typeof item.description === "string" ? item.description : "",
    sections,
    source: item.source === "custom" ? "custom" : "builtin",
    createdAt: typeof item.createdAt === "number" ? item.createdAt : undefined,
    updatedAt: typeof item.updatedAt === "number" ? item.updatedAt : undefined,
  };
}

async function syncRemoteTemplates() {
  const response = await fetch("/api/briefing/templates");
  if (!response.ok) throw new Error("templates");
  const data = await response.json();
  const items = Array.isArray(data.items)
    ? data.items
        .map((item: unknown) => normalizeRemoteTemplate(item))
        .filter((item: BriefingTemplate | null): item is BriefingTemplate =>
          Boolean(item),
        )
    : [];
  emit("update", items.length ? items : [...defaultBriefingTemplates]);
}

async function save() {
  const name = form.name.trim();
  const description = form.description.trim();
  const sections = normalizeTemplateSections(form.sections);
  if (!name || !sections.length) {
    message.value = "请填写模板名称，并至少保留一个板块。";
    return;
  }
  if (props.live) {
    busy.value = true;
    try {
      const response = await fetch(
        editingId.value
          ? `/api/briefing/templates/${encodeURIComponent(editingId.value)}`
          : "/api/briefing/templates",
        {
          method: editingId.value ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name, description, sections }),
        },
      );
      if (!response.ok) throw new Error("save");
      const saved = normalizeRemoteTemplate(await response.json());
      await syncRemoteTemplates();
      if (saved) editingId.value = saved.id;
      message.value = "模板已保存到后端";
    } catch {
      message.value = "模板保存失败，请稍后重试。";
    } finally {
      busy.value = false;
    }
    return;
  }
  const now = Date.now();
  const template: BriefingTemplate = {
    id: editingId.value || crypto.randomUUID(),
    name,
    description,
    sections,
    source: "custom",
    createdAt:
      customTemplates.value.find((item) => item.id === editingId.value)
        ?.createdAt || now,
    updatedAt: now,
  };
  const next = [
    ...props.templates.filter(
      (item) => item.source === "builtin" || item.id !== template.id,
    ),
    template,
  ];
  emit("update", next);
  editingId.value = template.id;
  message.value = "模板已保存";
}

async function remove(id: string) {
  if (props.live) {
    busy.value = true;
    try {
      const response = await fetch(
        `/api/briefing/templates/${encodeURIComponent(id)}`,
        { method: "DELETE" },
      );
      if (!response.ok) throw new Error("delete");
      await syncRemoteTemplates();
      if (editingId.value === id) startNew();
      message.value = "模板已删除";
    } catch {
      message.value = "模板删除失败，请稍后重试。";
    } finally {
      busy.value = false;
    }
    return;
  }
  emit(
    "update",
    props.templates.filter((template) => template.id !== id),
  );
  if (editingId.value === id) startNew();
  message.value = "模板已删除";
}

async function resetCustom() {
  if (props.live) {
    busy.value = true;
    try {
      await Promise.all(
        customTemplates.value.map((template) =>
          fetch(`/api/briefing/templates/${encodeURIComponent(template.id)}`, {
            method: "DELETE",
          }).then((response) => {
            if (!response.ok) throw new Error("delete");
          }),
        ),
      );
      await syncRemoteTemplates();
      startNew();
      message.value = "已清空后端自定义模板";
    } catch {
      message.value = "清空失败，请稍后重试。";
    } finally {
      busy.value = false;
    }
    return;
  }
  emit(
    "update",
    props.templates.filter((template) => template.source === "builtin"),
  );
  startNew();
  message.value = "已清空自定义模板";
}
</script>

<template>
  <section class="p1-templates">
    <header class="p1-section-head">
      <div>
        <p class="p1-content-kicker">纪要模板</p>
        <h1>管理可复用的纪要板块组合</h1>
        <p class="p1-secondary">
          {{
            live
              ? "模板会保存到后端，进入任意公共记录详情后都可以直接选择使用。"
              : "模板保存的是板块选择与排列顺序。进入记录详情后，可直接选择模板生成纪要。"
          }}
        </p>
      </div>
      <el-button :disabled="busy" @click="startNew"
        ><Plus :size="15" />新建模板</el-button
      >
    </header>

    <div class="p1-template-grid">
      <main class="p1-template-editor">
        <h2>{{ editingId ? "编辑自定义模板" : "新建自定义模板" }}</h2>
        <label>
          <span>模板名称</span>
          <el-input
            v-model="form.name"
            maxlength="80"
            placeholder="例如：项目例会纪要"
          />
        </label>
        <label>
          <span>说明</span>
          <el-input
            v-model="form.description"
            maxlength="300"
            type="textarea"
            :rows="3"
            placeholder="说明这个模板适用的会议类型"
          />
        </label>

        <div class="p1-template-section-picker">
          <h3>板块选项</h3>
          <button
            v-for="option in briefingSectionOptions"
            :key="option.id"
            type="button"
            :class="{ selected: form.sections.includes(option.id) }"
            @click="toggle(option.id)"
          >
            <strong>{{ option.label }}</strong>
            <small>{{ option.description }}</small>
          </button>
        </div>

        <div class="p1-template-order">
          <h3>生成顺序</h3>
          <article v-for="(option, index) in selectedOptions" :key="option.id">
            <span>{{ index + 1 }}. {{ option.label }}</span>
            <span>
              <el-button
                size="small"
                :disabled="index === 0"
                @click="move(option.id, -1)"
                >上移</el-button
              >
              <el-button
                size="small"
                :disabled="index === selectedOptions.length - 1"
                @click="move(option.id, 1)"
                >下移</el-button
              >
            </span>
          </article>
        </div>

        <div class="p1-template-actions">
          <el-button type="primary" :loading="busy" @click="save"
            ><Save :size="15" />保存模板</el-button
          >
          <el-button :disabled="busy" @click="startNew"
            ><RotateCcw :size="15" />重置表单</el-button
          >
          <p v-if="message" role="status">{{ message }}</p>
        </div>
      </main>

      <aside class="p1-template-list">
        <div class="p1-template-list-head">
          <h2>已有模板</h2>
          <el-button
            size="small"
            :disabled="busy || !customTemplates.length"
            @click="resetCustom"
            >清空自定义</el-button
          >
        </div>
        <article v-for="template in templates" :key="template.id">
          <div>
            <FileText :size="17" />
            <span>{{ template.source === "builtin" ? "内置" : "自定义" }}</span>
          </div>
          <h3>{{ template.name }}</h3>
          <p>{{ template.description || "暂无说明" }}</p>
          <small>{{
            template.sections
              .map(
                (id) =>
                  briefingSectionOptions.find((option) => option.id === id)
                    ?.label,
              )
              .filter(Boolean)
              .join(" / ")
          }}</small>
          <div class="p1-template-card-actions">
            <el-button size="small" :disabled="busy" @click="edit(template)">
              {{ template.source === "builtin" ? "套用" : "编辑" }}
            </el-button>
            <el-button
              size="small"
              :disabled="busy"
              @click="edit(template, true)"
              ><Copy :size="13" />复制</el-button
            >
            <el-button
              v-if="template.source === 'custom'"
              size="small"
              type="danger"
              plain
              :disabled="busy"
              @click="remove(template.id)"
              ><Trash2 :size="13" />删除</el-button
            >
          </div>
        </article>
      </aside>
    </div>
  </section>
</template>
