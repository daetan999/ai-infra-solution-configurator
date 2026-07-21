"""FastAPI application composition for the Enterprise AI Solution Configurator."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.demo_data import seed_demo_scenarios
from app.repository import ScenarioRepository
from app.routes import register_routes

ROOT = Path(__file__).resolve().parents[1]


def _database_path() -> str:
    return (
        os.getenv("CONFIGURATOR_DB")
        or os.getenv("CONFIGURATOR_DATABASE_PATH")
        or "data/configurator.db"
    )


def create_app(
    *,
    repository: ScenarioRepository | object | None = None,
    seed_demos: bool | None = None,
) -> FastAPI:
    """Create an app with injectable persistence for isolated tests and deployments."""

    repo = repository or ScenarioRepository(database_path=_database_path())
    application = FastAPI(
        title="Enterprise AI Solution Configurator",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    application.state.repository = repo
    should_seed = seed_demos if seed_demos is not None else os.getenv("SEED_DEMO_DATA") == "true"
    if should_seed:
        seed_demo_scenarios(repo)  # type: ignore[arg-type]
    static_directory = ROOT / "static"
    if static_directory.is_dir():
        application.mount("/static", StaticFiles(directory=static_directory), name="static")
    register_routes(application, repo)
    return application


app = create_app()
