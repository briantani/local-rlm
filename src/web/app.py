"""
FastAPI Application Factory.

Creates and configures the FastAPI application with all routes and middleware.
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.web.dependencies import get_services
from src.web.routes import configs, sessions, tasks
from src.web.websocket import stream
from src.web.database import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting RLM Web Application...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Initialize services
    services = get_services()
    logger.info(f"Found {len(services.config_service.get_profile_names())} configuration profiles")

    yield

    # Shutdown
    logger.info("Shutting down RLM Web Application...")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="RLM Agent API",
        description=(
            "REST API and WebSocket interface for the Recursive Language Model Agent. "
            "Execute tasks, stream real-time updates, and manage configurations."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict in production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
    app.include_router(configs.router, prefix="/api/configs", tags=["Configs"])
    app.include_router(tasks.router, prefix="/api/tasks", tags=["Tasks"])
    app.include_router(stream.router, tags=["WebSocket"])

    # Mount static files (for Phase 14)
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Setup templates
    templates_path = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_path))

    @app.get("/", tags=["UI"])
    async def index(request: Request):
        """Render the main UI page."""
        return templates.TemplateResponse("index.html", {"request": request})

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    return app


# Create app instance for uvicorn
app = create_app()
