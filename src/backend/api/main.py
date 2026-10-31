"""Main FastAPI Application Entrypoint."""

import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from loguru import logger

from ...config import settings
from ..db.session import init_db
from .routes.violations import router as violations_router
from .routes.configs import router as configs_router
from .routes.streams import router as streams_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown procedures."""
    logger.info("Initializing Database...")
    init_db()
    yield
    logger.info("Shutting down Traffic Violation API server.")


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description="Enterprise Real-time Traffic Violation Detection & ALPR REST API",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Evidence Directory for Media Serving
evidence_path = Path(settings.local_storage_dir)
evidence_path.mkdir(parents=True, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=str(evidence_path)), name="evidence")

# Mount Static Assets for Dashboard UI
static_path = Path("src/dashboard/static")
static_path.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include Routers
app.include_router(violations_router)
app.include_router(configs_router)
app.include_router(streams_router)


@app.get("/")
def serve_dashboard():
    """Serves the main Web Dashboard UI."""
    index_file = Path("src/dashboard/templates/index.html")
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Traffic Violation Detection System API is live. Navigate to /docs for Swagger UI."}


@app.get("/healthz")
def health_check():
    """Health check probe for container orchestrators."""
    return {"status": "HEALTHY", "app": settings.app_name, "version": "1.0.0"}
