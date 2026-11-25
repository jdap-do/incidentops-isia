"""Pruebas estáticas del contrato Docker Compose del Hito 004."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ROOT / "compose.yaml"


def service_block(text: str, service: str) -> str:
    lines = text.splitlines()
    start = next(index for index, line in enumerate(lines) if line.strip() == f"{service}:")
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if line.startswith("  ") and not line.startswith("    ") and line.strip().endswith(":"):
            end = index
            break
    return "\n".join(lines[start:end])


def test_compose_contract_static() -> None:
    """Given compose.yaml, When se inspecciona, Then db y api cumplen health y orden."""
    text = COMPOSE.read_text(encoding="utf-8")
    db = service_block(text, "db")
    api = service_block(text, "api")

    assert "image: postgres:16-alpine" in db
    assert "postgres_data:/var/lib/postgresql/data" in db
    assert "pg_isready" in db
    assert "build:" in api
    assert "DATABASE_URL: postgresql://" in api
    assert "condition: service_healthy" in api
    assert "/health" in api
