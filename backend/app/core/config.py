import os
from pathlib import Path
from functools import lru_cache

import yaml
from pydantic import BaseModel


class AppConfig(BaseModel):
    name: str = "Bangladesh NID Extractor"
    version: str = "1.0.0"


class BackendConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    max_upload_size_mb: int = 10
    supported_formats: list[str] = ["jpg", "jpeg", "png"]
    min_image_dimension: int = 100
    max_image_dimension: int = 6000
    cors_origins: list[str] = ["http://localhost:3000"]


class OCRConfig(BaseModel):
    languages: list[str] = ["en", "bn"]
    use_gpu: bool = False
    confidence_threshold: float = 0.5


class VisionConfig(BaseModel):
    default_model: str = "google/gemini-2.5-flash"
    max_tokens: int = 2048
    temperature: float = 0.1


class FrontendConfig(BaseModel):
    port: int = 3000
    api_url: str = "http://localhost:8000"


class Settings(BaseModel):
    app: AppConfig = AppConfig()
    backend: BackendConfig = BackendConfig()
    ocr: OCRConfig = OCRConfig()
    vision: VisionConfig = VisionConfig()
    frontend: FrontendConfig = FrontendConfig()

    # Secrets from environment variables
    openrouter_api_key: str = ""
    openrouter_model: str = ""

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

    settings = Settings(
        app=AppConfig(**config_data.get("app", {})),
        backend=BackendConfig(**config_data.get("backend", {})),
        ocr=OCRConfig(**config_data.get("ocr", {})),
        vision=VisionConfig(**config_data.get("vision", {})),
        frontend=FrontendConfig(**config_data.get("frontend", {})),
        openrouter_api_key=os.getenv("OPENROUTER_API_KEY", ""),
        openrouter_model=os.getenv("OPENROUTER_MODEL", ""),
    )

    return settings
