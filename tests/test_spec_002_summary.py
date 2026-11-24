"""Pruebas de aceptación BDD del resumen de incidentes activos del Hito 002."""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api import create_api_app
from src.adapters.inbound.cli import create_cli_app
from src.adapters.outbound.sqlite_repository import create_incident_repository
from src.application.services import REFERENCE_TIME_ERROR, IncidentService
from src.domain.models import Incident

REFERENCE = datetime(2026, 11, 9, 12, 0)
VOLUME_REFERENCE = datetime(2026, 11, 10, 1, 59)


def build_stack() -> SimpleNamespace:
    repository = create_incident_repository("sqlite:///:memory:")
    service = IncidentService(repository)
    return SimpleNamespace(
        repository=repository,
        service=service,
        api=create_api_app(service),
        cli=create_cli_app(service),
    )


@pytest.fixture
def stack() -> SimpleNamespace:
    return build_stack()


@pytest.fixture
def client(stack: SimpleNamespace) -> TestClient:
    with TestClient(stack.api) as test_client:
        yield test_client


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def seed_mixed_incidents(repository: object) -> None:
    rows = [
        Incident(
            "INC-P0", "Pago caído", "payments-gateway", "P0", "OPEN",
            datetime(2026, 11, 9, 9, 0),
        ),
        Incident(
            "INC-P1", "Login lento", "auth-identity", "P1", "IN_PROGRESS",
            datetime(2026, 11, 9, 8, 0),
        ),
        Incident(
            "INC-P2", "Cola de pagos", "PAYMENTS-GATEWAY", "P2", "OPEN",
            datetime(2026, 11, 9, 10, 0),
        ),
        Incident(
            "INC-RESOLVED", "Incidente resuelto", "payments-gateway", "P0", "RESOLVED",
            datetime(2026, 11, 9, 7, 0), datetime(2026, 11, 9, 8, 0),
        ),
        Incident(
            "INC-ESCALATED", "Incidente escalado", "payments-gateway", "P2",
            "ESCALATION_REQUIRED", datetime(2026, 11, 9, 7, 0),
        ),
    ]
    for row in rows:
        repository.save_incident(row)


def test_active_summary_matches_across_rest_and_cli(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given estados mixtos, When se consulta REST y CLI, Then coinciden y excluyen inactivos."""
    seed_mixed_incidents(stack.repository)

    response = client.get(
        "/api/v1/incidents/summary", params={"reference_time": REFERENCE.isoformat()}
    )
    result = cli_runner.invoke(
        stack.cli, ["summary", "--reference-time", REFERENCE.isoformat()]
    )

    assert response.status_code == 200
    assert result.exit_code == 0
    expected = response.json()
    assert json.loads(result.stdout) == expected
    assert expected["total_active"] == 3
    assert expected["breached_count"] == 1
    assert [row["title"] for row in expected["details"]] == [
        "Pago caído", "Login lento", "Cola de pagos"
    ]
    assert all(
        set(row) == {
            "title", "component", "severity", "status",
            "elapsed_minutes", "requires_escalation",
        }
        for row in expected["details"]
    )

    volume = build_stack()
    for index in range(1000):
        volume.repository.save_incident(
            Incident(
                f"VOL-{index:04d}",
                f"Carga {index:04d}",
                "payments-gateway",
                ["P0", "P1", "P2", "P3"][index % 4],
                "OPEN" if index % 2 == 0 else "IN_PROGRESS",
                datetime(2026, 11, 9, 8, 0) + timedelta(minutes=index),
            )
        )
    with TestClient(volume.api) as volume_client:
        volume_response = volume_client.get(
            "/api/v1/incidents/summary",
            params={"reference_time": VOLUME_REFERENCE.isoformat()},
        )
    volume_result = cli_runner.invoke(
        volume.cli, ["summary", "--reference-time", VOLUME_REFERENCE.isoformat()]
    )
    volume_body = volume_response.json()
    assert volume_response.status_code == 200
    assert volume_result.exit_code == 0
    assert json.loads(volume_result.stdout) == volume_body
    assert volume_body["total_active"] == 1000
    assert len(volume_body["details"]) == 1000
    assert len({row["title"] for row in volume_body["details"]}) == 1000


@pytest.mark.parametrize(
    ("raw_filter", "expected_total", "expected_components"),
    [
        ("payments-gateway", 2, ["payments-gateway", "payments-gateway"]),
        (" PAYMENTS-GATEWAY ", 2, ["payments-gateway", "payments-gateway"]),
        ("", 3, ["auth-identity", "payments-gateway", "payments-gateway"]),
        ("missing", 0, []),
    ],
)
def test_component_filter_scopes_totals_and_ignores_case_and_spaces(
    client: TestClient,
    cli_runner: CliRunner,
    stack: SimpleNamespace,
    raw_filter: str,
    expected_total: int,
    expected_components: list[str],
) -> None:
    """Given filtros canónicos, vacíos y desconocidos, When se consulta, Then totales y filas coinciden."""
    rows = [
        Incident(
            "INC-PAY-1", "Pago uno", "payments-gateway", "P1", "OPEN",
            datetime(2026, 11, 9, 9, 0),
        ),
        Incident(
            "INC-PAY-2", "Pago dos", "PAYMENTS-GATEWAY", "P2", "IN_PROGRESS",
            datetime(2026, 11, 9, 10, 0),
        ),
        Incident(
            "INC-AUTH", "Acceso", "auth-identity", "P3", "OPEN",
            datetime(2026, 11, 9, 8, 0),
        ),
    ]
    for row in rows:
        stack.repository.save_incident(row)

    response = client.get(
        "/api/v1/incidents/summary",
        params={"component": raw_filter, "reference_time": REFERENCE.isoformat()},
    )
    result = cli_runner.invoke(
        stack.cli,
        [
            "summary",
            "--component",
            raw_filter,
            "--reference-time",
            REFERENCE.isoformat(),
        ],
    )

    assert response.status_code == 200
    assert result.exit_code == 0
    expected = response.json()
    assert json.loads(result.stdout) == expected
    assert expected["total_active"] == expected_total
    assert len(expected["details"]) == expected_total
    assert sorted(row["component"] for row in expected["details"]) == expected_components


@pytest.mark.parametrize(
    ("title", "created_at", "reference_time", "elapsed", "breached", "escalation"),
    [
        ("P2 límite", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 16), 480, False, True),
        ("P2 excedido", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 16, 1), 481, True, True),
        ("P2 umbral", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 14), 360, False, True),
        ("P2 fin de semana", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9), 120, False, False),
        ("P0 continuo", datetime(2026, 11, 6, 17), datetime(2026, 11, 9, 9), 3840, True, True),
    ],
)
def test_sla_boundary_and_business_hours_match_across_channels(
    client: TestClient,
    cli_runner: CliRunner,
    stack: SimpleNamespace,
    title: str,
    created_at: datetime,
    reference_time: datetime,
    elapsed: int,
    breached: bool,
    escalation: bool,
) -> None:
    """Given límites SLA, When se consulta, Then REST y CLI reflejan minutos, breach y escalamiento."""
    severity = "P0" if title.startswith("P0") else "P2"
    stack.repository.save_incident(
        Incident(
            "INC-SLA", title, "payments-gateway", severity, "OPEN", created_at
        )
    )

    response = client.get(
        "/api/v1/incidents/summary",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(
        stack.cli, ["summary", "--reference-time", reference_time.isoformat()]
    )

    assert response.status_code == 200
    assert result.exit_code == 0
    expected = response.json()
    assert json.loads(result.stdout) == expected
    assert expected["breached_count"] == (1 if breached else 0)
    row = expected["details"][0]
    assert row["title"] == title
    assert row["elapsed_minutes"] == elapsed
    assert row["requires_escalation"] is escalation


def test_empty_and_invalid_summary_requests_are_consistent(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given un dataset vacío y referencias omitidas o inválidas, When se consulta, Then hay paridad y rechazo."""
    explicit = REFERENCE.isoformat()
    empty_response = client.get(
        "/api/v1/incidents/summary", params={"reference_time": explicit}
    )
    empty_cli = cli_runner.invoke(stack.cli, ["summary", "--reference-time", explicit])
    assert empty_response.status_code == 200
    assert empty_cli.exit_code == 0
    assert json.loads(empty_cli.stdout) == empty_response.json()
    assert empty_response.json() == {
        "reference_time": explicit,
        "component_filter": None,
        "total_active": 0,
        "breached_count": 0,
        "details": [],
    }

    stack.repository.save_incident(
        Incident(
            "INC-REF", "Referencia", "payments-gateway", "P1", "OPEN",
            datetime(2026, 11, 9, 8, 0),
        )
    )
    omitted_response = client.get("/api/v1/incidents/summary")
    omitted_cli = cli_runner.invoke(stack.cli, ["summary"])
    assert omitted_response.status_code == 200
    assert omitted_cli.exit_code == 0
    omitted_body = omitted_response.json()
    omitted_cli_body = json.loads(omitted_cli.stdout)
    assert omitted_body["total_active"] == omitted_cli_body["total_active"] == 1
    assert omitted_body["breached_count"] == omitted_cli_body["breached_count"]
    for body in (omitted_body, omitted_cli_body):
        captured = datetime.fromisoformat(body["reference_time"])
        assert captured.tzinfo is None
        assert captured >= datetime(2026, 11, 9, 8, 0)

    for invalid_value in [
        "not-a-date",
        "2026-11-09T12:00:00+00:00",
        "2026-11-09T07:00:00",
    ]:
        bad_response = client.get(
            "/api/v1/incidents/summary", params={"reference_time": invalid_value}
        )
        bad_cli = cli_runner.invoke(
            stack.cli, ["summary", "--reference-time", invalid_value]
        )
        assert bad_response.status_code == 422
        assert bad_response.json() == {"detail": REFERENCE_TIME_ERROR}
        assert bad_cli.exit_code == 1
        assert bad_cli.stdout == ""
        assert REFERENCE_TIME_ERROR in bad_cli.stderr
