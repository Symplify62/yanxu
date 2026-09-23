#!/usr/bin/env python3
"""Install separate Mac launch agents for the public testing environment."""

from pathlib import Path
import os
import plistlib
import subprocess


ROOT = Path(__file__).resolve().parents[1]
SECRET = ROOT / ".local-data/credentials/staging-worker.env"
DATA = ROOT / ".local-data/staging-worker"
AGENTS = Path.home() / "Library/LaunchAgents"
PYTHON = ROOT / "backend/.venv/bin/python"
LABELS = {
    "asr": ("cn.jiajian.yanxu.test-remote-asr", "yanxu.remote_worker"),
    "voice": ("cn.jiajian.yanxu.test-remote-voice", "yanxu.voice.remote_worker"),
}


def main():
    if not SECRET.is_file() or SECRET.stat().st_mode & 0o077:
        raise SystemExit("测试 worker 机密文件必须存在且仅当前用户可读")
    if not PYTHON.is_file():
        raise SystemExit("先安装 backend Python 依赖")
    DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
    AGENTS.mkdir(parents=True, exist_ok=True)
    for kind, (label, module) in LABELS.items():
        path = AGENTS / (label + ".plist")
        if path.exists():
            raise SystemExit(f"{path} 已存在；请先检查后再更新")
        payload = {
            "Label": label,
            "ProgramArguments": [str(PYTHON), "-m", module],
            "WorkingDirectory": str(ROOT / "backend"),
            "EnvironmentVariables": {
                "YANXU_ENVIRONMENT": "testing",
                "YANXU_SECRET_FILE": str(SECRET),
                "PATH": os.environ.get("PATH", "/usr/bin:/bin:/usr/sbin:/sbin"),
            },
            "StandardOutPath": str(DATA / (kind + ".log")),
            "StandardErrorPath": str(DATA / (kind + ".error.log")),
            "RunAtLoad": True,
            "KeepAlive": True,
        }
        with path.open("xb") as output:
            plistlib.dump(payload, output)
        path.chmod(0o600)
        subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(path)], check=True)
        print(label, "installed")


if __name__ == "__main__":
    main()
