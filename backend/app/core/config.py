import os

from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import BaseModel
from dotenv import load_dotenv


def _load_env_file() -> None:
    """Find and load the .env file from common candidate paths."""
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
        Path(__file__).resolve().parents[3] / ".env",
    ]
    for path in candidates:
        if path.exists():
            load_dotenv(dotenv_path=path)
            return
    load_dotenv()  # Fallback to standard behaviour


_load_env_file()


class AppConfig(BaseModel):
    name: str = "Bangladesh NID Extractor"
    version: str = "2.0.0"


class BackendConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    max_upload_size_mb: int = 10
    supported_formats: list[str] = ["jpg", "jpeg", "png"]
    min_image_dimension: int = 100
    max_image_dimension: int = 6000
    cors_origins: list[str] = ["http://localhost:3000"]


class VisionConfig(BaseModel):
    default_model: str = "google/gemini-2.5-flash"
    max_tokens: int = 1024
    temperature: float = 0.0
    timeout_s: float = 90.0
    retry_attempts: int = 3
    retry_delay_s: float = 1.0


class FrontendConfig(BaseModel):
    port: int = 3000
    api_url: str = "http://localhost:8000"


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    backend: BackendConfig = BackendConfig()
    vision: VisionConfig = VisionConfig()
    frontend: FrontendConfig = FrontendConfig()

    # Secrets from environment variables
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    app_env: str = "dev"

    @property
    def model(self) -> str:
        return self.openrouter_model or self.vision.default_model

    @property
    def max_upload_bytes(self) -> int:
        return self.backend.max_upload_size_mb * 1024 * 1024


def _find_config_path() -> Path | None:
    """Search for config.yaml in common locations."""
    candidates = [
        Path("/app/config.yaml"),          # Docker mount
        Path.cwd() / "config.yaml",        # Current directory
        Path(__file__).resolve().parents[2] / "config.yaml",  # backend/
        Path(__file__).resolve().parents[3] / "config.yaml",  # project root
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


@lru_cache()
def get_settings() -> Settings:
    """Load settings from config.yaml + environment variables."""
    config_data = {}
    config_path = _find_config_path()

    if config_path:
        with open(config_path, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f) or {}

    app_env = os.getenv("APP_ENV", "dev").strip().lower()
    if app_env not in ("prod", "dev"):
        app_env = "dev"

    backend_config = BackendConfig(**config_data.get("backend", {}))

    # Load CORS origins from env (comma-separated list)
    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        origins = [o.strip() for o in cors_env.split(",") if o.strip()]
        for origin in origins:
            if origin not in backend_config.cors_origins:
                backend_config.cors_origins.append(origin)
    elif app_env == "prod":
        # Fallback default prod origins
        prod_origins = [
            "https://81t5j6p1-3000.asse.devtunnels.ms",
            "https://81t5j6p1-3000.asse.devtunnels.ms/",
        ]
        for origin in prod_origins:
            if origin not in backend_config.cors_origins:
                backend_config.cors_origins.append(origin)

    settings = Settings(
        app=AppConfig(**config_data.get("app", {})),
        backend=backend_config,
        vision=VisionConfig(**config_data.get("vision", {})),
        frontend=FrontendConfig(**config_data.get("frontend", {})),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", ""),
        app_env=app_env,
    )

    return settings
