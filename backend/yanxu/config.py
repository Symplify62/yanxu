from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: ROOT / ".local-data/server")
    environment: str = "legacy"
    public_origin: str = "https://yanxu.qjl666.xyz"
    android_package_name: str = "cn.jiajian.yanxu"
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
    identity_enabled: bool = True
    session_hours: int = 24
    backup_token: str = field(default="", repr=False)
    voice_worker_token: str = field(default="", repr=False)
    voice_engine_command: str = ""
    voice_model_version: str = "wespeaker-cnceleb-resnet34-lm:e7584940aeac8d55:kaldi80-v1"
    voice_match_threshold: float = 0.75
    voice_match_margin: float = 0.08
    voice_private_bucket: str = ""
    voice_private_domain: str = ""

    def __post_init__(self):
        from urllib.parse import urlsplit

        public = urlsplit(self.public_origin)
        if (public.scheme not in ("https", "http") or not public.hostname
                or public.username or public.password or public.query or public.fragment
                or public.path not in ("", "/")
                or (public.scheme == "http" and public.hostname not in ("127.0.0.1", "localhost"))
                or (self.environment in ("testing", "production") and public.scheme != "https")):
            raise ValueError("环境公网入口必须为无路径的 HTTPS 地址；本机开发可使用回环 HTTP")
        if self.environment not in ("legacy", "development", "testing", "production"):
            raise ValueError("无效的言序环境")
        if self.environment in ("testing", "production") and self.remote_api and self.remote_api != self.public_origin:
            raise ValueError("远程 worker 地址与当前环境不匹配")
        if self.environment == "testing" and self.data_dir.resolve().is_relative_to(Path("/var/lib/yanxu").resolve()):
            raise ValueError("测试数据不能写入生产目录")
        if self.environment == "production" and self.data_dir.resolve().is_relative_to(Path("/var/lib/yanxu-test").resolve()):
            raise ValueError("生产数据不能写入测试目录")
        if not self.android_package_name.startswith("cn.jiajian.yanxu"):
            raise ValueError("Android 包名与环境配置不匹配")

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
        if not 1 <= self.session_hours <= 720:
            raise ValueError("会话有效期须为1至720小时")
        if not 0 <= self.voice_match_threshold <= 1 or not 0 <= self.voice_match_margin <= 1:
            raise ValueError("声音匹配阈值无效")
        secrets_set = [x for x in (self.worker_token, self.backup_token, self.voice_worker_token) if x]
        if len(secrets_set) != len(set(secrets_set)):
            raise ValueError("转写、备份和声音处理必须使用独立凭证")
        if self.voice_private_bucket and (self.voice_private_bucket == self.qiniu_bucket or not self.qiniu_access_key or not self.qiniu_secret_key):
            raise ValueError("声音档案镜像需要独立私有空间和服务端存储凭证")

    @property
    def db_path(self):
        return self.data_dir / "yanxu.sqlite3"

    @classmethod
    def load(cls):
        selected = os.environ.get("YANXU_ENVIRONMENT", "").strip()
        if selected:
            if selected not in ("development", "testing", "production"):
                raise ValueError("YANXU_ENVIRONMENT 只能为 development、testing 或 production")
            profile_path = ROOT / "config/environments" / f"{selected}.env"
            if not profile_path.is_file():
                raise ValueError("环境配置文件不存在")
            profile = dotenv_values(profile_path)
        else:
            selected = "legacy"
            profile = dotenv_values(ROOT / "config/.env.local")
        secret_path = os.environ.get("YANXU_SECRET_FILE", "")
        secrets = {}
        if secret_path:
            path = Path(secret_path)
            if not path.is_absolute() or not path.is_file() or path.is_symlink() or path.stat().st_mode & 0o077:
                raise ValueError("机密配置必须是权限 600 的绝对路径文件")
            secrets = dotenv_values(path)
        values = {**profile, **secrets, **os.environ}
        if selected in ("testing", "production"):
            if profile.get("YANXU_AUDIO_ORIGIN") != profile.get("QINIU_PUBLIC_BASE_URL"):
                raise ValueError("Android 音频域名与当前存储域名不匹配")
            for key in ("YANXU_PUBLIC_ORIGIN", "YANXU_AUDIO_ORIGIN", "QINIU_BUCKET", "QINIU_PUBLIC_BASE_URL", "ANDROID_APPLICATION_ID", "YANXU_REMOTE_API"):
                if values.get(key) != profile.get(key):
                    raise ValueError("运行环境与版本化配置冲突：" + key)
        return cls(
            data_dir=Path(values.get("YANXU_DATA_DIR", ROOT / ".local-data/server"))
            .expanduser()
            .resolve(),
            environment=selected,
            public_origin=(values.get("YANXU_PUBLIC_ORIGIN", "https://yanxu.qjl666.xyz") or "").rstrip("/"),
            android_package_name=values.get("ANDROID_APPLICATION_ID", "cn.jiajian.yanxu"),
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
            identity_enabled=values.get("YANXU_IDENTITY_ENABLED", "true").lower() == "true",
            session_hours=int(values.get("YANXU_SESSION_HOURS", 24)),
            backup_token=values.get("YANXU_BACKUP_TOKEN", "") or "",
            voice_worker_token=values.get("YANXU_VOICE_WORKER_TOKEN", "") or "",
            voice_engine_command=values.get("YANXU_VOICE_ENGINE_COMMAND", "") or "",
            voice_model_version=values.get("YANXU_VOICE_MODEL_VERSION", "wespeaker-cnceleb-resnet34-lm:e7584940aeac8d55:kaldi80-v1"),
            voice_match_threshold=float(values.get("YANXU_VOICE_MATCH_THRESHOLD", .75)),
            voice_match_margin=float(values.get("YANXU_VOICE_MATCH_MARGIN", .08)),
            voice_private_bucket=values.get("YANXU_VOICE_PRIVATE_BUCKET", "") or "",
            voice_private_domain=values.get("YANXU_VOICE_PRIVATE_DOMAIN", "") or "",
        )
