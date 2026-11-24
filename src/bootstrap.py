"""Raíz de composición que ensambla los adaptadores con el caso de uso."""

from src.adapters.outbound.sqlite_repository import create_incident_repository
from src.application.ports import IncidentRepositoryPort
from src.application.services import IncidentService


def build_incident_service(
    repository: IncidentRepositoryPort | None = None,
) -> IncidentService:
    """Construye el servicio con el repositorio SQLite configurado."""
    return IncidentService(repository or create_incident_repository())
