"""Esquemas REST del ciclo de vida de incidentes y del estado de SLA."""

from typing import Literal

from pydantic import BaseModel

from src.domain.models import IncidentStatus, SeverityLevel


class HealthResponseModel(BaseModel):
    """Cuerpo exacto compartido por el endpoint de verificación."""

    status: Literal["ok", "error"]
    database: Literal["connected", "unavailable"]


class RegistrationRequestModel(BaseModel):
    """Entrada opcional del alta; los campos obligatorios se validan en el servicio."""

    title: str | None = None
    raw_text: str | None = None
    incident_id: str | None = None
    created_at: str | None = None
    status: str | None = None


class IncidentSnapshotModel(BaseModel):
    """Vista estable de un incidente, sin texto crudo."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: str
    duplicate_group_key: str


class RegistrationResponseModel(BaseModel):
    """Confirmación de registro con aviso de equivalentes."""

    incident: IncidentSnapshotModel
    duplicate_incident_ids: list[str]


class SLAStatusResponseModel(BaseModel):
    """Estado de SLA compartido con la CLI."""

    incident_id: str
    reference_time: str
    effective_time: str
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool


class SummaryDetailModel(BaseModel):
    """Fila observable del detalle del resumen."""

    title: str
    component: str
    severity: SeverityLevel
    status: Literal["OPEN", "IN_PROGRESS"]
    elapsed_minutes: int
    requires_escalation: bool


class SummaryResponseModel(BaseModel):
    """Respuesta compartida por el endpoint de resumen."""

    reference_time: str
    component_filter: str | None
    total_active: int
    breached_count: int
    details: list[SummaryDetailModel]
