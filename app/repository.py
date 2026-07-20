"""SQLite persistence and immutable assessment workflow."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Callable, Mapping
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas import ScenarioCreate

Evaluator = Callable[[Mapping[str, object]], Mapping[str, object]]
BlueprintBuilder = Callable[[Mapping[str, object]], object]
DiagramRenderer = Callable[[object], str]


def _default_evaluator(requirements: Mapping[str, object]) -> Mapping[str, object]:
    from app.engine import evaluate_configuration

    return evaluate_configuration(requirements)


def _default_blueprint_builder(assessment: Mapping[str, object]) -> object:
    from app.architecture import build_blueprint

    return build_blueprint(assessment)


def _default_diagram_renderer(blueprint: object) -> str:
    from app.diagram import render_architecture_svg

    return render_architecture_svg(blueprint)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _mapping_snapshot(value: object) -> dict[str, object]:
    if is_dataclass(value) and not isinstance(value, type):
        serialized = asdict(value)
    elif isinstance(value, Mapping):
        serialized = dict(value)
    else:
        raise TypeError("blueprint builder must return a dataclass or mapping")
    return json.loads(_json(serialized))


class ScenarioRepository:
    """Own scenario versions and append-only assessment-run snapshots."""

    def __init__(
        self,
        database_path: str | Path | None = None,
        *,
        connection: sqlite3.Connection | None = None,
        evaluator: Evaluator = _default_evaluator,
        blueprint_builder: BlueprintBuilder = _default_blueprint_builder,
        diagram_renderer: DiagramRenderer = _default_diagram_renderer,
    ) -> None:
        if connection is not None and database_path is not None:
            raise ValueError("provide connection or database_path, not both")
        if connection is None:
            path = Path(database_path or "data/configurator.db")
            path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        self._connection = connection
        self._evaluator = evaluator
        self._blueprint_builder = blueprint_builder
        self._diagram_renderer = diagram_renderer
        self._lock = threading.RLock()
        self._initialize()

    def _initialize(self) -> None:
        with self._lock, self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scenarios (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL,
                    fictional INTEGER NOT NULL CHECK (fictional = 1),
                    requirements_json TEXT NOT NULL,
                    version INTEGER NOT NULL CHECK (version > 0),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT
                );

                CREATE TABLE IF NOT EXISTS assessment_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    scenario_id INTEGER NOT NULL,
                    scenario_version INTEGER NOT NULL CHECK (scenario_version > 0),
                    scenario_name TEXT NOT NULL,
                    scenario_description TEXT NOT NULL,
                    requirements_json TEXT NOT NULL,
                    assessment_json TEXT NOT NULL,
                    blueprint_json TEXT NOT NULL,
                    architecture_svg TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (scenario_id) REFERENCES scenarios(id),
                    UNIQUE (scenario_id, scenario_version)
                );

                CREATE INDEX IF NOT EXISTS idx_assessment_runs_scenario
                ON assessment_runs (scenario_id, scenario_version);
                """
            )

    def _build_artifacts(
        self, scenario: ScenarioCreate
    ) -> tuple[dict[str, object], dict[str, object], str]:
        requirements = scenario.requirements_dict()
        engine_result = dict(self._evaluator(dict(requirements)))
        assessment = json.loads(
            _json(
                {
                    **engine_result,
                    "scenario_name": scenario.name,
                    "scenario_description": scenario.description,
                    "fictional": True,
                    "requirements": dict(requirements),
                }
            )
        )
        blueprint_object = self._blueprint_builder(assessment)
        blueprint = _mapping_snapshot(blueprint_object)
        architecture_svg = self._diagram_renderer(blueprint_object)
        if not isinstance(architecture_svg, str) or not architecture_svg.lstrip().startswith(
            "<svg"
        ):
            raise ValueError("diagram renderer must return SVG markup")
        return assessment, blueprint, architecture_svg

    def create_scenario(self, scenario: ScenarioCreate) -> dict[str, Any]:
        requirements = scenario.requirements_dict()
        assessment, blueprint, architecture_svg = self._build_artifacts(scenario)
        timestamp = _utc_now()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO scenarios (
                    name, description, fictional, requirements_json, version, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    scenario.name,
                    scenario.description,
                    1,
                    _json(requirements),
                    1,
                    timestamp,
                    timestamp,
                ),
            )
            scenario_id = int(cursor.lastrowid or 0)
            self._insert_run(
                scenario_id=scenario_id,
                scenario_version=1,
                scenario=scenario,
                requirements=requirements,
                assessment=assessment,
                blueprint=blueprint,
                architecture_svg=architecture_svg,
                created_at=timestamp,
            )
        created = self.get_scenario(scenario_id)
        if created is None:  # pragma: no cover - transaction invariant
            raise RuntimeError("created scenario could not be read")
        return created

    def update_scenario(self, scenario_id: int, scenario: ScenarioCreate) -> dict[str, Any] | None:
        with self._lock:
            current = self._scenario_row(scenario_id)
            if current is None:
                return None
            next_version = int(current["version"]) + 1
            requirements = scenario.requirements_dict()
            assessment, blueprint, architecture_svg = self._build_artifacts(scenario)
            timestamp = _utc_now()
            with self._connection:
                self._connection.execute(
                    """
                    UPDATE scenarios
                    SET name = ?, description = ?, fictional = 1, requirements_json = ?,
                        version = ?, updated_at = ?
                    WHERE id = ? AND deleted_at IS NULL
                    """,
                    (
                        scenario.name,
                        scenario.description,
                        _json(requirements),
                        next_version,
                        timestamp,
                        scenario_id,
                    ),
                )
                self._insert_run(
                    scenario_id=scenario_id,
                    scenario_version=next_version,
                    scenario=scenario,
                    requirements=requirements,
                    assessment=assessment,
                    blueprint=blueprint,
                    architecture_svg=architecture_svg,
                    created_at=timestamp,
                )
        return self.get_scenario(scenario_id)

    def _insert_run(
        self,
        *,
        scenario_id: int,
        scenario_version: int,
        scenario: ScenarioCreate,
        requirements: dict[str, object],
        assessment: dict[str, object],
        blueprint: dict[str, object],
        architecture_svg: str,
        created_at: str,
    ) -> None:
        self._connection.execute(
            """
            INSERT INTO assessment_runs (
                scenario_id, scenario_version, scenario_name, scenario_description,
                requirements_json, assessment_json, blueprint_json, architecture_svg, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scenario_id,
                scenario_version,
                scenario.name,
                scenario.description,
                _json(requirements),
                _json(assessment),
                _json(blueprint),
                architecture_svg,
                created_at,
            ),
        )

    def _scenario_row(self, scenario_id: int) -> sqlite3.Row | None:
        return self._connection.execute(
            "SELECT * FROM scenarios WHERE id = ? AND deleted_at IS NULL", (scenario_id,)
        ).fetchone()

    def get_scenario(self, scenario_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._scenario_row(scenario_id)
            return self._scenario_from_row(row) if row is not None else None

    def list_scenarios(self) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM scenarios WHERE deleted_at IS NULL ORDER BY id"
            ).fetchall()
            return [self._scenario_from_row(row) for row in rows]

    def _scenario_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        scenario_id = int(row["id"])
        requirements = json.loads(row["requirements_json"])
        latest_row = self._connection.execute(
            """
            SELECT * FROM assessment_runs
            WHERE scenario_id = ?
            ORDER BY scenario_version DESC
            LIMIT 1
            """,
            (scenario_id,),
        ).fetchone()
        return {
            "id": scenario_id,
            "name": row["name"],
            "description": row["description"],
            "fictional": bool(row["fictional"]),
            **requirements,
            "version": int(row["version"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "latest_run": self._run_from_row(latest_row) if latest_row is not None else None,
        }

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM assessment_runs WHERE id = ?", (run_id,)
            ).fetchone()
            return self._run_from_row(row) if row is not None else None

    def list_runs(self, scenario_id: int) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM assessment_runs
                WHERE scenario_id = ?
                ORDER BY scenario_version
                """,
                (scenario_id,),
            ).fetchall()
            return [self._run_from_row(row) for row in rows]

    @staticmethod
    def _run_from_row(row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "scenario_id": int(row["scenario_id"]),
            "scenario_version": int(row["scenario_version"]),
            "scenario_name": row["scenario_name"],
            "scenario_description": row["scenario_description"],
            "requirements": json.loads(row["requirements_json"]),
            "assessment": json.loads(row["assessment_json"]),
            "blueprint": json.loads(row["blueprint_json"]),
            "architecture_svg": row["architecture_svg"],
            "created_at": row["created_at"],
        }

    def delete_scenario(self, scenario_id: int) -> bool:
        timestamp = _utc_now()
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                UPDATE scenarios SET deleted_at = ?, updated_at = ?
                WHERE id = ? AND deleted_at IS NULL
                """,
                (timestamp, timestamp, scenario_id),
            )
            return cursor.rowcount == 1

    def has_active_name(self, name: str) -> bool:
        with self._lock:
            row = self._connection.execute(
                "SELECT 1 FROM scenarios WHERE name = ? AND deleted_at IS NULL LIMIT 1", (name,)
            ).fetchone()
            return row is not None

    def close(self) -> None:
        with self._lock:
            self._connection.close()
