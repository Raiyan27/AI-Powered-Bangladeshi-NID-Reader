from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import logger
from app.api.routes import router
from app.services.ocr_service import get_ocr_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize resources on startup."""
    logger.info("Starting Bangladesh NID Extractor API")
    settings = get_settings()
    logger.info(f"Version: {settings.app.version}")
    logger.info(f"Vision model: {settings.model}")

    # Pre-load OCR engine to avoid cold start on first request
    logger.info("Pre-loading OCR engine...")
    get_ocr_engine()
    logger.info("OCR engine ready")

    yield

    logger.info("Shutting down NID Extractor API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app.name,
        version=settings.app.version,
        description="AI-powered Bangladesh National ID card information extractor",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routes
    app.include_router(router)

    return app


app = create_app()
