import json
from types import SimpleNamespace

import httpx

from yanxu.briefing import SECTION_OPTIONS
from yanxu.briefing_ai import BriefingAI


def test_selection_and_template_reuse_all_sections(tmp_path, monkeypatch):
    calls = []

    def post(_client, _url, **kwargs):
        payload = json.loads(kwargs["json"]["messages"][1]["content"])
        calls.append(payload)
        sections = [
            {"id": item["id"], "title": item["title"], "lines": ["Meeting fact"], "evidence": ["s1"]}
            for item in payload["requested_sections"]
        ]
        return httpx.Response(200, json={"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"sections": sections})}}]})

    monkeypatch.setattr(httpx.Client, "post", post)
    cfg = SimpleNamespace(data_dir=tmp_path, api_key="test", base_url="https://example.test", model="test", timeout=5)
    record = {"id": "record-1", "title": "Test", "created_at": 1, "transcript": {"segments": [{"id": "s1", "text": "Meeting fact", "start": 0, "end": 2}]}, "analysis": None}
    record["transcript"] = json.dumps(record["transcript"])
    first = BriefingAI(cfg).generate(record, ["summary"], template={"name": "First"})
    second = BriefingAI(cfg).generate(record, ["risks", "summary"], template={"name": "Other"})
    assert len(calls) == 1
    assert {item["id"] for item in calls[0]["requested_sections"]} == {item["id"] for item in SECTION_OPTIONS if item["id"] != "meta"}
    assert [item["id"] for item in first["sections"]] == ["summary"]
    assert [item["id"] for item in second["sections"]] == ["risks", "summary"]
    assert second["context"]["template"]["name"] == "Other"
    record["transcript"] = record["transcript"].replace("Meeting fact", "Updated fact")
    BriefingAI(cfg).generate(record, ["summary"])
    assert len(calls) == 2
