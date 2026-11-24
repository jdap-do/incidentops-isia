"""Pruebas de aceptación del ciclo de vida de incidentes y SLA del Hito 003."""

import json
import re
import time
from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api import create_api_app
from src.adapters.inbound.cli import create_cli_app
from src.adapters.outbound.sqlite_repository import create_incident_repository
from src.application.services import (
    INCIDENT_NOT_FOUND_ERROR,
    INVALID_INITIAL_STATUS_ERROR,
    INVALID_INCIDENT_ID_ERROR,
    REFERENCE_TIME_ERROR,
    REQUIRED_FIELDS_ERROR,
    IncidentService,
)
from src.domain.models import Incident
from src.domain.triage_rules import classify_incident_report

P0_RAW = "El gateway de pagos cayó y devuelve HTTP 502 en todas las transacciones."
P1_RAW = "El cluster de datos está al 95% de conexiones con degradación severa."
P2_RAW = "Los reportes están lentos con 10.000 registros."
P2_EXPORT_RAW = "La exportación a Excel tarda."
P3_RAW = "Cambiar el color del botón."

SNAPSHOT_KEYS = {
    "incident_id",
    "title",
    "component",
    "severity",
    "status",
    "created_at",
    "duplicate_group_key",
}
SLA_KEYS = {
    "incident_id",
    "reference_time",
    "effective_time",
    "elapsed_minutes",
    "allowed_minutes",
    "remaining_minutes",
    "is_breached",
    "requires_escalation",
}


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


def duplicate_key(raw_text: str) -> str:
    return classify_incident_report("INC-SEED", raw_text).duplicate_group_key


def seed_incident(
    repository: object,
    incident_id: str,
    raw_text: str,
    status: str,
    created_at: datetime,
    *,
    title: str = "Reporte sembrado",
    resolved_at: datetime | None = None,
    duplicate_group: str | None = None,
) -> None:
    triage = classify_incident_report(incident_id, raw_text)
    repository.save_incident(
        Incident(
            incident_id=incident_id,
            title=title,
            raw_text=raw_text,
            component=triage.component,
            severity=triage.severity,
            status=status,
            created_at=created_at,
            resolved_at=resolved_at,
            duplicate_group_key=duplicate_group or triage.duplicate_group_key,
        )
    )


def register_payload(
    incident_id: str | None,
    raw_text: str,
    created_at: datetime,
    *,
    title: str = "Fallo de pasarela de pagos",
    status: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"title": title, "raw_text": raw_text}
    if incident_id is not None:
        payload["incident_id"] = incident_id
    payload["created_at"] = created_at.isoformat()
    if status is not None:
        payload["status"] = status
    return payload


def register_cli_args(
    incident_id: str | None,
    raw_text: str,
    created_at: datetime,
    *,
    title: str = "Fallo de pasarela de pagos",
    status: str | None = None,
) -> list[str]:
    args = ["register", "--title", title, "--raw-text", raw_text]
    if incident_id is not None:
        args.extend(["--incident-id", incident_id])
    args.extend(["--created-at", created_at.isoformat()])
    if status is not None:
        args.extend(["--status", status])
    return args


def sla_args(incident_id: str, reference_time: datetime) -> list[str]:
    return ["sla", incident_id, "--reference-time", reference_time.isoformat()]


def test_bdd_scenario_1_minimal_registration_and_rest_cli_parity(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given solo título y texto, When se registra en REST y CLI, Then coinciden y se puede consultar."""
    minimal = client.post(
        "/api/v1/incidents",
        json={"title": "Fallo mínimo", "raw_text": P0_RAW},
    )
    assert minimal.status_code == 201
    body = minimal.json()
    assert set(body) == {"incident", "duplicate_incident_ids"}
    snapshot = body["incident"]
    assert set(snapshot) == SNAPSHOT_KEYS
    assert re.fullmatch(r"INC-[0-9A-F]{8}", snapshot["incident_id"])
    assert snapshot["status"] == "OPEN"
    assert snapshot["severity"] == "P0"
    assert snapshot["duplicate_group_key"] == duplicate_key(P0_RAW)
    assert datetime.fromisoformat(snapshot["created_at"]).tzinfo is None
    assert "raw_text" not in snapshot

    retrieved = client.get(f"/api/v1/incidents/{snapshot['incident_id']}")
    assert retrieved.status_code == 200
    assert retrieved.json() == snapshot

    rest_stack = build_stack()
    cli_stack = build_stack()
    created_at = datetime(2026, 11, 24, 10)
    payload = register_payload("INC-00002001", P0_RAW, created_at)
    with TestClient(rest_stack.api) as rest_client:
        rest = rest_client.post("/api/v1/incidents", json=payload)
    cli = cli_runner.invoke(
        cli_stack.cli,
        register_cli_args("INC-00002001", P0_RAW, created_at),
    )
    cli_show = cli_runner.invoke(cli_stack.cli, ["show", "INC-00002001"])
    assert rest.status_code == 201
    assert cli.exit_code == 0
    assert cli_show.exit_code == 0
    assert rest.json() == json.loads(cli.stdout)
    assert json.loads(cli_show.stdout) == rest.json()["incident"]


def test_bdd_scenario_2_duplicate_warning_by_key(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given equivalentes en tres estados y uno resuelto, When se registra, Then el aviso coincide."""
    cli_stack = build_stack()
    key = duplicate_key(P0_RAW)
    base = datetime(2026, 11, 24, 8)
    for candidate_stack in (stack, cli_stack):
        seed_incident(candidate_stack.repository, "INC-00000001", P0_RAW, "OPEN", base)
        seed_incident(
            candidate_stack.repository, "INC-00000002", P0_RAW, "IN_PROGRESS", base
        )
        seed_incident(
            candidate_stack.repository,
            "INC-00000003",
            P0_RAW,
            "ESCALATION_REQUIRED",
            base,
        )
        seed_incident(
            candidate_stack.repository,
            "INC-00000004",
            P0_RAW,
            "RESOLVED",
            base,
        )

    created_at = datetime(2026, 11, 24, 12)
    payload = register_payload("INC-00002002", P0_RAW, created_at)
    response = client.post("/api/v1/incidents", json=payload)
    result = cli_runner.invoke(
        cli_stack.cli,
        register_cli_args("INC-00002002", P0_RAW, created_at),
    )

    expected = ["INC-00000001", "INC-00000002", "INC-00000003"]
    assert response.status_code == 201
    assert result.exit_code == 0
    assert response.json()["duplicate_incident_ids"] == expected
    assert json.loads(result.stdout)["duplicate_incident_ids"] == expected
    assert json.loads(result.stdout) == response.json()
    assert "INC-00000004" not in expected
    assert "INC-00002002" not in response.json()["duplicate_incident_ids"]
    assert key == "payments-gateway:http-502-outage"


def test_bdd_scenario_3_continuous_p0_sla(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given un P0 abierto desde las 10:00, When se consulta a las 11:01, Then incumple y escala."""
    created_at = datetime(2026, 11, 23, 10)
    reference_time = datetime(2026, 11, 23, 11, 1)
    registered = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002003", P0_RAW, created_at),
    )
    assert registered.status_code == 201

    response = client.get(
        "/api/v1/incidents/INC-00002003/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(
        stack.cli, sla_args("INC-00002003", reference_time)
    )
    assert response.status_code == 200
    assert result.exit_code == 0
    assert set(response.json()) == SLA_KEYS
    assert json.loads(result.stdout) == response.json()
    assert response.json() == {
        "incident_id": "INC-00002003",
        "reference_time": reference_time.isoformat(),
        "effective_time": reference_time.isoformat(),
        "elapsed_minutes": 61,
        "allowed_minutes": 60,
        "remaining_minutes": -1,
        "is_breached": True,
        "requires_escalation": True,
    }


def test_bdd_scenario_4_p2_exact_limit_is_not_breached(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given un P2 desde el lunes a las 08:00, When se consulta a las 16:00, Then no incumple."""
    created_at = datetime(2026, 11, 9, 8)
    reference_time = datetime(2026, 11, 9, 16)
    registered = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002004", P2_RAW, created_at),
    )
    assert registered.status_code == 201

    response = client.get(
        "/api/v1/incidents/INC-00002004/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(
        stack.cli, sla_args("INC-00002004", reference_time)
    )
    assert response.status_code == 200
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()
    assert response.json()["elapsed_minutes"] == 480
    assert response.json()["allowed_minutes"] == 480
    assert response.json()["remaining_minutes"] == 0
    assert response.json()["is_breached"] is False
    assert response.json()["requires_escalation"] is True


def test_bdd_scenario_5_p2_weekend_business_hours_parity(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    """Given un P2 desde el viernes a las 17:00, When se consulta el lunes a las 09:00, Then coinciden."""
    created_at = datetime(2026, 11, 6, 17)
    reference_time = datetime(2026, 11, 9, 9)
    registered = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002005", P2_RAW, created_at),
    )
    assert registered.status_code == 201

    response = client.get(
        "/api/v1/incidents/INC-00002005/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(
        stack.cli, sla_args("INC-00002005", reference_time)
    )
    assert response.status_code == 200
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()
    assert response.json() == {
        "incident_id": "INC-00002005",
        "reference_time": reference_time.isoformat(),
        "effective_time": reference_time.isoformat(),
        "elapsed_minutes": 120,
        "allowed_minutes": 480,
        "remaining_minutes": 360,
        "is_breached": False,
        "requires_escalation": False,
    }


def test_us1_duplicate_id_is_rejected_without_overwriting(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    created_at = datetime(2026, 11, 24, 9)
    first = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002006", P0_RAW, created_at, title="Original"),
    )
    second = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002006", P2_RAW, created_at, title="Reemplazo"),
    )
    cli = cli_runner.invoke(
        stack.cli,
        register_cli_args("INC-00002006", P2_RAW, created_at, title="Reemplazo CLI"),
    )
    stored = client.get("/api/v1/incidents/INC-00002006")

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "incident_id ya existe: INC-00002006."}
    assert cli.exit_code == 1
    assert cli.stdout == ""
    assert "incident_id ya existe: INC-00002006." in cli.stderr
    assert stored.status_code == 200
    assert stored.json()["title"] == "Original"


@pytest.mark.parametrize(
    ("payload", "cli_args", "expected_error"),
    [
        (
            {"raw_text": P0_RAW},
            ["register", "--raw-text", P0_RAW],
            REQUIRED_FIELDS_ERROR,
        ),
        (
            {"title": "Sin texto", "raw_text": "   "},
            ["register", "--title", "Sin texto", "--raw-text", "   "],
            REQUIRED_FIELDS_ERROR,
        ),
        (
            {
                "title": "Estado inválido",
                "raw_text": P0_RAW,
                "status": "ESCALATION_REQUIRED",
            },
            [
                "register",
                "--title",
                "Estado inválido",
                "--raw-text",
                P0_RAW,
                "--status",
                "ESCALATION_REQUIRED",
            ],
            INVALID_INITIAL_STATUS_ERROR,
        ),
        (
            {
                "title": "ID inválido",
                "raw_text": P0_RAW,
                "incident_id": "INC-1",
            },
            [
                "register",
                "--title",
                "ID inválido",
                "--raw-text",
                P0_RAW,
                "--incident-id",
                "INC-1",
            ],
            INVALID_INCIDENT_ID_ERROR,
        ),
    ],
)
def test_us1_rejects_invalid_registration_inputs_in_both_channels(
    client: TestClient,
    cli_runner: CliRunner,
    stack: SimpleNamespace,
    payload: dict[str, str],
    cli_args: list[str],
    expected_error: str,
) -> None:
    response = client.post("/api/v1/incidents", json=payload)
    result = cli_runner.invoke(stack.cli, cli_args)
    assert response.status_code == 422
    assert response.json() == {"detail": expected_error}
    assert result.exit_code == 1
    assert result.stdout == ""
    assert expected_error in result.stderr


def test_us1_severity_is_derived_from_text_and_ids_are_valid(
    client: TestClient, cli_runner: CliRunner
) -> None:
    created_at = datetime(2026, 11, 24, 11)
    explicit = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002007", P1_RAW, created_at),
    )
    generated = client.post(
        "/api/v1/incidents",
        json=register_payload(None, P1_RAW, created_at),
    )
    cli_generated = cli_runner.invoke(
        build_stack().cli,
        register_cli_args(None, P1_RAW, created_at),
    )

    assert explicit.status_code == 201
    assert explicit.json()["incident"]["incident_id"] == "INC-00002007"
    assert explicit.json()["incident"]["severity"] == "P1"
    assert generated.status_code == 201
    assert re.fullmatch(
        r"INC-[0-9A-F]{8}", generated.json()["incident"]["incident_id"]
    )
    assert generated.json()["incident"]["severity"] == "P1"
    assert cli_generated.exit_code == 0
    assert re.fullmatch(
        r"INC-[0-9A-F]{8}",
        json.loads(cli_generated.stdout)["incident"]["incident_id"],
    )


def test_us2_escalated_equivalent_warns_and_same_title_other_key_does_not(
    client: TestClient, stack: SimpleNamespace
) -> None:
    base = datetime(2026, 11, 24, 8)
    seed_incident(
        stack.repository,
        "INC-00000010",
        P0_RAW,
        "ESCALATION_REQUIRED",
        base,
        title="Título compartido",
    )
    seed_incident(
        stack.repository,
        "INC-00000011",
        P2_EXPORT_RAW,
        "OPEN",
        base,
        title="Título compartido",
    )
    seed_incident(
        stack.repository,
        "INC-00000012",
        P0_RAW,
        "RESOLVED",
        base,
        title="Título compartido",
    )

    response = client.post(
        "/api/v1/incidents",
        json=register_payload(
            "INC-00002008",
            P0_RAW,
            datetime(2026, 11, 24, 12),
            title="Título compartido",
        ),
    )
    assert response.status_code == 201
    assert response.json()["duplicate_incident_ids"] == ["INC-00000010"]


def test_us2_empty_warning_and_self_exclusion(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    created_at = datetime(2026, 11, 24, 9)
    response = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002009", P0_RAW, created_at),
    )
    result = cli_runner.invoke(
        build_stack().cli, register_cli_args("INC-00002010", P0_RAW, created_at)
    )
    assert response.status_code == 201
    assert response.json()["duplicate_incident_ids"] == []
    assert result.exit_code == 0
    assert json.loads(result.stdout)["duplicate_incident_ids"] == []
    assert "INC-00002009" not in response.json()["duplicate_incident_ids"]
    assert "INC-00002010" not in response.json()["duplicate_incident_ids"]


def test_us3_resolved_at_takes_precedence(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    created_at = datetime(2026, 11, 6, 17)
    resolved_at = datetime(2026, 11, 9, 9)
    reference_time = datetime(2026, 11, 9, 14)
    seed_incident(
        stack.repository,
        "INC-00002011",
        P2_RAW,
        "RESOLVED",
        created_at,
        resolved_at=resolved_at,
    )

    response = client.get(
        "/api/v1/incidents/INC-00002011/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(stack.cli, sla_args("INC-00002011", reference_time))
    assert response.status_code == 200
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()
    assert response.json()["effective_time"] == resolved_at.isoformat()
    assert response.json()["elapsed_minutes"] == 120
    assert response.json()["remaining_minutes"] == 360
    assert response.json()["is_breached"] is False
    assert response.json()["requires_escalation"] is False


@pytest.mark.parametrize(
    "reference_time",
    ["not-a-date", "2026-11-23T12:00:00+00:00", "2026-11-23T09:59:59"],
)
def test_us3_rejects_invalid_reference_time(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace, reference_time: str
) -> None:
    created_at = datetime(2026, 11, 23, 10)
    client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002012", P0_RAW, created_at),
    )
    response = client.get(
        "/api/v1/incidents/INC-00002012/sla",
        params={"reference_time": reference_time},
    )
    result = cli_runner.invoke(
        stack.cli, ["sla", "INC-00002012", "--reference-time", reference_time]
    )
    assert response.status_code == 422
    assert response.json() == {"detail": REFERENCE_TIME_ERROR}
    assert result.exit_code == 1
    assert result.stdout == ""
    assert REFERENCE_TIME_ERROR in result.stderr


def test_us3_unknown_incident_is_reported_in_both_channels(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    expected = INCIDENT_NOT_FOUND_ERROR.format(incident_id="INC-0000FFFF")
    reference_time = datetime(2026, 11, 23, 12)
    response = client.get(
        "/api/v1/incidents/INC-0000FFFF/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    show_response = client.get("/api/v1/incidents/INC-0000FFFF")
    result = cli_runner.invoke(stack.cli, sla_args("INC-0000FFFF", reference_time))
    show_result = cli_runner.invoke(stack.cli, ["show", "INC-0000FFFF"])

    assert response.status_code == 404
    assert show_response.status_code == 404
    assert response.json() == {"detail": expected}
    assert show_response.json() == {"detail": expected}
    assert result.exit_code == 1
    assert show_result.exit_code == 1
    assert result.stdout == ""
    assert show_result.stdout == ""
    assert expected in result.stderr
    assert expected in show_result.stderr


def test_us3_escalation_starts_at_75_percent_without_breach(
    client: TestClient, cli_runner: CliRunner, stack: SimpleNamespace
) -> None:
    created_at = datetime(2026, 11, 9, 8)
    reference_time = datetime(2026, 11, 9, 14)
    client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002013", P2_RAW, created_at),
    )
    response = client.get(
        "/api/v1/incidents/INC-00002013/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    result = cli_runner.invoke(stack.cli, sla_args("INC-00002013", reference_time))
    assert response.status_code == 200
    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()
    assert response.json()["elapsed_minutes"] == 360
    assert response.json()["remaining_minutes"] == 120
    assert response.json()["is_breached"] is False
    assert response.json()["requires_escalation"] is True


def test_sc005_registration_warning_and_sla_are_single_interactions_under_30s(
    client: TestClient, stack: SimpleNamespace
) -> None:
    seed_incident(
        stack.repository,
        "INC-00000020",
        P0_RAW,
        "OPEN",
        datetime(2026, 11, 24, 8),
    )
    created_at = datetime(2026, 11, 24, 10)
    reference_time = datetime(2026, 11, 24, 10, 1)

    started = time.perf_counter()
    registration = client.post(
        "/api/v1/incidents",
        json=register_payload("INC-00002014", P0_RAW, created_at),
    )
    registration_elapsed = time.perf_counter() - started
    assert registration.status_code == 201
    assert registration_elapsed < 30

    started = time.perf_counter()
    warning = registration.json()["duplicate_incident_ids"]
    warning_elapsed = time.perf_counter() - started
    assert warning == ["INC-00000020"]
    assert warning_elapsed < 30

    started = time.perf_counter()
    sla = client.get(
        "/api/v1/incidents/INC-00002014/sla",
        params={"reference_time": reference_time.isoformat()},
    )
    sla_elapsed = time.perf_counter() - started
    assert sla.status_code == 200
    assert sla_elapsed < 30


def test_sc006_complete_warning_with_one_thousand_equivalents(
    cli_runner: CliRunner,
) -> None:
    rest_stack = build_stack()
    cli_stack = build_stack()
    base = datetime(2026, 11, 24, 8)
    statuses = ["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED"]
    expected_ids: list[str] = []
    for index in range(1000):
        incident_id = f"INC-{index:08X}"
        expected_ids.append(incident_id)
        for candidate_stack in (rest_stack, cli_stack):
            seed_incident(
                candidate_stack.repository,
                incident_id,
                P0_RAW,
                statuses[index % len(statuses)],
                base,
                title=f"Equivalente {index}",
            )
    for candidate_stack in (rest_stack, cli_stack):
        seed_incident(
            candidate_stack.repository,
            "INC-FFFFFFFF",
            P0_RAW,
            "RESOLVED",
            base,
            title="Resuelto",
        )

    created_at = datetime(2026, 11, 24, 12)
    with TestClient(rest_stack.api) as rest_client:
        response = rest_client.post(
            "/api/v1/incidents",
            json=register_payload("INC-10000000", P0_RAW, created_at),
        )
    result = cli_runner.invoke(
        cli_stack.cli, register_cli_args("INC-10000000", P0_RAW, created_at)
    )

    expected_ids.sort()
    rest_warning = response.json()["duplicate_incident_ids"]
    cli_warning = json.loads(result.stdout)["duplicate_incident_ids"]
    assert response.status_code == 201
    assert result.exit_code == 0
    assert len(rest_warning) == 1000
    assert rest_warning == expected_ids
    assert rest_warning == cli_warning
    assert len(set(rest_warning)) == 1000
    assert "INC-FFFFFFFF" not in rest_warning
    assert "INC-10000000" not in rest_warning
