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

    # Import chat, export, and share routers
    from src.web.routes import chat, export, share, templates
    app.include_router(chat.router)
    app.include_router(export.router)
    app.include_router(share.router)
    app.include_router(templates.router)

    # Mount static files (for Phase 14)
    static_path = Path(__file__).parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

    # Setup templates
    templates_path = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_path))

    # Initialize services for routes
    services = get_services()

    @app.get("/", tags=["UI"])
    async def index(request: Request):
        """Render the main UI page (simplified chat interface)."""
        return templates.TemplateResponse(request, "index.html")

    @app.get("/configs", tags=["UI"])
    async def configs_list(request: Request):
        """Render the configurations list page."""
        return templates.TemplateResponse(request, "configs.html")

    @app.get("/configs/estimate", tags=["UI"])
    async def cost_estimator(request: Request):
        """Render the cost estimator page."""
        return templates.TemplateResponse(request, "cost_estimator.html")

    @app.get("/configs/compare", tags=["UI"])
    async def configs_compare(request: Request, config: list[str] = []):
        """Render the configuration comparison page."""
        # Get config names from query params
        config_names = request.query_params.getlist("config")

        # Load the configurations
        configs_data = []
        for name in config_names:
            try:
                summary = services.config_service.get_profile_summary(name)
                if summary:
                    # Get required providers
                    required_providers = summary.get_required_providers()

                    # Estimate cost
                    if not required_providers:
                        cost_estimate = "Free"
                    else:
                        root_model = summary.root_model.lower() if summary.root_model else ""
                        if "flash" in root_model:
                            cost_estimate = "~$0.01/task"
                        elif "pro" in root_model:
                            cost_estimate = "~$0.05/task"
                        elif "gpt-4" in root_model:
                            cost_estimate = "~$0.10/task"
                        else:
                            cost_estimate = "~$0.02/task"

                    profile_dict = {
                        "name": name,
                        "description": summary.description,
                        "root_model": summary.root_model,
                        "coder_model": summary.coder_model,
                        "delegate_model": summary.delegate_model,
                        "required_providers": required_providers,
                        "cost_estimate": cost_estimate,
                    }
                    configs_data.append(profile_dict)
            except Exception as e:
                logger.warning(f"Failed to load config {name}: {e}")

        return templates.TemplateResponse(
            request,
            "config_compare.html",
            {"configs": configs_data}
        )

    @app.get("/configs/{name}", tags=["UI"])
    async def config_detail(request: Request, name: str):
        """Render the configuration detail page."""
        from dataclasses import asdict
        from pathlib import Path

        try:
            # Load the configuration
            config = services.config_service.load_profile(name)
            if not config:
                return templates.TemplateResponse(
                    request,
                    "error.html",
                    {"error": "Configuration not found"},
                    status_code=404
                )

            # Load YAML content
            config_path = Path("configs") / f"{name}.yaml"
            yaml_content = ""
            if config_path.exists():
                yaml_content = config_path.read_text()

            # Get summary for required providers
            summary = services.config_service.get_profile_summary(name)
            required_providers = summary.get_required_providers() if summary else []

            # Prepare config data
            profile_dict = asdict(config)
            profile_dict["name"] = name
            profile_dict["root_model"] = profile_dict.get("root", {}).get("model", "Unknown")
            profile_dict["coder_model"] = profile_dict.get("modules", {}).get("coder", {}).get("model", "Unknown")
            profile_dict["delegate_model"] = profile_dict.get("delegate", {}).get("model", None)
            profile_dict["required_providers"] = required_providers

            # Estimate cost
            provider = "local" if not required_providers else "cloud"
            if provider == "local":
                profile_dict["cost_estimate"] = "Free"
            else:
                profile_dict["cost_estimate"] = "~$0.02/task"

            # Extract modules info
            modules_list = []
            for module_name, module_config in profile_dict.get("modules", {}).items():
                modules_list.append({
                    "name": module_name,
                    "model": module_config.get("model", "Unknown"),
                    "provider": module_config.get("provider", "Unknown"),
                    "temperature": module_config.get("temperature", 0.7)
                })
            profile_dict["modules"] = modules_list

            return templates.TemplateResponse(
                request,
                "config_detail.html",
                {
                    "config": profile_dict,
                    "yaml_content": yaml_content
                }
            )
        except Exception as e:
            logger.error(f"Error loading config detail: {e}")
            return templates.TemplateResponse(
                request,
                "error.html",
                {"error": str(e)},
                status_code=500
            )

    @app.get("/health", tags=["Health"])
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "version": "0.1.0"}

    return app


# Create app instance for uvicorn
app = create_app()
