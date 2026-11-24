"""Casos de uso compartidos por los adaptadores de IncidentOps."""

from src.domain.models import TriageResult
from src.domain.triage_rules import classify_incident_report


class InvalidTriageInput(ValueError):
    """Campos obligatorios ausentes para clasificar un reporte."""


class IncidentService:
    """Orquesta el triaje sin depender de HTTP, CLI ni persistencia."""

    def triage_incident(self, incident_id: str, raw_text: str) -> TriageResult:
        """Valida la entrada y delega la clasificación en el dominio."""
        if not isinstance(incident_id, str) or not incident_id.strip():
            raise InvalidTriageInput("incident_id no puede estar vacío.")
        if not isinstance(raw_text, str) or not raw_text.strip():
            raise InvalidTriageInput("raw_text no puede estar vacío.")
        return classify_incident_report(incident_id, raw_text)
