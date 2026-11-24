"""Entidades de dominio y tipos de datos para IncidentOps."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional

SeverityLevel = Literal["P0", "P1", "P2", "P3"]
IncidentStatus = Literal["OPEN", "IN_PROGRESS", "ESCALATION_REQUIRED", "RESOLVED"]


@dataclass(frozen=True)
class SLARule:
    """Acuerdo de nivel de servicio para una severidad."""

    severity: SeverityLevel
    max_resolution_minutes: int
    operates_24x7: bool
    escalation_threshold_ratio: float = 0.75


@dataclass
class Incident:
    """Incidente registrado en IncidentOps."""

    incident_id: str
    title: str
    component: str
    severity: SeverityLevel
    status: IncidentStatus
    created_at: datetime
    resolved_at: Optional[datetime] = None


@dataclass(frozen=True)
class SLAEvaluation:
    """Resultado determinista de la evaluación de SLA."""

    incident_id: str
    severity: SeverityLevel
    elapsed_minutes: int
    allowed_minutes: int
    remaining_minutes: int
    is_breached: bool
    requires_escalation: bool


@dataclass(frozen=True)
class TriageResult:
    """Resultado del triaje determinista.

    consistency_ratio conserva su valor predeterminado por compatibilidad.
    duplicate_group_key representa una correlación candidata.
    """

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float = 1.0
    recommended_team: str = "Backend-Core"
    duplicate_group_key: str = "unknown:unclassified"
