"""Adaptador SQLite de salida que implementa ``IncidentRepositoryPort``."""

import sqlite3
from datetime import datetime
from typing import cast

from src.application.ports import IncidentRepositoryPort
from src.domain.models import Incident, IncidentStatus, SeverityLevel, normalize_component
from src.domain.sla_calculator import SLA_POLICY_TABLE


class SQLiteIncidentRepository:
    """Persistencia SQLite con filtros en SQL y sin consultas N+1."""

    def __init__(self, database_url: str | None = None) -> None:
        self._database_path = _resolve_database_path(database_url)
        self._connection = sqlite3.connect(self._database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._connection:
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS sla_policies (
                    severity TEXT PRIMARY KEY,
                    max_resolution_minutes INTEGER NOT NULL,
                    operates_24x7 INTEGER NOT NULL
                )
                """
            )
            self._connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    component TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT
                )
                """
            )
            self._connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_incidents_component_status
                ON incidents(component, status, incident_id)
                """
            )
            for rule in SLA_POLICY_TABLE.values():
                self._connection.execute(
                    """
                    INSERT OR REPLACE INTO sla_policies
                    (severity, max_resolution_minutes, operates_24x7)
                    VALUES (?, ?, ?)
                    """,
                    (rule.severity, rule.max_resolution_minutes, 1 if rule.operates_24x7 else 0),
                )

    def save_incident(self, incident: Incident) -> None:
        """Inserta o reemplaza un incidente normalizando su componente."""
        component = normalize_component(incident.component) or incident.component
        with self._connection:
            self._connection.execute(
                """
                INSERT OR REPLACE INTO incidents
                (incident_id, title, component, severity, status, created_at, resolved_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    incident.incident_id,
                    incident.title,
                    component,
                    incident.severity,
                    incident.status,
                    incident.created_at.isoformat(),
                    incident.resolved_at.isoformat() if incident.resolved_at else None,
                ),
            )

    def get_incident(self, incident_id: str) -> Incident | None:
        """Devuelve un incidente por ID o ``None`` si no existe."""
        cursor = self._connection.execute(
            """
            SELECT incident_id, title, component, severity, status, created_at, resolved_at
            FROM incidents WHERE incident_id = ?
            """,
            (incident_id,),
        )
        row = cursor.fetchone()
        return None if row is None else self._row_to_incident(row)

    def find_open_duplicates(
        self, incident: Incident, *, exclude_incident_id: str | None = None
    ) -> list[Incident]:
        """Busca incidentes activos con componente y título equivalentes."""
        component = normalize_component(incident.component) or incident.component
        target_title = " ".join(incident.title.split()).casefold()
        cursor = self._connection.execute(
            """
            SELECT incident_id, title, component, severity, status, created_at, resolved_at
            FROM incidents
            WHERE component = ? AND status IN (?, ?)
            """,
            (component, "OPEN", "IN_PROGRESS"),
        )
        matches: list[Incident] = []
        for row in cursor.fetchall():
            if exclude_incident_id is not None and row["incident_id"] == exclude_incident_id:
                continue
            if " ".join(row["title"].split()).casefold() != target_title:
                continue
            matches.append(self._row_to_incident(row))
        return matches

    def list_active_incidents(
        self, component_filter: str | None = None
    ) -> list[Incident]:
        """Obtiene activos con una sola consulta filtrada y join de políticas."""
        query = """
            SELECT i.incident_id, i.title, i.component, i.severity,
                   i.status, i.created_at, i.resolved_at
            FROM incidents AS i
            INNER JOIN sla_policies AS p ON p.severity = i.severity
            WHERE i.status IN (?, ?)
        """
        parameters: list[str] = ["OPEN", "IN_PROGRESS"]
        normalized_filter = normalize_component(component_filter)
        if normalized_filter is not None:
            query += " AND i.component = ?"
            parameters.append(normalized_filter)
        cursor = self._connection.execute(query, parameters)
        return [self._row_to_incident(row) for row in cursor.fetchall()]

    def check_health(self) -> bool:
        """Comprueba que la conexión SQLite responda."""
        try:
            self._connection.execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return False
        return True

    @staticmethod
    def _row_to_incident(row: sqlite3.Row) -> Incident:
        return Incident(
            incident_id=row["incident_id"],
            title=row["title"],
            component=row["component"],
            severity=cast(SeverityLevel, row["severity"]),
            status=cast(IncidentStatus, row["status"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            resolved_at=(
                datetime.fromisoformat(row["resolved_at"]) if row["resolved_at"] else None
            ),
        )


def _resolve_database_path(database_url: str | None) -> str:
    if database_url is None or not database_url.strip():
        return ":memory:"
    value = database_url.strip()
    if value in {":memory:", "sqlite:///:memory:"}:
        return ":memory:"
    if value.startswith("sqlite:////"):
        return value[len("sqlite:////") - 1 :]
    if value.startswith("sqlite:///"):
        return value[len("sqlite:///") :]
    if "://" in value:
        raise ValueError("Solo se admite SQLite como motor de persistencia.")
    return value


def create_incident_repository(database_url: str | None = None) -> IncidentRepositoryPort:
    """Crea el adaptador SQLite configurado por URL o variable de entorno."""
    import os

    selected_url = database_url if database_url is not None else os.environ.get("DATABASE_URL")
    return SQLiteIncidentRepository(selected_url)
