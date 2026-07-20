"""FastAPI application for the Enterprise AI Solution Configurator."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.demo_data import seed_demo_scenarios
from app.exports import json_export, markdown_export, validate_svg_export
from app.repository import ScenarioRepository
from app.schemas import ScenarioCreate

LOGGER = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[1]


def _success(data: object, *, status_code: int = 200) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"success": True, "data": data, "error": None, "meta": {}},
    )


def _error(
    status_code: int, code: str, message: str, details: object | None = None
) -> JSONResponse:
    error: dict[str, object] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "error": error, "meta": {}},
    )


def _public_run(run: Mapping[str, object]) -> dict[str, object]:
    run_id = int(run["id"])
    return {key: value for key, value in run.items() if key != "architecture_svg"} | {
        "diagram_url": f"/api/runs/{run_id}/architecture.svg",
        "export_url": f"/api/runs/{run_id}/export.json",
    }


def _scenario_bundle(scenario: Mapping[str, object]) -> dict[str, object]:
    latest = scenario.get("latest_run")
    public_scenario = {key: value for key, value in scenario.items() if key != "latest_run"}
    return {
        "scenario": public_scenario,
        "latest_run": _public_run(latest) if isinstance(latest, Mapping) else None,
    }


def _download(
    content: str,
    *,
    media_type: str,
    filename: str,
    svg: bool = False,
) -> Response:
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Content-Type-Options": "nosniff",
    }
    if svg:
        headers["Content-Security-Policy"] = (
            "sandbox; default-src 'none'; style-src 'unsafe-inline'"
        )
    return Response(content=content, media_type=media_type, headers=headers)


def create_app(
    *,
    repository: ScenarioRepository | object | None = None,
    seed_demos: bool | None = None,
) -> FastAPI:
    """Create an app with an injectable repository for isolated tests and deployments."""

    repo = repository or ScenarioRepository(
        database_path=os.getenv("CONFIGURATOR_DATABASE_PATH", "data/configurator.db")
    )
    application = FastAPI(
        title="Enterprise AI Solution Configurator",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url=None,
    )
    application.state.repository = repo

    if seed_demos if seed_demos is not None else os.getenv("SEED_DEMO_DATA") == "true":
        seed_demo_scenarios(repo)  # type: ignore[arg-type]

    static_directory = ROOT / "static"
    if static_directory.is_dir():
        application.mount("/static", StaticFiles(directory=static_directory), name="static")

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exception: RequestValidationError
    ) -> JSONResponse:
        details = [
            {
                "field": ".".join(str(part) for part in error.get("loc", ())),
                "type": error.get("type", "invalid_value"),
            }
            for error in exception.errors()
        ]
        return _error(422, "validation_error", "Request validation failed.", details)

    @application.exception_handler(Exception)
    async def unexpected_error_handler(_request: Request, exception: Exception) -> JSONResponse:
        LOGGER.exception("Unhandled configurator request failure", exc_info=exception)
        return _error(500, "internal_error", "The request could not be completed.")

    @application.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def interface() -> HTMLResponse:
        template_directory = ROOT / "templates"
        if not (template_directory / "index.html").is_file():
            return HTMLResponse("<h1>Enterprise AI Solution Configurator</h1>")
        environment = Environment(
            loader=FileSystemLoader(template_directory),
            autoescape=select_autoescape(("html", "xml")),
        )
        return HTMLResponse(environment.get_template("index.html").render())

    @application.get("/api/health")
    async def health() -> JSONResponse:
        return _success({"status": "ok"})

    @application.get("/api/scenarios")
    async def list_scenarios() -> JSONResponse:
        scenarios = repo.list_scenarios()  # type: ignore[attr-defined]
        summaries = [
            {key: value for key, value in scenario.items() if key != "latest_run"}
            for scenario in scenarios
        ]
        return _success({"scenarios": summaries, "count": len(summaries)})

    @application.post("/api/scenarios")
    async def create_scenario(payload: ScenarioCreate) -> JSONResponse:
        scenario = repo.create_scenario(payload)  # type: ignore[attr-defined]
        return _success(_scenario_bundle(scenario), status_code=201)

    @application.get("/api/scenarios/{scenario_id}")
    async def get_scenario(scenario_id: int) -> JSONResponse:
        scenario = repo.get_scenario(scenario_id)  # type: ignore[attr-defined]
        if scenario is None:
            return _error(404, "not_found", "Scenario was not found.")
        return _success(_scenario_bundle(scenario))

    @application.put("/api/scenarios/{scenario_id}")
    async def update_scenario(scenario_id: int, payload: ScenarioCreate) -> JSONResponse:
        scenario = repo.update_scenario(scenario_id, payload)  # type: ignore[attr-defined]
        if scenario is None:
            return _error(404, "not_found", "Scenario was not found.")
        return _success(_scenario_bundle(scenario))

    @application.delete("/api/scenarios/{scenario_id}")
    async def delete_scenario(scenario_id: int) -> JSONResponse:
        if not repo.delete_scenario(scenario_id):  # type: ignore[attr-defined]
            return _error(404, "not_found", "Scenario was not found.")
        return _success({"deleted": True, "id": scenario_id})

    @application.get("/api/scenarios/{scenario_id}/runs")
    async def list_runs(scenario_id: int) -> JSONResponse:
        scenario = repo.get_scenario(scenario_id)  # type: ignore[attr-defined]
        if scenario is None:
            return _error(404, "not_found", "Scenario was not found.")
        runs = repo.list_runs(scenario_id)  # type: ignore[attr-defined]
        return _success({"runs": [_public_run(run) for run in runs], "count": len(runs)})

    @application.get("/api/runs/{run_id}")
    async def get_run(run_id: int) -> JSONResponse:
        run = repo.get_run(run_id)  # type: ignore[attr-defined]
        if run is None:
            return _error(404, "not_found", "Assessment run was not found.")
        return _success({"run": _public_run(run)})

    def require_run(run_id: int) -> Mapping[str, object] | None:
        return repo.get_run(run_id)  # type: ignore[attr-defined]

    def require_latest_run(scenario_id: int) -> Mapping[str, object] | None:
        scenario = repo.get_scenario(scenario_id)  # type: ignore[attr-defined]
        if not isinstance(scenario, Mapping):
            return None
        latest = scenario.get("latest_run")
        return latest if isinstance(latest, Mapping) else None

    def export_response(run: Mapping[str, object], export_format: str) -> Response:
        run_id = int(run["id"])
        if export_format == "json":
            return _download(
                json_export(run),
                media_type="application/json",
                filename=f"solution-run-{run_id}.json",
            )
        if export_format == "markdown":
            return _download(
                markdown_export(run),
                media_type="text/markdown",
                filename=f"solution-run-{run_id}.md",
            )
        svg = validate_svg_export(run.get("architecture_svg"))
        return _download(
            svg,
            media_type="image/svg+xml",
            filename=f"architecture-run-{run_id}.svg",
            svg=True,
        )

    @application.get("/api/runs/{run_id}/export.json")
    async def export_run_json(run_id: int) -> Response:
        run = require_run(run_id)
        if run is None:
            return _error(404, "not_found", "Assessment run was not found.")
        return export_response(run, "json")

    @application.get("/api/runs/{run_id}/export.md")
    async def export_run_markdown(run_id: int) -> Response:
        run = require_run(run_id)
        if run is None:
            return _error(404, "not_found", "Assessment run was not found.")
        return export_response(run, "markdown")

    @application.get("/api/runs/{run_id}/architecture.svg")
    async def export_run_svg(run_id: int) -> Response:
        run = require_run(run_id)
        if run is None:
            return _error(404, "not_found", "Assessment run was not found.")
        return export_response(run, "svg")

    @application.get("/api/scenarios/{scenario_id}/diagram.svg")
    async def scenario_diagram(scenario_id: int) -> Response:
        run = require_latest_run(scenario_id)
        if run is None:
            return _error(404, "not_found", "Scenario was not found.")
        return export_response(run, "svg")

    @application.get("/api/scenarios/{scenario_id}/export")
    async def scenario_export(
        scenario_id: int,
        format: Literal["json", "markdown", "svg"] = Query(...),
    ) -> Response:
        run = require_latest_run(scenario_id)
        if run is None:
            return _error(404, "not_found", "Scenario was not found.")
        return export_response(run, format)

    return application


app = create_app()
