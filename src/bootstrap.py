"""Raíz de composición que ensambla los adaptadores con el caso de uso."""

import os
from urllib.parse import urlparse

from src.adapters.outbound.sqlite_repository import create_incident_repository
from src.application.ports import IncidentRepositoryPort
from src.application.services import IncidentService


def resolve_incident_repository(
    database_url: str | None,
) -> IncidentRepositoryPort | None:
    """Resuelve el adaptador de salida seleccionado por ``DATABASE_URL``."""
    if database_url is None or not database_url.strip():
        return create_incident_repository()
    value = database_url.strip()
    scheme = urlparse(value).scheme.lower()
    if scheme == "sqlite":
        return create_incident_repository(value)
    if scheme == "postgresql":
        from src.adapters.outbound.postgres_repository import create_postgres_repository

        return create_postgres_repository(value)
    return None


def build_incident_service(
    repository: IncidentRepositoryPort | None = None,
) -> IncidentService:
    """Construye el servicio con el repositorio configurado por entorno."""
    selected = (
        repository
        if repository is not None
        else resolve_incident_repository(os.environ.get("DATABASE_URL"))
    )
    return IncidentService(selected)
