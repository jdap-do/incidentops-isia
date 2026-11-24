"""Esquemas REST del resumen de incidentes activos."""

from typing import Literal

from pydantic import BaseModel

from src.domain.models import SeverityLevel


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
