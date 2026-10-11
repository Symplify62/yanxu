<script setup lang="ts">
import { reactive, ref } from "vue";
import { FileText, Upload } from "@lucide/vue";

const emit = defineEmits<{ open: [id: string]; back: [] }>();
const busy = ref(false);
const message = ref("");
const form = reactive({
  title: "",
  sourceName: "",
  meetingTime: "",
  location: "",
  weather: "",
  text: "",
});

async function readFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  if (!file) return;
  form.sourceName = file.name;
  if (!form.title) form.title = file.name.replace(/\.(txt|md)$/i, "");
  form.text = await file.text();
}

async function submit() {
  const title = form.title.trim();
  const text = form.text.trim();
  if (!title || !text) {
    message.value = "请填写标题并导入或粘贴文本。";
    return;
  }
  busy.value = true;
  message.value = "";
  try {
    const response = await fetch("/api/text-recordings", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title,
        text,
        sourceName: form.sourceName.trim(),
        context: {
          meetingTime: form.meetingTime.trim(),
          location: form.location.trim(),
          weather: form.weather.trim(),
        },
      }),
    });
    if (!response.ok) throw new Error("import");
    const data = await response.json();
    emit("open", data.id);
  } catch {
    message.value = "文本导入失败，请稍后重试。";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <section class="p1-text-import">
    <button class="p1-back" @click="$emit('back')">返回公共记录</button>
    <header class="p1-section-head">
      <div>
        <p class="p1-content-kicker">文本导入</p>
        <h1>导入已有文字稿</h1>
        <p class="p1-secondary">
          上传或粘贴已经整理好的会议文字，系统会直接创建可生成个性化纪要的公共记录。
        </p>
      </div>
    </header>
    <main class="p1-text-import-grid">
      <section class="p1-text-import-form">
        <label>
          <span>标题</span>
          <el-input
            v-model="form.title"
            maxlength="120"
            placeholder="例如：客户沟通会文字稿"
          />
        </label>
        <div class="p1-text-import-row">
          <label>
            <span>会议时间</span>
            <el-input
              v-model="form.meetingTime"
              placeholder="例如：2026-10-08 15:00"
            />
          </label>
          <label>
            <span>地点</span>
            <el-input v-model="form.location" placeholder="例如：杭州会议室" />
          </label>
          <label>
            <span>天气</span>
            <el-input v-model="form.weather" placeholder="例如：多云，26°C" />
          </label>
        </div>
        <label>
          <span>文字内容</span>
          <el-input
            v-model="form.text"
            type="textarea"
            :rows="16"
            maxlength="200000"
            show-word-limit
            placeholder="粘贴逐字稿、会议记录或纪要草稿。建议每段一行，方便生成带证据的板块。"
          />
        </label>
        <div class="p1-text-import-actions">
          <label class="p1-text-file-button">
            <Upload :size="15" />
            <span>选择 .txt / .md</span>
            <input
              type="file"
              accept=".txt,.md,text/plain,text/markdown"
              @change="readFile"
            />
          </label>
          <el-button type="primary" :loading="busy" @click="submit"
            ><FileText :size="15" />创建记录</el-button
          >
          <p v-if="message" role="alert">{{ message }}</p>
        </div>
      </section>
    </main>
  </section>
</template>
