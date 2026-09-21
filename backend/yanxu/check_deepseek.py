import json, tempfile
from pathlib import Path
from .config import Settings
from .deepseek import DeepSeek

if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as folder:
        result = DeepSeek(Settings.load()).analyze(
            {
                "segments": [
                    {
                        "id": "seg-00001",
                        "start": 0,
                        "end": 3,
                        "text": "这是连通性测试。决定明天继续讨论，负责人尚未确定。",
                    }
                ]
            },
            "connectivity",
            Path(folder),
        )
        print(
            json.dumps(
                {
                    "status": "ok",
                    "valid_json": True,
                    "summary_present": bool(result["summary"]),
                    "model": Settings.load().model,
                }
            )
        )
