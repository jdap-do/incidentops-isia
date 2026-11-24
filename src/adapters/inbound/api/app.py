"""Aplicación FastAPI para el triaje manual y el resumen de incidentes."""

from dataclasses import asdict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.application.services import (
    IncidentService,
    InvalidReferenceTime,
    InvalidTriageInput,
    parse_reference_time,
)
from src.bootstrap import build_incident_service
from src.domain.models import SeverityLevel

from .schemas import SummaryResponseModel


class TriageRequest(BaseModel):
    """Solicitud de clasificación manual."""

    incident_id: str
    raw_text: str


class TriageResponse(BaseModel):
    """Resultado de la clasificación manual."""

    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float
    recommended_team: str
    duplicate_group_key: str


def create_api_app(service: IncidentService) -> FastAPI:
    """Construye una API con el servicio inyectado."""
    application = FastAPI(title="IncidentOps Triage API", version="0.1.0")

    @application.post("/api/v1/incidents/triage", response_model=TriageResponse)
    def triage_incident(request: TriageRequest) -> TriageResponse:
        """Delega el triaje en el caso de uso compartido."""
        try:
            result = service.triage_incident(request.incident_id, request.raw_text)
        except InvalidTriageInput as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return TriageResponse(**asdict(result))

    @application.get("/api/v1/incidents/summary", response_model=SummaryResponseModel)
    def incident_summary(
        component: str | None = None,
        reference_time: str | None = None,
    ) -> SummaryResponseModel:
        """Captura o valida el instante y devuelve el resumen del servicio."""
        try:
            resolved_reference = parse_reference_time(
                reference_time, resolved_now=datetime.now()
            )
            result = service.get_active_incidents_summary(component, resolved_reference)
        except InvalidReferenceTime as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return SummaryResponseModel(**asdict(result))

    return application


app = create_api_app(build_incident_service())
