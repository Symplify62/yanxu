from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: ROOT / ".local-data/server")
    api_key: str = field(default="", repr=False)
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"
    timeout: float = 180
    max_bytes: int = 2 * 1024**3
    chunk_size: int = 1024**2
    max_pending: int = 30
    daily_token_budget: int = 200000
    max_attempts: int = 3
    lease_seconds: int = 180
    retry_seconds: int = 10
    asr_home: Path = field(
        default_factory=lambda: Path.home() / ".local/share/pcim-asr"
    )
    asr_runner: Path = field(default_factory=lambda: ROOT / "backend/local_asr/run.sh")
    frontend_dist: Path = field(default_factory=lambda: ROOT / "frontend/dist")
    storage: str = "local"
    qiniu_access_key: str = field(default="", repr=False)
    qiniu_secret_key: str = field(default="", repr=False)
    qiniu_bucket: str = ""
    qiniu_domain: str = ""
    qiniu_delivery: bool = False
    worker_stage: str = "all"
    worker_token: str = field(default="", repr=False)
    remote_api: str = ""
    min_free_bytes: int = 0

    def __post_init__(self):
        from urllib.parse import urlsplit

        if self.storage not in ("local", "qiniu"):
            raise ValueError("YANXU_STORAGE 必须为 local 或 qiniu")
        if self.storage == "qiniu" and not all(
            (self.qiniu_access_key, self.qiniu_secret_key, self.qiniu_bucket)
        ):
            raise ValueError("七牛上传凭证或空间名称未配置")
        if self.qiniu_domain:
            url = urlsplit(self.qiniu_domain)
            if (
                url.scheme != "https"
                or not url.hostname
                or url.username
                or url.password
                or url.query
                or url.fragment
                or url.path not in ("", "/")
            ):
                raise ValueError("七牛文件域名必须为不含路径的 HTTPS 地址")
        if self.qiniu_delivery and (self.storage != "qiniu" or not self.qiniu_domain):
            raise ValueError("七牛文件分发需要配置存储和 HTTPS 域名")
        if self.worker_stage not in ("all", "analysis"):
            raise ValueError("无效的 worker 阶段")
        if self.remote_api and not self.remote_api.startswith("https://"):
            raise ValueError("远程转写仅允许 HTTPS")

    @property
    def db_path(self):
        return self.data_dir / "yanxu.sqlite3"

    @classmethod
    def load(cls):
        values = {**dotenv_values(ROOT / "config/.env.local"), **os.environ}
        return cls(
            data_dir=Path(values.get("YANXU_DATA_DIR", ROOT / ".local-data/server"))
            .expanduser()
            .resolve(),
            api_key=values.get("DEEPSEEK_API_KEY", "") or "",
            base_url=(
                values.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com") or ""
            ).rstrip("/"),
            model=values.get("DEEPSEEK_MODEL", "deepseek-flash") or "deepseek-flash",
            timeout=float(values.get("DEEPSEEK_TIMEOUT_SECONDS", 180)),
            max_bytes=int(values.get("YANXU_MAX_UPLOAD_BYTES", 2 * 1024**3)),
            daily_token_budget=int(values.get("YANXU_DAILY_TOKEN_BUDGET", 200000)),
            storage=values.get("YANXU_STORAGE", "local"),
            qiniu_access_key=values.get("QINIU_ACCESS_KEY", "") or "",
            qiniu_secret_key=values.get("QINIU_SECRET_KEY", "") or "",
            qiniu_bucket=values.get("QINIU_BUCKET", "") or "",
            qiniu_domain=(values.get("QINIU_PUBLIC_BASE_URL", "") or "").rstrip("/"),
            qiniu_delivery=values.get("QINIU_DELIVERY_ENABLED", "false").lower()
            == "true",
            worker_stage=values.get("YANXU_WORKER_STAGE", "all"),
            worker_token=values.get("YANXU_WORKER_TOKEN", "") or "",
            remote_api=(values.get("YANXU_REMOTE_API", "") or "").rstrip("/"),
            min_free_bytes=int(values.get("YANXU_MIN_FREE_BYTES", 0)),
        )
