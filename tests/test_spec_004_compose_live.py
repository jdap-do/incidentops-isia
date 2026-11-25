"""Prueba opt-in de arranque real con Docker Compose del Hito 004."""

import json
import os
import shutil
from urllib.request import urlopen

import pytest

SUCCESS_BODY = {"status": "ok", "database": "connected"}


@pytest.mark.compose
def test_compose_live_health() -> None:
    """Given pila levantada, When se consulta /health, Then PostgreSQL está conectado."""
    if os.environ.get("RUN_COMPOSE_TESTS") != "1":
        pytest.skip("opt-in: define RUN_COMPOSE_TESTS=1 para ejecutar Compose")
    if shutil.which("docker") is None:
        pytest.skip("Docker no está disponible")

    port = os.environ.get("API_PORT", "8000")
    with urlopen(f"http://localhost:{port}/health", timeout=10) as response:
        assert response.status == 200
        assert json.load(response) == SUCCESS_BODY
