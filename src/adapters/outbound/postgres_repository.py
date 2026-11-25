"""Adaptador PostgreSQL de salida que implementa ``IncidentRepositoryPort``."""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import cast

import psycopg

from src.application.ports import IncidentRepositoryPort
from src.application.services import DuplicateIncidentId
from src.domain.models import (
    DUPLICATE_NOTIFICATION_STATUSES,
    Incident,
    IncidentStatus,
    SeverityLevel,
    normalize_component,
)
from src.domain.sla_calculator import SLA_POLICY_TABLE

_INCIDENT_COLUMNS = (
    "incident_id, title, raw_text, component, severity, status, "
    "created_at, resolved_at, duplicate_group_key"
)


class PostgreSQLIncidentRepository:
    """Persistencia PostgreSQL con SQL parametrizado y sin ORM."""

    def __init__(self, database_url: str) -> None:
        self._dsn = database_url
        self._schema_ready = False

    @contextmanager
    def _cursor(self) -> Iterator[object]:
        with psycopg.connect(self._dsn, connect_timeout=5) as connection:
            if not self._schema_ready:
                with connection.cursor() as cursor:
                    self._create_schema(cursor)
            with connection.cursor() as cursor:
                yield cursor
        self._schema_ready = True

    def _create_schema(self, cursor: object) -> None:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sla_policies (
                severity TEXT PRIMARY KEY,
                max_resolution_minutes INTEGER NOT NULL,
                operates_24x7 INTEGER NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                incident_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                raw_text TEXT NOT NULL DEFAULT '',
                component TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                resolved_at TEXT,
                duplicate_group_key TEXT NOT NULL DEFAULT 'unknown:unclassified'
            )
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_component_status
            ON incidents(component, status, incident_id)
            """
        )
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_incidents_duplicate_status
            ON incidents(duplicate_group_key, status, incident_id)
            """
        )
        for rule in SLA_POLICY_TABLE.values():
            cursor.execute(
                """
                INSERT INTO sla_policies
                (severity, max_resolution_minutes, operates_24x7)
                VALUES (%s, %s, %s)
                ON CONFLICT (severity) DO UPDATE SET
                    max_resolution_minutes = EXCLUDED.max_resolution_minutes,
                    operates_24x7 = EXCLUDED.operates_24x7
                """,
                (rule.severity, rule.max_resolution_minutes, 1 if rule.operates_24x7 else 0),
            )

    def save_incident(self, incident: Incident) -> None:
        """Inserta un incidente sin sobrescribir otro identificador."""
        component = normalize_component(incident.component) or incident.component
        try:
            with self._cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO incidents
                    (incident_id, title, raw_text, component, severity, status,
                     created_at, resolved_at, duplicate_group_key)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        incident.incident_id,
                        incident.title,
                        incident.raw_text,
                        component,
                        incident.severity,
                        incident.status,
                        incident.created_at.isoformat(),
                        incident.resolved_at.isoformat() if incident.resolved_at else None,
                        incident.duplicate_group_key,
                    ),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise DuplicateIncidentId(incident.incident_id) from exc

    def get_incident(self, incident_id: str) -> Incident | None:
        """Devuelve un incidente por identificador o ``None`` si no existe."""
        with self._cursor() as cursor:
            cursor.execute(
                f"SELECT {_INCIDENT_COLUMNS} FROM incidents WHERE incident_id = %s",
                (incident_id,),
            )
            row = cursor.fetchone()
        return None if row is None else self._row_to_incident(row)

    def find_open_duplicates(
        self, incident: Incident, *, exclude_incident_id: str | None = None
    ) -> list[Incident]:
        """Busca equivalentes no resueltos por clave de duplicados."""
        statuses = sorted(DUPLICATE_NOTIFICATION_STATUSES)
        placeholders = ", ".join("%s" for _ in statuses)
        query = (
            f"SELECT {_INCIDENT_COLUMNS} FROM incidents "
            f"WHERE duplicate_group_key = %s AND status IN ({placeholders})"
        )
        parameters: list[str] = [incident.duplicate_group_key, *statuses]
        if exclude_incident_id is not None:
            query += " AND incident_id != %s"
            parameters.append(exclude_incident_id)
        query += " ORDER BY incident_id"
        with self._cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            rows = cursor.fetchall()
        return [self._row_to_incident(row) for row in rows]

    def list_active_incidents(
        self, component_filter: str | None = None
    ) -> list[Incident]:
        """Obtiene activos con una sola consulta filtrada y join de políticas."""
        query = """
            SELECT i.incident_id, i.title, i.raw_text, i.component, i.severity,
                   i.status, i.created_at, i.resolved_at, i.duplicate_group_key
            FROM incidents AS i
            INNER JOIN sla_policies AS p ON p.severity = i.severity
            WHERE i.status IN (%s, %s)
        """
        parameters: list[str] = ["OPEN", "IN_PROGRESS"]
        normalized_filter = normalize_component(component_filter)
        if normalized_filter is not None:
            query += " AND i.component = %s"
            parameters.append(normalized_filter)
        with self._cursor() as cursor:
            cursor.execute(query, tuple(parameters))
            rows = cursor.fetchall()
        return [self._row_to_incident(row) for row in rows]

    def check_health(self) -> bool:
        """Comprueba que la conexión PostgreSQL responda a ``SELECT 1``."""
        try:
            with psycopg.connect(self._dsn, connect_timeout=5) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
        except Exception:
            return False
        return True

    @staticmethod
    def _row_to_incident(row: object) -> Incident:
        values = tuple(row)
        return Incident(
            incident_id=values[0],
            title=values[1],
            raw_text=values[2],
            component=values[3],
            severity=cast(SeverityLevel, values[4]),
            status=cast(IncidentStatus, values[5]),
            created_at=datetime.fromisoformat(values[6]),
            resolved_at=(
                datetime.fromisoformat(values[7]) if values[7] is not None else None
            ),
            duplicate_group_key=values[8],
        )


def create_postgres_repository(database_url: str) -> IncidentRepositoryPort:
    """Crea el adaptador PostgreSQL configurado por URL."""
    return PostgreSQLIncidentRepository(database_url)
