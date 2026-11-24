"""Adaptadores outbound de IncidentOps."""

from src.adapters.outbound.sqlite_repository import (
    SQLiteIncidentRepository,
    create_incident_repository,
)

__all__ = ["SQLiteIncidentRepository", "create_incident_repository"]
