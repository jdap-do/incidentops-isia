"""Pruebas de aceptación del Hito 004 para persistencia dual y health real."""

import json

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

import src.adapters.outbound.postgres_repository as postgres_module
from src.adapters.inbound.api import create_api_app
from src.adapters.inbound.cli import create_cli_app
from src.adapters.outbound.postgres_repository import PostgreSQLIncidentRepository
from src.adapters.outbound.sqlite_repository import SQLiteIncidentRepository
from src.application.services import IncidentService
from src.bootstrap import build_incident_service, resolve_incident_repository

SUCCESS_BODY = {"status": "ok", "database": "connected"}
ERROR_BODY = {"status": "error", "database": "unavailable"}


class RecordingRepository:
    def __init__(self, healthy: bool = True, error: Exception | None = None) -> None:
        self.healthy = healthy
        self.error = error
        self.calls = 0

    def check_health(self) -> bool:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.healthy

    def save_incident(self, incident: object) -> None:
        raise AssertionError("save_incident no debe usarse en pruebas de health")

    def get_incident(self, incident_id: str) -> object | None:
        raise AssertionError("get_incident no debe usarse en pruebas de health")

    def find_open_duplicates(
        self, incident: object, *, exclude_incident_id: str | None = None
    ) -> list[object]:
        raise AssertionError("find_open_duplicates no debe usarse en pruebas de health")

    def list_active_incidents(self, component_filter: str | None = None) -> list[object]:
        raise AssertionError("list_active_incidents no debe usarse en pruebas de health")


def test_successful_connection_matches_rest_and_cli() -> None:
    """Given base accesible, When REST y CLI verifican, Then ejecutan SELECT 1 y coinciden."""
    repository = RecordingRepository(healthy=True)
    service = IncidentService(repository)
    api = create_api_app(service)
    cli = create_cli_app(service)

    with TestClient(api) as client:
        response = client.get("/health")
    result = CliRunner().invoke(cli, ["health"])

    assert response.status_code == 200
    assert response.json() == SUCCESS_BODY
    assert json.loads(result.stdout) == SUCCESS_BODY
    assert result.exit_code == 0
    assert repository.calls == 2


def assert_error_channels(
    api: object, cli: object, repository: RecordingRepository | None, secret: str | None
) -> None:
    with TestClient(api) as client:
        response = client.get("/health")
    result = CliRunner().invoke(cli, ["health"])

    assert response.status_code == 503
    assert response.json() == ERROR_BODY
    assert json.loads(result.stdout) == ERROR_BODY
    assert result.exit_code == 1
    if repository is not None:
        assert repository.calls == 2
    if secret is not None:
        assert secret not in response.text
        assert secret not in result.stdout


def test_failed_connection_matches_rest_and_cli() -> None:
    """Given base inaccesible, When REST y CLI verifican, Then ambos informan error idéntico."""
    repository = RecordingRepository(healthy=False)
    service = IncidentService(repository)
    assert_error_channels(
        create_api_app(service), create_cli_app(service), repository, None
    )


def test_query_failure_does_not_expose_secret() -> None:
    """Given fallo de SELECT 1 con secreto, When se verifica, Then el secreto no aparece."""
    repository = RecordingRepository(error=RuntimeError("password=SECRET_VALUE"))
    service = IncidentService(repository)
    assert_error_channels(
        create_api_app(service), create_cli_app(service), repository, "SECRET_VALUE"
    )


@pytest.mark.parametrize(
    "database_url",
    ["mysql://user:SECRET_VALUE@host/db", "not-a-url", "postgres://user:SECRET_VALUE@host/db"],
)
def test_invalid_database_url_starts_api_and_fails_health(
    monkeypatch: pytest.MonkeyPatch, database_url: str
) -> None:
    """Given DATABASE_URL inválida, When arranca la API, Then health falla sin fallback SQLite."""
    monkeypatch.setenv("DATABASE_URL", database_url)
    service = build_incident_service()

    assert service._repository is None
    assert_error_channels(
        create_api_app(service), create_cli_app(service), None, "SECRET_VALUE"
    )


class FakeCursor:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.statements: list[tuple[str, object]] = []

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def execute(self, query: str, parameters: object = None) -> None:
        self.statements.append((query, parameters))
        if self.error is not None:
            raise self.error

    def fetchone(self) -> tuple[int]:
        return (1,)

    def fetchall(self) -> list[object]:
        return []


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.cursor_instance = cursor

    def __enter__(self) -> "FakeConnection":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool:
        return False

    def cursor(self) -> FakeCursor:
        return self.cursor_instance


def test_engine_selection_uses_sqlite_default_and_never_falls_back() -> None:
    """Given valores de DATABASE_URL, When se resuelve el motor, Then SQLite es el default."""
    assert isinstance(resolve_incident_repository(None), SQLiteIncidentRepository)
    assert isinstance(resolve_incident_repository(""), SQLiteIncidentRepository)
    assert isinstance(
        resolve_incident_repository("sqlite:///:memory:"), SQLiteIncidentRepository
    )
    assert isinstance(
        resolve_incident_repository("postgresql://user:secret@db:5432/incidents"),
        PostgreSQLIncidentRepository,
    )
    assert resolve_incident_repository("mysql://user:secret@host/db") is None
    assert resolve_incident_repository("not-a-url") is None


@pytest.mark.parametrize("healthy", [True, False])
def test_postgres_check_health_executes_select_one(monkeypatch: pytest.MonkeyPatch, healthy: bool) -> None:
    """Given adaptador PostgreSQL, When se verifica, Then ejecuta SELECT 1 y mapea el resultado."""
    cursor = FakeCursor(None if healthy else RuntimeError("connection refused"))
    connection = FakeConnection(cursor)
    monkeypatch.setattr(
        postgres_module.psycopg, "connect", lambda *args, **kwargs: connection
    )
    repository = PostgreSQLIncidentRepository(
        "postgresql://user:secret@db:5432/incidents"
    )

    assert repository.check_health() is healthy
    assert cursor.statements == [("SELECT 1", None)]
