"""Seed completed text-based meeting records for local briefing tests.

This creates public records with small placeholder WAV files, transcripts, and
baseline analysis. It does not call ASR or any AI provider.
"""

import hashlib
import io
import json
import secrets
import time
import wave

from yanxu.config import Settings
from yanxu.store import Store


DOCS = [
    {
        "id": "seed-text-product-review",
        "client_id": "seed-text-product-review-0001",
        "title": "模板化纪要评审会",
        "duration": 1860,
        "segments": [
            ("00:00", "主持人", "今天在杭州会议室评审模板化纪要能力，天气多云，目标是验证已有文字能按自定义板块生成纪要。"),
            ("00:42", "产品", "使用方希望可以选择基础信息、会议摘要、方案讨论、待办事项、风险与阻塞这些板块，并且保存为可复用模板。"),
            ("01:25", "技术", "近期方案是不再等待语音转文字能力，先对已经完成转写的文本调用 AI，按模板输出结构化 JSON。"),
            ("02:10", "产品", "归档结果需要保存模板名称、板块顺序和生成引擎，方便以后追溯当时为什么生成这些内容。"),
            ("03:05", "技术", "主要风险是 AI 输出格式不稳定，所以后端必须校验 JSON、板块顺序和 evidence 证据 ID。"),
            ("04:20", "主持人", "决定本周先完成后端 AI 纪要接口，并用三条测试文档验证预览和归档。"),
        ],
        "analysis": {
            "summary": "会议评审了模板化纪要能力，决定先基于已有转写文本接入 AI，按自定义板块生成结构化纪要并归档。",
            "points": [
                "模板需要支持基础信息、摘要、方案、待办、风险等板块组合。",
                "近期重点是分析已有文本，不处理语音转文字。",
                "归档需要保存模板快照和生成引擎。",
            ],
            "decisions": ["本周先完成后端 AI 纪要接口，并用测试文档验证。"],
            "tasks": [
                {
                    "text": "完成后端 AI 纪要接口",
                    "owner": "技术",
                    "due": "本周",
                    "evidence": ["seg-0006"],
                },
                {
                    "text": "验证预览和归档流程",
                    "owner": "产品与技术",
                    "due": "本周",
                    "evidence": ["seg-0006"],
                },
            ],
        },
    },
    {
        "id": "seed-text-customer-visit",
        "client_id": "seed-text-customer-visit-0001",
        "title": "客户沟通纪要样本文档",
        "duration": 1440,
        "segments": [
            ("00:00", "销售", "今天拜访上海客户，会议地点在客户总部会议室，天气晴，主要讨论会议纪要自动归档需求。"),
            ("00:35", "客户", "我们希望会议结束后能自动形成客户沟通纪要，包括需求背景、关键反馈、待办事项和原文摘录。"),
            ("01:16", "客户", "不同部门关注的格式不同，销售想看客户诉求，实施想看待办，管理层想看风险和下一步建议。"),
            ("02:20", "产品", "可以通过模板管理页预先配置不同部门需要的板块，然后在详情页选择模板生成。"),
            ("03:05", "客户", "后续希望可以导入自己的纪要格式，甚至用一句话描述想要哪些栏目。"),
            ("04:10", "销售", "待办是下周给客户演示一版模板化纪要，并收集他们的格式样例。"),
        ],
        "analysis": {
            "summary": "客户希望会议结束后自动生成可归档的客户沟通纪要，并支持不同部门按模板查看重点。",
            "points": [
                "客户关注需求背景、关键反馈、待办事项和原文摘录。",
                "不同部门需要不同纪要格式。",
                "远期希望通过导入格式或自然语言描述创建栏目。",
            ],
            "decisions": ["下周给客户演示一版模板化纪要。"],
            "tasks": [
                {
                    "text": "给客户演示模板化纪要",
                    "owner": "销售",
                    "due": "下周",
                    "evidence": ["seg-0006"],
                },
                {
                    "text": "收集客户纪要格式样例",
                    "owner": "销售",
                    "due": "下周",
                    "evidence": ["seg-0006"],
                },
            ],
        },
    },
    {
        "id": "seed-text-risk-retro",
        "client_id": "seed-text-risk-retro-0001",
        "title": "上线复盘与风险梳理",
        "duration": 1680,
        "segments": [
            ("00:00", "主持人", "本次复盘在远程会议进行，会议时间按系统记录，天气信息由用户后续填写。"),
            ("00:28", "运维", "上线过程中最大阻塞是后端服务没有重启，导致新接口代码没有被加载。"),
            ("01:10", "开发", "另一个问题是本地没有测试数据，公共记录页面显示暂无记录，用户无法验证详情页能力。"),
            ("01:48", "测试", "建议提供一个种子脚本，直接生成已完成的文字记录，避免每次都依赖真实录音链路。"),
            ("02:34", "产品", "归档纪要需要清楚标记是 AI 生成还是规则回退，避免误以为所有内容都来自真实 AI。"),
            ("03:30", "主持人", "决定补充测试数据脚本，并把是否配置 DeepSeek 显示在测试说明里。"),
        ],
        "analysis": {
            "summary": "复盘指出当前验证受阻于服务未重启和缺少测试数据，决定补充种子脚本并明确 AI 配置状态。",
            "points": [
                "后端服务未重启会导致新代码未加载。",
                "缺少公共记录会让页面显示暂无记录。",
                "测试数据脚本可以绕开真实录音链路。",
            ],
            "decisions": ["补充测试数据脚本，并在说明中标记 DeepSeek 配置状态。"],
            "tasks": [
                {
                    "text": "补充种子数据脚本",
                    "owner": "开发",
                    "due": "今天",
                    "evidence": ["seg-0006"],
                },
                {
                    "text": "说明 AI 配置与规则回退的区别",
                    "owner": "开发",
                    "due": "今天",
                    "evidence": ["seg-0005", "seg-0006"],
                },
            ],
        },
    },
]


def wav_bytes(seconds=1):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(b"\x00\x00" * 16000 * seconds)
    return buffer.getvalue()


def seconds(value):
    minute, second = value.split(":")[-2:]
    return int(minute) * 60 + int(second)


def transcript(doc):
    segments = []
    for index, (time_label, speaker, text) in enumerate(doc["segments"], start=1):
        start = seconds(time_label)
        segments.append(
            {
                "id": f"seg-{index:04}",
                "start": start,
                "end": start + max(2, min(20, len(text) // 6)),
                "speaker": speaker,
                "text": text,
            }
        )
    return {
        "text": "\n".join(segment["text"] for segment in segments),
        "segments": segments,
    }


def main():
    cfg = Settings.load()
    store = Store(cfg)
    assets = cfg.data_dir / "assets"
    docs_dir = cfg.data_dir / "seed-documents"
    assets.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    now = time.time()
    raw = wav_bytes()
    sha256 = hashlib.sha256(raw).hexdigest()
    for offset, doc in enumerate(DOCS):
        audio_path = assets / f"{doc['id']}.wav"
        audio_path.write_bytes(raw)
        text_path = docs_dir / f"{doc['id']}.txt"
        text_path.write_text(
            "\n".join(
                f"{time_label} {speaker}：{text}"
                for time_label, speaker, text in doc["segments"]
            ),
            encoding="utf-8",
        )
        with store.connect(True) as db:
            db.execute("DELETE FROM recording_briefings WHERE recording_id=?", (doc["id"],))
            db.execute("DELETE FROM jobs WHERE recording_id=?", (doc["id"],))
            db.execute("DELETE FROM parts WHERE recording_id=?", (doc["id"],))
            db.execute(
                "DELETE FROM recordings WHERE id=? OR client_id=?",
                (doc["id"], doc["client_id"]),
            )
            db.execute(
                """
                INSERT INTO recordings(
                  id,client_id,upload_token,title,total_bytes,sha256,extension,
                  created_at,duration,state,audio_path,media_type,transcript,
                  analysis,error,interrupted
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    doc["id"],
                    doc["client_id"],
                    secrets.token_urlsafe(32),
                    doc["title"],
                    len(raw),
                    sha256,
                    "wav",
                    now - offset * 1800,
                    doc["duration"],
                    "complete",
                    str(audio_path),
                    "audio/wav",
                    json.dumps(transcript(doc), ensure_ascii=False),
                    json.dumps(doc["analysis"], ensure_ascii=False),
                    None,
                    0,
                ),
            )
        print(f"seeded {doc['id']}: {doc['title']}")
    print(f"data_dir={cfg.data_dir}")
    print(f"documents={docs_dir}")


if __name__ == "__main__":
    main()
