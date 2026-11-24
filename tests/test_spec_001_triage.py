"""Pruebas de aceptación de la especificación 001: triaje manual HTTP y CLI."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from src.adapters.inbound.api import app as api_app
from src.adapters.inbound.cli import app as cli_app

SAMPLE_DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "sample_incidents.json"


@pytest.fixture(scope="module")
def incidents() -> dict[str, str]:
    rows = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    return {row["id"]: row["raw_text"] for row in rows}


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(api_app) as test_client:
        yield test_client


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


def test_http_triage_payment_outage_502(client: TestClient, incidents: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": "INC-1001", "raw_text": incidents["INC-1001"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "incident_id": "INC-1001",
        "severity": "P0",
        "component": "payments-gateway",
        "rationale": "El reporte indica un fallo en el servicio crítico de pagos.",
        "consistency_ratio": 1.0,
        "recommended_team": "Backend-Core",
        "duplicate_group_key": "payments-gateway:http-502-outage",
    }


def test_http_triage_locked_account_with_hoy(client: TestClient, incidents: dict[str, str]) -> None:
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": "INC-1002", "raw_text": incidents["INC-1002"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["severity"] == "P2"
    assert body["recommended_team"] == "Security-IAM"
    assert body["duplicate_group_key"] == "auth-identity:account-lockout"


@pytest.mark.parametrize(
    ("incident_id", "raw_text"),
    [("", "Reporte de prueba"), ("INC-1002", "   ")],
)
def test_http_rejects_blank_fields(
    client: TestClient, incident_id: str, raw_text: str
) -> None:
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": incident_id, "raw_text": raw_text},
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": f"{'incident_id' if not incident_id.strip() else 'raw_text'} no puede estar vacío."
    }


def test_cli_returns_same_json_as_http(
    client: TestClient, cli_runner: CliRunner, incidents: dict[str, str]
) -> None:
    response = client.post(
        "/api/v1/incidents/triage",
        json={"incident_id": "INC-1001", "raw_text": incidents["INC-1001"]},
    )

    result = cli_runner.invoke(
        cli_app,
        ["triage", "--incident-id", "INC-1001", "--raw-text", incidents["INC-1001"]],
    )

    assert result.exit_code == 0
    assert json.loads(result.stdout) == response.json()


@pytest.mark.parametrize(
    ("incident_id", "raw_text"),
    [("", "Reporte de prueba"), ("INC-1002", "   ")],
)
def test_cli_rejects_blank_fields(
    cli_runner: CliRunner, incident_id: str, raw_text: str
) -> None:
    result = cli_runner.invoke(
        cli_app,
        ["triage", "--incident-id", incident_id, "--raw-text", raw_text],
    )

    assert result.exit_code == 1
    assert result.stdout == ""
