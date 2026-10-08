from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # MySQL — 连接信息仅从环境变量读取，代码中不留真实密码
    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "shiguangji"
    mysql_charset: str = "utf8mb4"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7
    cookie_name: str = "access_token"
    admin_cookie_name: str = "admin_access_token"
    cookie_secure: bool = False  # 生产 HTTPS 置 true
    cookie_samesite: str = "lax"

    # Media limits
    max_photo_bytes: int = 10 * 1024 * 1024  # 10 MB
    max_video_bytes: int = 100 * 1024 * 1024  # 100 MB
    max_video_seconds: int = 180  # 3 min
    max_photos_per_post: int = 9
    photo_mime_types: tuple[str, ...] = ("image/jpeg", "image/png", "image/webp")
    video_mime_types: tuple[str, ...] = ("video/mp4", "video/quicktime")

    # Paths
    base_dir: Path = Path(__file__).resolve().parent.parent
    upload_dir: Path = base_dir / "uploads"
    tmp_dir: Path = upload_dir / "tmp"
    photo_dir: Path = upload_dir / "photos"
    video_dir: Path = upload_dir / "videos"
    preview_dir: Path = upload_dir / "previews"

    # CORS / CSRF
    frontend_origin: str = "http://localhost:5173"
    allowed_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174"
    )

    @property
    def allowed_origin_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def database_url(self) -> str:
        return (
            f"mysql+pymysql://{self.mysql_user}:{self.mysql_password}"
            f"@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"
            f"?charset={self.mysql_charset}"
        )


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.tmp_dir.mkdir(parents=True, exist_ok=True)
settings.photo_dir.mkdir(parents=True, exist_ok=True)
settings.video_dir.mkdir(parents=True, exist_ok=True)
settings.preview_dir.mkdir(parents=True, exist_ok=True)
