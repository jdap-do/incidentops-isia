"""Puertos de persistencia usados por los casos de uso de IncidentOps."""

from typing import Protocol

from src.domain.models import Incident


class IncidentRepositoryPort(Protocol):
    """Contrato de persistencia que debe implementar todo adaptador de salida."""

    def save_incident(self, incident: Incident) -> None:
        """Inserta un incidente por su identificador sin sobrescribir otro."""
        ...

    def get_incident(self, incident_id: str) -> Incident | None:
        """Devuelve un incidente por identificador o ``None`` si no existe."""
        ...

    def find_open_duplicates(
        self, incident: Incident, *, exclude_incident_id: str | None = None
    ) -> list[Incident]:
        """Devuelve equivalentes no resueltos por ``duplicate_group_key``."""
        ...

    def list_active_incidents(
        self, component_filter: str | None = None
    ) -> list[Incident]:
        """Devuelve incidentes OPEN o IN_PROGRESS, opcionalmente filtrados."""
        ...

    def check_health(self) -> bool:
        """Informa si el adaptador de persistencia está disponible."""
        ...
