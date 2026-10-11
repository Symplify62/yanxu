import type { PublicRecord } from "./model";

export type BriefingSectionId =
  | "meta"
  | "summary"
  | "points"
  | "plans"
  | "decisions"
  | "tasks"
  | "risks"
  | "questions"
  | "next"
  | "quotes";

export interface BriefingSectionOption {
  id: BriefingSectionId;
  label: string;
  description: string;
  defaultSelected: boolean;
}

export interface BriefingSegment {
  id: string;
  time: string;
  speaker: string;
  text: string;
}

export interface BriefingTask {
  text: string;
  owner: string | null;
  due: string | null;
  evidence?: string | string[];
}

export interface BriefingAnalysis {
  summary: string;
  points: string[];
  decisions: string[];
  tasks: BriefingTask[];
}

export interface BriefingContext {
  title: string;
  meetingTime: string;
  location: string;
  weather: string;
  duration: string;
  segments: BriefingSegment[];
  analysis?: BriefingAnalysis | null;
}

export interface GeneratedBriefingSection {
  id: BriefingSectionId;
  title: string;
  lines: string[];
  evidence?: string[];
}

export interface ArchivedBriefing {
  id: string;
  recordingId: string;
  createdAt: number;
  sections: GeneratedBriefingSection[];
  context: {
    title?: string;
    meetingTime?: string;
    location?: string;
    weather?: string;
    duration?: string;
    template?: {
      id?: string;
      name?: string;
      description?: string;
      sections?: BriefingSectionId[];
    };
    promptVersion?: string;
  };
  markdown: string;
  engine: string;
}

export interface BriefingTemplate {
  id: string;
  name: string;
  description: string;
  sections: BriefingSectionId[];
  source: "builtin" | "custom";
  createdAt?: number;
  updatedAt?: number;
}

export const briefingSectionOptions: BriefingSectionOption[] = [
  {
    id: "meta",
    label: "基础信息",
    description: "时间、地点、天气与录音时长",
    defaultSelected: true,
  },
  {
    id: "summary",
    label: "会议摘要",
    description: "压缩成一段适合归档的摘要",
    defaultSelected: true,
  },
  {
    id: "plans",
    label: "方案讨论",
    description: "整理方案、路径、优先级和取舍",
    defaultSelected: true,
  },
  {
    id: "tasks",
    label: "待办事项",
    description: "列出任务、负责人、期限和依据",
    defaultSelected: true,
  },
  {
    id: "points",
    label: "讨论重点",
    description: "保留主要讨论点和上下文",
    defaultSelected: false,
  },
  {
    id: "decisions",
    label: "决策记录",
    description: "只记录已明确的决定",
    defaultSelected: false,
  },
  {
    id: "risks",
    label: "风险与阻塞",
    description: "标出依赖、阻碍和验证风险",
    defaultSelected: false,
  },
  {
    id: "questions",
    label: "未解决问题",
    description: "沉淀仍需确认的问题",
    defaultSelected: false,
  },
  {
    id: "next",
    label: "下一步建议",
    description: "给出后续推进建议",
    defaultSelected: false,
  },
  {
    id: "quotes",
    label: "逐字稿摘录",
    description: "引用关键原文片段辅助追溯",
    defaultSelected: false,
  },
];

export const defaultBriefingTemplates: BriefingTemplate[] = [
  {
    id: "builtin-project-weekly",
    name: "项目例会纪要",
    description: "适合周会、项目推进会，突出基础信息、摘要、方案和待办。",
    sections: ["meta", "summary", "plans", "tasks", "next"],
    source: "builtin",
  },
  {
    id: "builtin-solution-review",
    name: "方案评审纪要",
    description: "适合方案评审或技术讨论，突出方案、决策、风险和未解决问题。",
    sections: [
      "meta",
      "summary",
      "plans",
      "decisions",
      "risks",
      "questions",
      "tasks",
    ],
    source: "builtin",
  },
  {
    id: "builtin-customer-visit",
    name: "客户沟通纪要",
    description: "适合拜访、访谈和需求沟通，保留重点、待办和关键原文摘录。",
    sections: ["meta", "summary", "points", "tasks", "quotes"],
    source: "builtin",
  },
];

export function normalizeTemplateSections(
  value: string[],
): BriefingSectionId[] {
  const allowed = new Set(briefingSectionOptions.map((option) => option.id));
  const result = value.filter((id): id is BriefingSectionId =>
    allowed.has(id as BriefingSectionId),
  );
  return [...new Set(result)];
}

export function mockBriefingSegments(record: PublicRecord): BriefingSegment[] {
  const prefix = record.title.includes("流程") ? "流程评审" : "项目例会";
  return [
    {
      id: "seg-demo-001",
      time: "00:08",
      speaker: "主持人",
      text: `${prefix}开始，会议时间按系统记录归档，地点暂定杭州会议室，天气多云，适合按第一阶段模板补齐纪要基础信息。`,
    },
    {
      id: "seg-demo-002",
      time: "00:42",
      speaker: "产品",
      text: "这次希望在公共记录详情里增加个性化纪要模块，让用户选择基础信息、会议摘要、方案讨论和待办事项等板块。",
    },
    {
      id: "seg-demo-003",
      time: "01:18",
      speaker: "技术",
      text: "近期方案可以先在前端用模拟逐字稿生成纪要，暂时不依赖真实录音、天气服务和大模型调用。",
    },
    {
      id: "seg-demo-004",
      time: "02:03",
      speaker: "产品",
      text: "远期需要支持用户自定义板块、用户提示词和输入路径编排，模板还要能归档和复用。",
    },
    {
      id: "seg-demo-005",
      time: "02:46",
      speaker: "主持人",
      text: "决定先完成可视化原型，本周验证交互是否合理；后续再接后端保存、模板版本和真实 AI 生成。",
    },
  ];
}

export function createBriefingContext(params: {
  record: PublicRecord;
  durationLabel: string;
  segments: BriefingSegment[];
  analysis?: BriefingAnalysis | null;
  context?: {
    meetingTime?: string;
    location?: string;
    weather?: string;
  } | null;
}): BriefingContext {
  const hasUsefulContext = params.segments.some((segment) =>
    /天气|地点|方案|待办|模板/.test(segment.text),
  );
  return {
    title: params.record.title,
    meetingTime:
      params.context?.meetingTime ||
      new Date(params.record.createdAt).toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      }),
    location: params.context?.location || "杭州会议室",
    weather: params.context?.weather || "多云，26°C",
    duration: params.durationLabel,
    segments: hasUsefulContext
      ? normalizeSegments(params.segments)
      : mockBriefingSegments(params.record),
    analysis: params.analysis,
  };
}

export function generatePersonalizedBriefing(
  context: BriefingContext,
  selected: BriefingSectionId[],
): GeneratedBriefingSection[] {
  const selectedSet = new Set(selected);
  return briefingSectionOptions
    .filter((option) => selectedSet.has(option.id))
    .map((option) => createSection(option.id, context))
    .filter((section) => section.lines.length > 0);
}

export function toMarkdown(sections: GeneratedBriefingSection[]) {
  return sections
    .map(
      (section) =>
        `## ${section.title}\n${section.lines.map((line) => `- ${line}`).join("\n")}`,
    )
    .join("\n\n");
}

function normalizeSegments(segments: BriefingSegment[]) {
  return segments.map((segment, index) => ({
    id: segment.id || `seg-demo-${String(index + 1).padStart(3, "0")}`,
    time: segment.time,
    speaker: segment.speaker || "发言",
    text: segment.text,
  }));
}

function createSection(
  id: BriefingSectionId,
  context: BriefingContext,
): GeneratedBriefingSection {
  const source = context.segments.map((segment) => segment.text).join(" ");
  const analysis = context.analysis;
  switch (id) {
    case "meta":
      return {
        id,
        title: "基础信息",
        lines: [
          `会议名称：${context.title}`,
          `会议时间：${context.meetingTime}`,
          `会议地点：${context.location}`,
          `天气：${context.weather}`,
          `录音时长：${context.duration}`,
        ],
      };
    case "summary":
      return {
        id,
        title: "会议摘要",
        lines: [
          analysis?.summary ||
            "本次会议围绕公共记录详情页的个性化纪要能力展开，近期先验证板块选择与前端生成体验，后续再接入后端归档、模板版本和真实 AI 生成。",
        ],
      };
    case "points":
      return {
        id,
        title: "讨论重点",
        lines: analysis?.points?.length
          ? analysis.points
          : [
              "公共记录详情页需要新增可选择的纪要板块。",
              "测试阶段使用自动生成的逐字稿与会议信息，不依赖真实录音链路。",
              "后续能力应延展到模板归档、自定义提示词和输入路径编排。",
            ],
      };
    case "plans":
      return {
        id,
        title: "方案讨论",
        lines: [
          "近期方案：先在前端基于模拟逐字稿生成个性化纪要，用于快速验证交互和板块设计。",
          "中期方案：增加后端预览和归档接口，把所选板块、模板版本和生成结果保存为会议纪要快照。",
          "远期方案：支持用户自定义板块、user prompt 和输入路径编排，让不同使用方按自己的纪要格式生成结果。",
          source.includes("天气")
            ? "基础信息中的时间、地点、天气先由测试上下文填充，暂不调用定位和天气服务。"
            : "外部信息板块需要保持可缺省，不能让 AI 编造天气、地点或参会背景。",
        ],
      };
    case "decisions":
      return {
        id,
        title: "决策记录",
        lines: analysis?.decisions?.length
          ? analysis.decisions
          : [
              "先完成详情页内的可视化纪要原型。",
              "第一版暂不接真实录音、天气服务或大模型调用。",
              "交互确认后再设计后端模板、归档和 AI 生成接口。",
            ],
      };
    case "tasks":
      return {
        id,
        title: "待办事项",
        lines: analysis?.tasks?.length
          ? analysis.tasks.map(
              (task) =>
                `${task.text}；负责人：${task.owner || "未明确"}；期限：${task.due || "未明确"}`,
            )
          : [
              "完成个性化纪要前端原型；负责人：开发；期限：本周内。",
              "验证默认板块、勾选组合和复制纪要体验；负责人：产品与开发；期限：下次评审前。",
              "确认后端归档、模板版本和真实 AI 生成的接口范围；负责人：待定；期限：未明确。",
            ],
      };
    case "risks":
      return {
        id,
        title: "风险与阻塞",
        lines: [
          "如果没有结构化模板版本，历史纪要可能会随提示词变化而不可复现。",
          "如果允许用户自由写 prompt，需要限制输出格式并保留证据引用，避免生成不可追溯内容。",
          "天气、地点等外部信息必须来自明确输入或服务接口，不能由 AI 猜测。",
        ],
      };
    case "questions":
      return {
        id,
        title: "未解决问题",
        lines: [
          "第一版是否需要把生成结果保存到本地演示数据中，还是只做即时预览。",
          "模板导入优先支持 Markdown、JSON 还是 Word 文档。",
          "后续用户自定义提示词是否需要管理员审核或版本发布流程。",
        ],
      };
    case "next":
      return {
        id,
        title: "下一步建议",
        lines: [
          "先用前端模拟数据跑通可视化体验，确认板块命名、默认勾选项和展示顺序。",
          "再补后端 preview/archive 接口，保存生成结果和模板版本。",
          "最后接入 DeepSeek，把每个板块拆成结构化 prompt，并对输出做 JSON 校验。",
        ],
      };
    case "quotes":
      return {
        id,
        title: "逐字稿摘录",
        lines: context.segments.slice(0, 4).map((segment) => {
          return `${segment.time} ${segment.speaker}：${segment.text}`;
        }),
      };
  }
}
