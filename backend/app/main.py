from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import logger
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: log startup and shutdown events."""
    settings = get_settings()
    logger.info("Starting Bangladesh NID Extractor API")
    logger.info(f"Version: {settings.app.version}")
    logger.info(f"Vision model: {settings.model}")
    logger.info(f"Retry attempts: {settings.vision.retry_attempts}")

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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.backend.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app


app = create_app()
