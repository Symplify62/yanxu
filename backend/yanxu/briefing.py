import json
from datetime import datetime


SECTION_OPTIONS = [
    {
        "id": "meta",
        "label": "基础信息",
        "description": "时间、地点、天气与录音时长",
        "defaultSelected": True,
    },
    {
        "id": "summary",
        "label": "会议摘要",
        "description": "压缩成一段适合归档的摘要",
        "defaultSelected": True,
    },
    {
        "id": "plans",
        "label": "方案讨论",
        "description": "整理方案、路径、优先级和取舍",
        "defaultSelected": True,
    },
    {
        "id": "tasks",
        "label": "待办事项",
        "description": "列出任务、负责人、期限和依据",
        "defaultSelected": True,
    },
    {
        "id": "points",
        "label": "讨论重点",
        "description": "保留主要讨论点和上下文",
        "defaultSelected": False,
    },
    {
        "id": "decisions",
        "label": "决策记录",
        "description": "只记录已明确的决定",
        "defaultSelected": False,
    },
    {
        "id": "risks",
        "label": "风险与阻塞",
        "description": "标出依赖、阻碍和验证风险",
        "defaultSelected": False,
    },
    {
        "id": "questions",
        "label": "未解决问题",
        "description": "沉淀仍需确认的问题",
        "defaultSelected": False,
    },
    {
        "id": "next",
        "label": "下一步建议",
        "description": "给出后续推进建议",
        "defaultSelected": False,
    },
    {
        "id": "quotes",
        "label": "逐字稿摘录",
        "description": "引用关键原文片段辅助追溯",
        "defaultSelected": False,
    },
]
OPTION_IDS = {option["id"] for option in SECTION_OPTIONS}

DEFAULT_TEMPLATES = [
    {
        "id": "builtin-project-weekly",
        "name": "项目例会纪要",
        "description": "适合周会、项目推进会，突出基础信息、摘要、方案和待办。",
        "sections": ["meta", "summary", "plans", "tasks", "next"],
        "source": "builtin",
    },
    {
        "id": "builtin-solution-review",
        "name": "方案评审纪要",
        "description": "适合方案评审或技术讨论，突出方案、决策、风险和未解决问题。",
        "sections": [
            "meta",
            "summary",
            "plans",
            "decisions",
            "risks",
            "questions",
            "tasks",
        ],
        "source": "builtin",
    },
    {
        "id": "builtin-customer-visit",
        "name": "客户沟通纪要",
        "description": "适合拜访、访谈和需求沟通，保留重点、待办和关键原文摘录。",
        "sections": ["meta", "summary", "points", "tasks", "quotes"],
        "source": "builtin",
    },
]
DEFAULT_TEMPLATE_IDS = {template["id"] for template in DEFAULT_TEMPLATES}


def validate_section_ids(section_ids):
    if (
        not isinstance(section_ids, list)
        or not 1 <= len(section_ids) <= len(SECTION_OPTIONS)
        or len(set(section_ids)) != len(section_ids)
        or any(section_id not in OPTION_IDS for section_id in section_ids)
    ):
        raise ValueError("纪要板块无效")
    return section_ids


def validate_template_payload(value):
    name = value.get("name", "").strip()
    description = value.get("description", "").strip()
    sections = validate_section_ids(value.get("sections"))
    if not 1 <= len(name) <= 80 or len(description) > 300:
        raise ValueError("纪要模板无效")
    return {"name": name, "description": description, "sections": sections}


def build_context(record, override=None, demo_fallback=True):
    override = override or {}
    analysis = json.loads(record["analysis"]) if record.get("analysis") else None
    transcript = json.loads(record["transcript"]) if record.get("transcript") else None
    segments = []
    for index, segment in enumerate((transcript or {}).get("segments", [])):
        text = segment.get("text", "")
        if not isinstance(text, str) or not text.strip():
            continue
        segments.append(
            {
                "id": segment.get("id") or f"seg-demo-{index + 1:03d}",
                "time": _duration(segment.get("start", 0)),
                "speaker": segment.get("speaker") or "发言",
                "text": text,
            }
        )
    if demo_fallback and (
        not segments
        or not any(
            any(
                keyword in segment["text"]
                for keyword in ["天气", "地点", "方案", "待办", "模板"]
            )
            for segment in segments
        )
    ):
        segments = _mock_segments(record)
    return {
        "title": record["title"],
        "meetingTime": _clean(
            override.get("meetingTime"),
            datetime.fromtimestamp(record["created_at"]).strftime("%Y-%m-%d %H:%M"),
        ),
        "location": _clean(override.get("location"), "杭州会议室"),
        "weather": _clean(override.get("weather"), "多云，26°C"),
        "duration": _duration(record.get("duration", 0)),
        "segments": segments,
        "analysis": analysis,
    }


def generate_briefing(record, section_ids, override=None, template=None):
    section_ids = validate_section_ids(section_ids)
    context = build_context(record, override)
    sections = [_section(section_id, context) for section_id in section_ids]
    briefing_context = {
        key: context[key]
        for key in ["title", "meetingTime", "location", "weather", "duration"]
    }
    if template:
        briefing_context["template"] = template
    value = {
        "sections": sections,
        "context": briefing_context,
        "markdown": markdown(context["title"], sections),
        "engine": "deterministic-briefing-v1",
    }
    return value


def markdown(title, sections):
    blocks = [f"# {title}"]
    for section in sections:
        lines = "\n".join(f"- {line}" for line in section["lines"])
        blocks.append(f"## {section['title']}\n{lines}")
    return "\n\n".join(blocks)


def _section(section_id, context):
    source = " ".join(segment["text"] for segment in context["segments"])
    analysis = context.get("analysis")
    if section_id == "meta":
        lines = [
            f"会议名称：{context['title']}",
            f"会议时间：{context['meetingTime']}",
            f"会议地点：{context['location']}",
            f"天气：{context['weather']}",
            f"录音时长：{context['duration']}",
        ]
        title = "基础信息"
    elif section_id == "summary":
        lines = [
            (analysis or {}).get("summary")
            or "本次会议围绕公共记录详情页的个性化纪要能力展开，近期先验证板块选择与前端生成体验，后续再接入后端归档、模板版本和真实 AI 生成。"
        ]
        title = "会议摘要"
    elif section_id == "points":
        lines = (analysis or {}).get("points") or [
            "公共记录详情页需要新增可选择的纪要板块。",
            "测试阶段使用自动生成的逐字稿与会议信息，不依赖真实录音链路。",
            "后续能力应延展到模板归档、自定义提示词和输入路径编排。",
        ]
        title = "讨论重点"
    elif section_id == "plans":
        lines = [
            "近期方案：先在前端基于模拟逐字稿生成个性化纪要，用于快速验证交互和板块设计。",
            "中期方案：增加后端预览和归档接口，把所选板块、模板版本和生成结果保存为会议纪要快照。",
            "远期方案：支持用户自定义板块、user prompt 和输入路径编排，让不同使用方按自己的纪要格式生成结果。",
            "基础信息中的时间、地点、天气先由测试上下文填充，暂不调用定位和天气服务。"
            if "天气" in source
            else "外部信息板块需要保持可缺省，不能让 AI 编造天气、地点或参会背景。",
        ]
        title = "方案讨论"
    elif section_id == "decisions":
        lines = (analysis or {}).get("decisions") or [
            "先完成详情页内的可视化纪要原型。",
            "第一版暂不接真实录音、天气服务或大模型调用。",
            "交互确认后再设计后端模板、归档和 AI 生成接口。",
        ]
        title = "决策记录"
    elif section_id == "tasks":
        tasks = (analysis or {}).get("tasks") or []
        lines = [
            f"{task['text']}；负责人：{task.get('owner') or '未明确'}；期限：{task.get('due') or '未明确'}"
            for task in tasks
            if isinstance(task, dict) and task.get("text")
        ] or [
            "完成个性化纪要前端原型；负责人：开发；期限：本周内。",
            "验证默认板块、勾选组合和复制纪要体验；负责人：产品与开发；期限：下次评审前。",
            "确认后端归档、模板版本和真实 AI 生成的接口范围；负责人：待定；期限：未明确。",
        ]
        title = "待办事项"
    elif section_id == "risks":
        lines = [
            "如果没有结构化模板版本，历史纪要可能会随提示词变化而不可复现。",
            "如果允许用户自由写 prompt，需要限制输出格式并保留证据引用，避免生成不可追溯内容。",
            "天气、地点等外部信息必须来自明确输入或服务接口，不能由 AI 猜测。",
        ]
        title = "风险与阻塞"
    elif section_id == "questions":
        lines = [
            "第一版是否需要把生成结果保存到本地演示数据中，还是只做即时预览。",
            "模板导入优先支持 Markdown、JSON 还是 Word 文档。",
            "后续用户自定义提示词是否需要管理员审核或版本发布流程。",
        ]
        title = "未解决问题"
    elif section_id == "next":
        lines = [
            "先用前端模拟数据跑通可视化体验，确认板块命名、默认勾选项和展示顺序。",
            "再补后端 preview/archive 接口，保存生成结果和模板版本。",
            "最后接入 DeepSeek，把每个板块拆成结构化 prompt，并对输出做 JSON 校验。",
        ]
        title = "下一步建议"
    else:
        lines = [
            f"{segment['time']} {segment['speaker']}：{segment['text']}"
            for segment in context["segments"][:4]
        ]
        title = "逐字稿摘录"
    return {"id": section_id, "title": title, "lines": lines}


def _mock_segments(record):
    prefix = "流程评审" if "流程" in record["title"] else "项目例会"
    return [
        {
            "id": "seg-demo-001",
            "time": "00:08",
            "speaker": "主持人",
            "text": f"{prefix}开始，会议时间按系统记录归档，地点暂定杭州会议室，天气多云，适合按第一阶段模板补齐纪要基础信息。",
        },
        {
            "id": "seg-demo-002",
            "time": "00:42",
            "speaker": "产品",
            "text": "这次希望在公共记录详情里增加个性化纪要模块，让用户选择基础信息、会议摘要、方案讨论和待办事项等板块。",
        },
        {
            "id": "seg-demo-003",
            "time": "01:18",
            "speaker": "技术",
            "text": "近期方案可以先在前端用模拟逐字稿生成纪要，暂时不依赖真实录音、天气服务和大模型调用。",
        },
        {
            "id": "seg-demo-004",
            "time": "02:03",
            "speaker": "产品",
            "text": "远期需要支持用户自定义板块、用户提示词和输入路径编排，模板还要能归档和复用。",
        },
    ]


def _duration(seconds):
    seconds = max(0, int(float(seconds or 0)))
    return f"{seconds // 3600:02}:{seconds % 3600 // 60:02}:{seconds % 60:02}"


def _clean(value, fallback):
    if not isinstance(value, str):
        return fallback
    value = value.strip()
    return value[:80] if value else fallback
