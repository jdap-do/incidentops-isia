"""Casos de uso compartidos por los adaptadores de IncidentOps."""

from collections.abc import Sequence
from datetime import datetime

from src.application.ports import IncidentRepositoryPort
from src.domain.models import (
    ActiveIncidentDetail,
    ActiveIncidentSummary,
    Incident,
    TriageResult,
    normalize_component,
)
from src.domain.sla_calculator import evaluate_sla_status
from src.domain.triage_rules import classify_incident_report

REFERENCE_TIME_ERROR = (
    "reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior "
    "a created_at de un incidente devuelto."
)


class InvalidTriageInput(ValueError):
    """Campos obligatorios ausentes para clasificar un reporte."""


class InvalidReferenceTime(ValueError):
    """Instante de referencia inválido para evaluar el resumen."""


class RepositoryNotConfigured(RuntimeError):
    """El caso de uso requiere un repositorio inyectado."""


def parse_reference_time(raw: str | None, *, resolved_now: datetime) -> datetime:
    """Valida ISO-8601 local naive o devuelve el instante capturado por el adaptador."""
    if raw is None or not raw.strip():
        return resolved_now
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError as exc:
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR) from exc
    if parsed.tzinfo is not None or parsed.utcoffset() is not None:
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)
    return parsed


def validate_reference_time(reference_time: datetime, incidents: Sequence[Incident]) -> None:
    """Rechaza instantes con zona horaria o anteriores a algún incidente mostrado."""
    if reference_time.tzinfo is not None or reference_time.utcoffset() is not None:
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)
    if any(reference_time < incident.created_at for incident in incidents):
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)


class IncidentService:
    """Orquesta triaje y resumen sin depender de HTTP, CLI ni persistencia concreta."""

    def __init__(self, repository: IncidentRepositoryPort | None = None) -> None:
        self._repository = repository

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        """Valida la entrada y delega la clasificación en el dominio."""
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise InvalidTriageInput("incident_id no puede estar vacío.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise InvalidTriageInput("raw_text no puede estar vacío.")
        return classify_incident_report(incident_id, raw_text)

    def get_active_incidents_summary(
        self, component_filter: str | None, reference_time: datetime
    ) -> ActiveIncidentSummary:
        """Devuelve el resumen activo para un instante explícito y un filtro opcional."""
        if self._repository is None:
            raise RepositoryNotConfigured("IncidentService requiere un repositorio inyectado.")
        normalized_filter = normalize_component(component_filter)
        incidents = self._repository.list_active_incidents(normalized_filter)
        validate_reference_time(reference_time, incidents)

        severity_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        details: list[ActiveIncidentDetail] = []
        breached_count = 0
        for incident in incidents:
            evaluation = evaluate_sla_status(incident, reference_time)
            if evaluation.is_breached:
                breached_count += 1
            details.append(
                ActiveIncidentDetail(
                    title=incident.title,
                    component=incident.component,
                    severity=incident.severity,
                    status="OPEN" if incident.status == "OPEN" else "IN_PROGRESS",
                    elapsed_minutes=evaluation.elapsed_minutes,
                    requires_escalation=evaluation.requires_escalation,
                )
            )
        details.sort(
            key=lambda row: (
                severity_order[row.severity],
                -row.elapsed_minutes,
                row.title,
            )
        )
        return ActiveIncidentSummary(
            reference_time=reference_time.isoformat(),
            component_filter=normalized_filter,
            total_active=len(details),
            breached_count=breached_count,
            details=details,
        )
