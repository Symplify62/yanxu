<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from "vue";
const props = defineProps<{ confirmed?: boolean }>();
const requestedSurface =
  new URLSearchParams(location.search).get("surface") || "tablet";
const startSurface = ["tablet", "employee", "admin", "components"].includes(
  requestedSurface,
)
  ? requestedSurface
  : "tablet";
const options = [
  {
    id: "element",
    letter: "A",
    name: "温润 · Element Plus",
    note: "柔和的绿与暖白，更亲近会议室场景。保留当前组件，重新组织空间与层次。",
  },
  {
    id: "shadcn",
    letter: "B",
    name: "克制 · shadcn/vue",
    note: "黑白、细线与留白，让内容成为主角。使用官方组件源码，拥有更自由的定制空间。",
  },
];
const variant = ref("element"),
  frame = ref<HTMLIFrameElement>(),
  ready = ref(false),
  phase = ref("scan"),
  width = ref("wide"),
  surface = ref(startSurface),
  initialSurface = ref(startSurface),
  scenario = ref("normal");
const selected = computed(() => options.find((x) => x.id === variant.value)!);
function select(id: string) {
  if (props.confirmed || id === variant.value) return;
  initialSurface.value = surface.value;
  variant.value = id;
  ready.value = false;
  phase.value = "scan";
  scenario.value = "normal";
}
function send(action: string) {
  frame.value?.contentWindow?.postMessage(
    {
      type: "yanxu-design",
      action: action === "reset" ? "full-reset" : action,
    },
    location.origin,
  );
}
function navigate(value: string) {
  if (value === surface.value && ready.value) return;
  surface.value = value;
  ready.value = false;
  frame.value?.contentWindow?.postMessage(
    { type: "yanxu-design", action: "navigate", surface: value },
    location.origin,
  );
}
function setScenario() {
  frame.value?.contentWindow?.postMessage(
    { type: "yanxu-design", action: "scenario", value: scenario.value },
    location.origin,
  );
}
function message(e: MessageEvent) {
  if (e.origin !== location.origin || e.source !== frame.value?.contentWindow)
    return;
  if (e.data?.type === "yanxu-full-ready") {
    if (e.data.surface !== surface.value) navigate(surface.value);
    else if (surface.value !== "tablet") ready.value = true;
  }
  if (e.data?.type === "yanxu-design-state") {
    ready.value = true;
    phase.value = e.data.phase;
  }
}
onMounted(() => window.addEventListener("message", message));
onUnmounted(() => window.removeEventListener("message", message));
</script>
<template>
  <div class="lab">
    <header class="lab-header">
      <div>
        <a
          :href="confirmed ? '/design-lab.html' : '/prototype.html'"
          class="back"
          >{{ confirmed ? "查看历史方案对比" : "← 打开已确认的 A 原型" }}</a
        >
        <h1>
          {{
            confirmed ? "言序 · 正式组件原型" : "从录音到查阅，两套完整体验。"
          }}
        </h1>
        <p>
          {{
            confirmed
              ? "已确认采用 A · 温润 / Element Plus，覆盖平板、员工手机和管理后台。"
              : "A 方案已确认。此页保留 A / B 的历史对比。"
          }}
        </p>
      </div>
      <span class="lab-label">{{
        confirmed ? "言序 / A · 已确认" : "言序 / DESIGN STUDY 02"
      }}</span>
    </header>
    <div
      v-if="!confirmed"
      class="option-tabs"
      role="tablist"
      aria-label="选择设计方向"
    >
      <button
        v-for="o in options"
        :key="o.id"
        role="tab"
        :aria-selected="variant === o.id"
        :class="{ active: variant === o.id }"
        @click="select(o.id)"
      >
        <span>{{ o.letter }}</span
        >{{ o.name }}
      </button>
    </div>
    <div class="lab-description">
      <p>{{ selected.note }}</p>
      <div
        v-if="surface !== 'employee'"
        class="viewport-controls"
        aria-label="预览尺寸"
      >
        <button :aria-pressed="width === 'wide'" @click="width = 'wide'">
          横屏</button
        ><button :aria-pressed="width === 'tablet'" @click="width = 'tablet'">
          竖屏
        </button>
      </div>
    </div>
    <nav class="surface-picker" aria-label="切换业务端">
      <button
        v-for="item in [
          ['tablet', '平板录音端'],
          ['employee', '员工手机端'],
          ['admin', '管理后台'],
          ['components', '组件与状态'],
        ]"
        :key="item[0]"
        :class="{ active: surface === item[0] }"
        :disabled="!ready"
        @click="navigate(item[0]!)"
      >
        {{ item[1] }}
      </button>
    </nav>
    <div class="demo-bar">
      <span><i></i>演示控制 · 不属于正式产品</span>
      <div>
        <button
          v-if="surface === 'tablet'"
          :disabled="!ready || phase !== 'scan'"
          @click="send('scan')"
        >
          模拟扫码登录</button
        ><button
          v-if="surface === 'tablet'"
          :disabled="!ready || phase !== 'scan'"
          @click="send('expire')"
        >
          模拟码过期</button
        ><select v-model="scenario" aria-label="演示场景" @change="setScenario">
          <option value="normal">正常自动流程</option>
          <option value="offline">设备断网</option>
          <option value="save-failure">本地保存失败</option>
          <option value="ai-failure">AI 重试耗尽</option>
          <option value="missing-route">接收群未配置</option>
          <option value="unknown">发送结果不明</option></select
        ><button
          :disabled="!ready"
          @click="
            send('reset');
            scenario = 'normal';
          "
        >
          重新体验
        </button>
      </div>
    </div>
    <div class="preview-area">
      <iframe
        :key="variant"
        ref="frame"
        :src="
          '/design-option.html?variant=' +
          variant +
          '&surface=' +
          initialSurface
        "
        :class="[width, { phone: surface === 'employee' }]"
        :title="selected.name + '完整原型'"
      ></iframe>
    </div>
    <footer class="lab-footer">
      <span>{{
        confirmed
          ? "切换业务端保留演示资料；重新体验将重置本次模拟数据。"
          : "同一方案切换端保留演示资料；切换 A/B 会重新开始该方案数据。"
      }}</span
      ><span>模拟数据 · 不采音、不连接企业微信、不发真实消息</span>
    </footer>
  </div>
</template>
<style>
* {
  box-sizing: border-box;
}
body {
  margin: 0;
  background: #efefed;
  color: #252825;
  font-family:
    Inter,
    -apple-system,
    BlinkMacSystemFont,
    "PingFang SC",
    "Microsoft YaHei",
    sans-serif;
}
.lab {
  max-width: 1500px;
  margin: auto;
  padding: 30px 40px 24px;
}
.lab-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 26px;
}
.back {
  color: #72756f;
  text-decoration: none;
  font-size: 13px;
}
.lab-header h1 {
  font-size: 26px;
  letter-spacing: -0.8px;
  font-weight: 600;
  margin: 16px 0 9px;
}
.lab-header p {
  font-size: 14px;
  color: #6d716d;
  margin: 0;
}
.lab-label {
  font-size: 11px;
  letter-spacing: 2px;
  color: #777d76;
}
.option-tabs {
  display: flex;
  border-bottom: 1px solid #d4d7d1;
  gap: 30px;
}
.option-tabs button {
  border: 0;
  background: none;
  padding: 0 0 16px;
  color: #757a73;
  font-size: 15px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.option-tabs button span {
  font:
    12px ui-monospace,
    monospace;
  background: #e2e4df;
  border-radius: 5px;
  padding: 4px 7px;
}
.option-tabs button.active {
  color: #202a22;
  border-color: #354d3b;
  font-weight: 600;
}
.option-tabs button.active span {
  background: #354d3b;
  color: white;
}
.lab-description {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  min-height: 67px;
}
.lab-description p {
  font-size: 13px;
  color: #6e746e;
  line-height: 1.7;
}
.viewport-controls {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}
.viewport-controls button {
  border: 1px solid transparent;
  background: none;
  color: #72766f;
  padding: 6px 10px;
  border-radius: 5px;
  cursor: pointer;
}
.viewport-controls [aria-pressed="true"] {
  background: white;
  border-color: #d6d9d2;
  color: #30362e;
}
.demo-bar {
  background: #e3e6e0;
  border: 1px solid #d7dbd3;
  border-radius: 10px 10px 0 0;
  padding: 10px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #646c61;
  gap: 10px;
}
.demo-bar span {
  display: flex;
  align-items: center;
  gap: 7px;
}
.demo-bar i {
  width: 5px;
  height: 5px;
  background: #869181;
  border-radius: 50%;
}
.demo-bar > div {
  display: flex;
  gap: 8px;
}
.demo-bar button {
  padding: 7px 11px;
  background: #f7f8f5;
  border: 1px solid #ccd1c7;
  border-radius: 5px;
  color: #3d4938;
  cursor: pointer;
  font-size: 12px;
}
.demo-bar button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.preview-area {
  background: #dadfd7;
  padding: 0;
  display: flex;
  justify-content: center;
  overflow: hidden;
  border: 1px solid #d7dbd3;
  border-top: 0;
  border-radius: 0 0 10px 10px;
}
iframe {
  display: block;
  border: 0;
  width: 100%;
  height: 710px;
  background: white;
  transition: width 0.2s;
}
iframe.tablet {
  width: 768px;
  height: 960px;
}
.lab-footer {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  color: #7d8479;
  font-size: 11px;
  margin-top: 16px;
  line-height: 1.8;
}
button:focus-visible,
a:focus-visible {
  outline: 2px solid #536d4e;
  outline-offset: 4px;
}
@media (max-width: 800px) {
  .lab {
    padding: 20px 14px;
  }
  .lab-label {
    display: none;
  }
  .lab-header h1 {
    font-size: 22px;
  }
  .option-tabs {
    gap: 14px;
  }
  .option-tabs button {
    font-size: 12px;
    gap: 6px;
  }
  .lab-description {
    gap: 8px;
  }
  .demo-bar {
    align-items: flex-start;
    flex-direction: column;
  }
  .lab-footer {
    flex-direction: column;
    gap: 2px;
  }
  iframe {
    height: 860px;
  }
}
.surface-picker {
  display: flex;
  gap: 5px;
  margin: 0 0 16px;
  background: #e2e5de;
  padding: 5px;
  border-radius: 8px;
  width: fit-content;
}
.surface-picker button {
  border: 0;
  background: none;
  border-radius: 5px;
  color: #6a7165;
  padding: 9px 18px;
  cursor: pointer;
  font-size: 13px;
}
.surface-picker button.active {
  background: #fff;
  color: #273b28;
  box-shadow: 0 1px 4px #0000000b;
}
.demo-bar select {
  padding: 5px 8px;
  border: 1px solid #ccd1c7;
  background: #f7f8f5;
  border-radius: 5px;
  color: #3d4938;
  font-size: 12px;
  max-width: 160px;
}
iframe.phone {
  width: 430px;
  height: 870px;
}
.preview-area:has(iframe.phone) {
  padding: 24px;
}
.demo-bar > div {
  flex-wrap: wrap;
}
@media (max-width: 600px) {
  .surface-picker {
    width: 100%;
    gap: 0;
  }
  .surface-picker button {
    padding: 8px;
    font-size: 11px;
    flex: 1;
  }
  .preview-area:has(iframe.phone) {
    padding: 0;
  }
}
</style>
