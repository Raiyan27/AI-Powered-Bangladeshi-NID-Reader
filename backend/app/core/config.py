import os
from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import BaseModel
from dotenv import load_dotenv


def _load_env_file() -> None:
    """Find and load the .env file from custom path or common candidate paths."""
    env_path = os.getenv("DOTENV_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists() and path.is_file():
            load_dotenv(dotenv_path=path)
            return

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
    jpeg_quality: int = 95


class VisionConfig(BaseModel):
    default_model: str = "google/gemini-3.1-flash-lite"
    api_url: str = "https://openrouter.ai/api/v1/chat/completions"
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

    # Secrets/Config from environment variables
    openrouter_api_key: str = ""
    openrouter_model: str = ""
    openrouter_api_url: str = ""
    app_env: str = "dev"

    @property
    def model(self) -> str:
        return self.openrouter_model or self.vision.default_model

    @property
    def vision_api_url(self) -> str:
        return self.openrouter_api_url or self.vision.api_url

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

    # Resolve AppConfig
    app_dict = config_data.get("app", {})
    if os.getenv("APP_NAME"):
        app_dict["name"] = os.getenv("APP_NAME")
    if os.getenv("APP_VERSION"):
        app_dict["version"] = os.getenv("APP_VERSION")
    app_config = AppConfig(**app_dict)

    # Resolve BackendConfig
    backend_dict = config_data.get("backend", {})
    if os.getenv("BACKEND_HOST"):
        backend_dict["host"] = os.getenv("BACKEND_HOST")
    if os.getenv("BACKEND_PORT"):
        try:
            backend_dict["port"] = int(os.getenv("BACKEND_PORT"))
        except ValueError:
            pass
    if os.getenv("MAX_UPLOAD_SIZE_MB"):
        try:
            backend_dict["max_upload_size_mb"] = int(os.getenv("MAX_UPLOAD_SIZE_MB"))
        except ValueError:
            pass
    if os.getenv("MIN_IMAGE_DIMENSION"):
        try:
            backend_dict["min_image_dimension"] = int(os.getenv("MIN_IMAGE_DIMENSION"))
        except ValueError:
            pass
    if os.getenv("MAX_IMAGE_DIMENSION"):
        try:
            backend_dict["max_image_dimension"] = int(os.getenv("MAX_IMAGE_DIMENSION"))
        except ValueError:
            pass
    if os.getenv("BACKEND_JPEG_QUALITY"):
        try:
            backend_dict["jpeg_quality"] = int(os.getenv("BACKEND_JPEG_QUALITY"))
        except ValueError:
            pass
    if os.getenv("BACKEND_SUPPORTED_FORMATS"):
        backend_dict["supported_formats"] = [
            f.strip().lower() for f in os.getenv("BACKEND_SUPPORTED_FORMATS").split(",") if f.strip()
        ]
    
    backend_config = BackendConfig(**backend_dict)

    # Load CORS origins from env (comma-separated list)
    cors_env = os.getenv("CORS_ORIGINS")
    if cors_env:
        origins = [o.strip() for o in cors_env.split(",") if o.strip()]
        for origin in origins:
            if origin not in backend_config.cors_origins:
                backend_config.cors_origins.append(origin)

    # Resolve VisionConfig
    vision_dict = config_data.get("vision", {})
    if os.getenv("OPENROUTER_MODEL"):
        vision_dict["default_model"] = os.getenv("OPENROUTER_MODEL")
    if os.getenv("VISION_MAX_TOKENS"):
        try:
            vision_dict["max_tokens"] = int(os.getenv("VISION_MAX_TOKENS"))
        except ValueError:
            pass
    if os.getenv("VISION_TEMPERATURE"):
        try:
            vision_dict["temperature"] = float(os.getenv("VISION_TEMPERATURE"))
        except ValueError:
            pass
    if os.getenv("VISION_TIMEOUT_S"):
        try:
            vision_dict["timeout_s"] = float(os.getenv("VISION_TIMEOUT_S"))
        except ValueError:
            pass
    if os.getenv("VISION_RETRY_ATTEMPTS"):
        try:
            vision_dict["retry_attempts"] = int(os.getenv("VISION_RETRY_ATTEMPTS"))
        except ValueError:
            pass
    if os.getenv("VISION_RETRY_DELAY_S"):
        try:
            vision_dict["retry_delay_s"] = float(os.getenv("VISION_RETRY_DELAY_S"))
        except ValueError:
            pass
    if os.getenv("OPENROUTER_API_URL"):
        vision_dict["api_url"] = os.getenv("OPENROUTER_API_URL")

    vision_config = VisionConfig(**vision_dict)

    # Resolve FrontendConfig
    frontend_dict = config_data.get("frontend", {})
    if os.getenv("FRONTEND_PORT"):
        try:
            frontend_dict["port"] = int(os.getenv("FRONTEND_PORT"))
        except ValueError:
            pass
    if os.getenv("NEXT_PUBLIC_API_URL"):
        frontend_dict["api_url"] = os.getenv("NEXT_PUBLIC_API_URL")
    
    frontend_config = FrontendConfig(**frontend_dict)

    settings = Settings(
        app=app_config,
        backend=backend_config,
        vision=vision_config,
        frontend=frontend_config,
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", "") or vision_config.default_model,
        openrouter_api_url=os.getenv("OPENROUTER_API_URL", "") or vision_config.api_url,
        app_env=app_env,
    )

    return settings
