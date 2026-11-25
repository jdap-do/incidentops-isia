"""Casos de uso compartidos por los adaptadores de IncidentOps."""

import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, cast

from src.application.ports import IncidentRepositoryPort
from src.domain.models import (
    ActiveIncidentDetail,
    ActiveIncidentSummary,
    DUPLICATE_NOTIFICATION_STATUSES,
    Incident,
    IncidentStatus,
    RegistrationStatus,
    SeverityLevel,
    TriageResult,
    normalize_component,
)
from src.domain.sla_calculator import evaluate_sla_status, get_sla_rule_for_severity
from src.domain.triage_rules import classify_incident_report

REFERENCE_TIME_ERROR = (
    "reference_time debe ser una fecha ISO-8601 local naive y no puede ser anterior "
    "a created_at de un incidente devuelto."
)
CREATED_AT_ERROR = "created_at debe ser una fecha ISO-8601 local naive."
REQUIRED_FIELDS_ERROR = "title y raw_text son obligatorios y no pueden estar vacíos."
INVALID_INCIDENT_ID_ERROR = "incident_id debe estar vacío o tener formato INC-<HEX8>."
INVALID_INITIAL_STATUS_ERROR = "status debe ser OPEN o IN_PROGRESS si se proporciona."
INCIDENT_NOT_FOUND_ERROR = "incidente no encontrado: {incident_id}."

_INCIDENT_ID_PATTERN = re.compile(r"INC-[0-9A-Fa-f]{8}")
_INITIAL_STATUSES: frozenset[str] = frozenset({"OPEN", "IN_PROGRESS"})


class InvalidTriageInput(ValueError):
    """Campos obligatorios ausentes para clasificar un reporte."""


class InvalidRegistrationInput(ValueError):
    """Campos inválidos para registrar un incidente."""


class InvalidCreatedAt(ValueError):
    """Fecha de creación inválida para registrar un incidente."""


class InvalidReferenceTime(ValueError):
    """Instante de referencia inválido para evaluar el resumen."""


class DuplicateIncidentId(ValueError):
    """El identificador proporcionado ya pertenece a otro incidente."""

    def __init__(self, incident_id: str) -> None:
        super().__init__(f"incident_id ya existe: {incident_id}.")


class IncidentNotFound(LookupError):
    """No existe un incidente con el identificador solicitado."""

    def __init__(self, incident_id: str) -> None:
        super().__init__(INCIDENT_NOT_FOUND_ERROR.format(incident_id=incident_id))


class RepositoryNotConfigured(RuntimeError):
    """El caso de uso requiere un repositorio inyectado."""


@dataclass(frozen=True)
class RegistrationInput:
    """Entrada observable del caso de uso de registro."""

    title: str | None
    raw_text: str | None
    incident_id: str | None = None
    created_at: datetime | None = None
    status: str | None = None


@dataclass(frozen=True)
class IncidentSnapshot:
    """Vista estable expuesta por REST y CLI."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: str
    duplicate_group_key: str

    @classmethod
    def from_incident(cls, incident: Incident) -> "IncidentSnapshot":
        return cls(
            incident_id=incident.incident_id,
            title=incident.title,
            component=incident.component,
            severity=incident.severity,
            status=incident.status,
            created_at=incident.created_at.isoformat(),
            duplicate_group_key=incident.duplicate_group_key,
        )


@dataclass(frozen=True)
class RegistrationResult:
    """Confirmación de registro y aviso de equivalentes."""

    incident: IncidentSnapshot
    duplicate_incident_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReferenceTime:
    """Instante resuelto por el adaptador y pasado al servicio."""

    raw: str | None
    value: datetime
    invalid_message: str = REFERENCE_TIME_ERROR

    @property
    def serialized(self) -> str:
        return self.value.isoformat()


@dataclass(frozen=True)
class DuplicateGroupKey:
    """Clave de equivalencia y estados que participan en el aviso."""

    value: str
    open_statuses: frozenset[IncidentStatus] = DUPLICATE_NOTIFICATION_STATUSES
    excluded_id: str | None = None


@dataclass(frozen=True)
class SLAStatusResult:
    """Estado de SLA compartido por REST y CLI."""

    incident_id: str
    reference_time: str
    effective_time: str
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool


@dataclass(frozen=True)
class HealthStatusResult:
    """Resultado de disponibilidad compartido por REST y CLI."""

    status: Literal["ok", "error"]
    database: Literal["connected", "unavailable"]

    @property
    def healthy(self) -> bool:
        return self.status == "ok" and self.database == "connected"


HEALTH_SUCCESS = HealthStatusResult(status="ok", database="connected")
HEALTH_FAILURE = HealthStatusResult(status="error", database="unavailable")


def _is_naive(value: datetime) -> bool:
    return value.tzinfo is None and value.utcoffset() is None


def parse_reference_time(raw: str | None, *, resolved_now: datetime) -> datetime:
    """Valida ISO-8601 local naive o devuelve el instante capturado por el adaptador."""
    if raw is None or not raw.strip():
        return resolved_now
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError as exc:
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR) from exc
    if not _is_naive(parsed):
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)
    return parsed


def parse_created_at(raw: str | None, *, resolved_now: datetime) -> datetime:
    """Valida ISO-8601 local naive o devuelve el instante capturado por el adaptador."""
    if raw is None or not raw.strip():
        return resolved_now
    try:
        parsed = datetime.fromisoformat(raw.strip())
    except ValueError as exc:
        raise InvalidCreatedAt(CREATED_AT_ERROR) from exc
    if not _is_naive(parsed):
        raise InvalidCreatedAt(CREATED_AT_ERROR)
    return parsed


def validate_reference_time(reference_time: datetime, incidents: Sequence[Incident]) -> None:
    """Rechaza instantes con zona horaria o anteriores a algún incidente mostrado."""
    if not _is_naive(reference_time):
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)
    if any(reference_time < incident.created_at for incident in incidents):
        raise InvalidReferenceTime(REFERENCE_TIME_ERROR)


def _require_repository(self: "IncidentService") -> IncidentRepositoryPort:
    if self._repository is None:
        raise RepositoryNotConfigured("IncidentService requiere un repositorio inyectado.")
    return self._repository


def _resolve_incident_id(
    requested_id: str | None, repository: IncidentRepositoryPort
) -> str:
    if requested_id is None:
        for _ in range(32):
            candidate = f"INC-{secrets.token_hex(4).upper()}"
            if repository.get_incident(candidate) is None:
                return candidate
        raise InvalidRegistrationInput(INVALID_INCIDENT_ID_ERROR)
    if not _INCIDENT_ID_PATTERN.fullmatch(requested_id):
        raise InvalidRegistrationInput(INVALID_INCIDENT_ID_ERROR)
    if repository.get_incident(requested_id) is not None:
        raise DuplicateIncidentId(requested_id)
    return requested_id


class IncidentService:
    """Orquesta triaje, registro y consultas sin depender de HTTP, CLI ni persistencia."""

    def __init__(self, repository: IncidentRepositoryPort | None = None) -> None:
        self._repository = repository

    def check_database_health(self) -> HealthStatusResult:
        """Devuelve el resultado compartido de disponibilidad de la base configurada."""
        if self._repository is None:
            return HEALTH_FAILURE
        try:
            available = self._repository.check_health()
        except Exception:
            return HEALTH_FAILURE
        return HEALTH_SUCCESS if available else HEALTH_FAILURE

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        """Valida la entrada y delega la clasificación en el dominio."""
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise InvalidTriageInput("incident_id no puede estar vacío.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise InvalidTriageInput("raw_text no puede estar vacío.")
        return classify_incident_report(incident_id, raw_text)

    def register_incident(
        self, request: RegistrationInput, *, registered_at: datetime
    ) -> RegistrationResult:
        """Registra el incidente y devuelve la confirmación con el aviso de equivalentes."""
        repository = _require_repository(self)
        if (
            not isinstance(request.title, str)
            or not request.title.strip()
            or not isinstance(request.raw_text, str)
            or not request.raw_text.strip()
        ):
            raise InvalidRegistrationInput(REQUIRED_FIELDS_ERROR)

        created_at = request.created_at if request.created_at is not None else registered_at
        if not _is_naive(created_at):
            raise InvalidCreatedAt(CREATED_AT_ERROR)

        requested_status = request.status if request.status is not None else "OPEN"
        if requested_status not in _INITIAL_STATUSES:
            raise InvalidRegistrationInput(INVALID_INITIAL_STATUS_ERROR)
        status = cast(RegistrationStatus, requested_status)

        incident_id = _resolve_incident_id(request.incident_id, repository)
        triage = classify_incident_report(incident_id, request.raw_text)
        get_sla_rule_for_severity(triage.severity)
        incident = Incident(
            incident_id=incident_id,
            title=request.title,
            component=triage.component,
            severity=triage.severity,
            status=status,
            created_at=created_at,
            raw_text=request.raw_text,
            duplicate_group_key=triage.duplicate_group_key,
        )
        repository.save_incident(incident)

        duplicate_key = DuplicateGroupKey(
            value=incident.duplicate_group_key, excluded_id=incident.incident_id
        )
        candidates = repository.find_open_duplicates(
            incident, exclude_incident_id=duplicate_key.excluded_id
        )
        duplicate_ids = sorted(
            {
                candidate.incident_id
                for candidate in candidates
                if candidate.incident_id != incident.incident_id
                and candidate.status in duplicate_key.open_statuses
                and candidate.duplicate_group_key == duplicate_key.value
            }
        )
        return RegistrationResult(
            incident=IncidentSnapshot.from_incident(incident),
            duplicate_incident_ids=duplicate_ids,
        )

    def get_incident(self, incident_id: str) -> IncidentSnapshot:
        """Devuelve la vista persistida de un incidente existente."""
        repository = _require_repository(self)
        incident = repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFound(incident_id)
        return IncidentSnapshot.from_incident(incident)

    def get_incident_sla(
        self, incident_id: str, reference_time: datetime | ReferenceTime
    ) -> SLAStatusResult:
        """Evalúa el SLA del incidente con un instante de referencia explícito."""
        repository = _require_repository(self)
        incident = repository.get_incident(incident_id)
        if incident is None:
            raise IncidentNotFound(incident_id)

        reference = (
            reference_time
            if isinstance(reference_time, ReferenceTime)
            else ReferenceTime(raw=None, value=reference_time)
        )
        if not _is_naive(reference.value) or (
            incident.resolved_at is not None and not _is_naive(incident.resolved_at)
        ):
            raise InvalidReferenceTime(reference.invalid_message)
        validate_reference_time(reference.value, [incident])

        evaluation = evaluate_sla_status(incident, reference.value)
        effective_time = incident.resolved_at or reference.value
        return SLAStatusResult(
            incident_id=incident.incident_id,
            reference_time=reference.serialized,
            effective_time=effective_time.isoformat(),
            elapsed_minutes=evaluation.elapsed_minutes,
            allowed_minutes=evaluation.allowed_minutes,
            remaining_minutes=evaluation.remaining_minutes,
            is_breached=evaluation.is_breached,
            requires_escalation=evaluation.requires_escalation,
        )

    def get_active_incidents_summary(
        self, component_filter: str | None, reference_time: datetime
    ) -> ActiveIncidentSummary:
        """Devuelve el resumen activo para un instante explícito y un filtro opcional."""
        repository = _require_repository(self)
        normalized_filter = normalize_component(component_filter)
        incidents = repository.list_active_incidents(normalized_filter)
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
