import fcntl, json, os, subprocess, threading, time, logging
from pathlib import Path
from .config import Settings
from .store import Store
from .deepseek import DeepSeek, ProviderError

logger = logging.getLogger("yanxu.worker")


def transcribe(cfg, row):
    output = cfg.data_dir / "asr" / row["id"]
    output.parent.mkdir(parents=True, exist_ok=True)
    log = output.parent / (row["id"] + ".log")
    with log.open("a") as f:
        result = subprocess.run(
            [
                "bash",
                str(cfg.asr_runner),
                row["audio_path"],
                "--engine",
                "qwen",
                "--max-seconds",
                "60",
                "--output",
                str(output),
            ],
            stdout=f,
            stderr=subprocess.STDOUT,
            env={**os.environ, "LOCAL_ASR_HOME": str(cfg.asr_home)},
            timeout=max(600, row["duration"] * 2),
        )
    if result.returncode:
        raise ProviderError("本地转写未完成，请检查处理日志")
    m = json.loads((output / "manifest.json").read_text())
    raw = json.loads((output / "transcript.raw.json").read_text())
    text = "".join(c["text"] for c in raw["chunks"])
    speech = sum(c["end"] - c["start"] for c in raw["chunks"])
    if m["status"] == "complete_no_speech" and not raw["chunks"] and not raw["cues"]:
        return {"noSpeech": True, "text": "", "segments": [], "engine": "Qwen3-ASR-1.7B"}
    if m["status"] != "complete" or not text.strip():
        raise ProviderError("转写结果不完整，请检查处理日志", False)
    if row["duration"] > 60 and (speech / row["duration"] < 0.03 or len(text) < 20):
        raise ProviderError("有效语音覆盖过低，请检查原始录音", False)
    segments = []
    for cue in raw["cues"]:
        segments.append(
            {
                "id": f"seg-{len(segments) + 1:05d}",
                "start": cue["start"],
                "end": cue["end"],
                "text": cue["text"],
                "speaker": None,
            }
        )
    if not segments:
        raise ProviderError("转写时间信息缺失", False)
    return {
        "text": text,
        "segments": segments,
        "engine": "Qwen3-ASR-1.7B",
        "speechSeconds": speech,
        "warning": "词级时间未经人工核对；未区分说话人",
    }


def process_one(store, asr=transcribe, analyzer=None):
    job = store.claim(
        stage="analysis" if store.settings.worker_stage == "analysis" else None
    )
    if not job:
        return False
    cfg = store.settings
    stop = threading.Event()

    def beat():
        while not stop.wait(max(1, cfg.lease_seconds / 3)):
            try:
                store.heartbeat(job["recording_id"], job["owner"])
            except Exception:
                logger.warning("heartbeat failed for %s", job["recording_id"])

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        row = store.get(job["recording_id"])
        if job["stage"] == "asr":
            value = asr(cfg, row)
        else:
            from .voice import public_transcript
            provider = analyzer or DeepSeek(cfg, store)
            value = provider.analyze(
                public_transcript(json.loads(row["transcript"])),
                row["id"],
                cfg.data_dir / "analysis-cache" / row["id"],
            )
        store.finish(job, value)
        logger.info("completed %s %s", job["recording_id"], job["stage"])
    except ProviderError as e:
        store.fail(job, str(e), e.retryable)
        logger.warning("stage failed %s %s", job["recording_id"], job["stage"])
    except Exception:
        store.fail(job, "处理暂未完成，请检查本地服务日志")
        logger.exception("unexpected stage error %s", job["recording_id"])
    finally:
        stop.set()
        thread.join(timeout=2)
    return True


def main():
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
    )
    cfg = Settings.load()
    store = Store(cfg)
    with (cfg.data_dir / "worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise SystemExit("已有本地worker运行")
        logger.info("worker ready")
        while True:
            if not process_one(store):
                time.sleep(1)


if __name__ == "__main__":
    main()
