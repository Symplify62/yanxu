import os, json, subprocess, wave
from pathlib import Path
from .locks import file_lock


def media_env():
    env = os.environ.copy()
    library = Path("/opt/homebrew/Cellar/x265/4.1/lib")
    if (library / "libx265.215.dylib").exists():
        env["DYLD_LIBRARY_PATH"] = str(library)
    return env


def inspect_audio(path, extension=None):
    try:
        p = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_streams",
                "-show_format",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            env=media_env(),
            check=True,
        )
        data = json.loads(p.stdout)
        audio = [s for s in data["streams"] if s["codec_type"] == "audio"]
        if not audio or any(s["codec_type"] == "video" for s in data["streams"]):
            raise ValueError()
        formats = set(data["format"]["format_name"].split(","))
        expected = {
            "wav": {"wav"},
            "mp3": {"mp3"},
            "m4a": {"mov", "mp4", "m4a"},
            "webm": {"webm"},
        }
        if extension and not formats.intersection(expected[extension]):
            raise ValueError()
        duration = float(data["format"]["duration"])
        if not 0 < duration < 365 * 86400:
            raise ValueError()
        return duration
    except (ValueError, KeyError, FileNotFoundError, subprocess.SubprocessError):
        try:
            return inspect_wav(path, extension)
        except ValueError:
            pass
        raise ValueError("音频不可读取，请保留本地文件后重试") from None


def inspect_wav(path, extension=None):
    if extension and extension != "wav":
        raise ValueError()
    try:
        with wave.open(str(path), "rb") as audio:
            frames = audio.getnframes()
            rate = audio.getframerate()
            channels = audio.getnchannels()
            width = audio.getsampwidth()
        duration = frames / rate
        if channels < 1 or width < 1 or not 0 < duration < 365 * 86400:
            raise ValueError()
        return duration
    except (wave.Error, OSError, ZeroDivisionError):
        raise ValueError() from None


def write_json(path, value):
    temp = path.with_suffix(".tmp")
    with temp.open("w", encoding="utf-8") as f:
        f.write(json.dumps(value, ensure_ascii=False))
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)
