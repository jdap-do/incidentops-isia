"""Aplicación FastAPI para triaje, ciclo de vida de incidentes y SLA."""

from dataclasses import asdict
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.application.services import (
    DuplicateIncidentId,
    IncidentNotFound,
    IncidentService,
    InvalidCreatedAt,
    InvalidReferenceTime,
    InvalidRegistrationInput,
    InvalidTriageInput,
    ReferenceTime,
    RegistrationInput,
    parse_created_at,
    parse_reference_time,
)
from src.bootstrap import build_incident_service
from src.domain.models import SeverityLevel

from .schemas import (
    HealthResponseModel,
    IncidentSnapshotModel,
    RegistrationRequestModel,
    RegistrationResponseModel,
    SLAStatusResponseModel,
    SummaryResponseModel,
)


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

    @application.get("/health", response_model=HealthResponseModel)
    def health() -> JSONResponse:
        """Devuelve el resultado exacto de la verificación compartida."""
        result = service.check_database_health()
        return JSONResponse(
            status_code=200 if result.healthy else 503,
            content={"status": result.status, "database": result.database},
        )

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

    @application.post(
        "/api/v1/incidents",
        response_model=RegistrationResponseModel,
        status_code=201,
    )
    def register_incident(request: RegistrationRequestModel) -> RegistrationResponseModel:
        """Registra un incidente y devuelve la confirmación compartida."""
        captured_at = datetime.now()
        try:
            created_at = parse_created_at(
                request.created_at, resolved_now=captured_at
            )
            result = service.register_incident(
                RegistrationInput(
                    title=request.title,
                    raw_text=request.raw_text,
                    incident_id=request.incident_id,
                    created_at=created_at,
                    status=request.status,
                ),
                registered_at=captured_at,
            )
        except (InvalidRegistrationInput, InvalidCreatedAt) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except DuplicateIncidentId as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return RegistrationResponseModel(**asdict(result))

    @application.get("/api/v1/incidents/{incident_id}", response_model=IncidentSnapshotModel)
    def show_incident(incident_id: str) -> IncidentSnapshotModel:
        """Devuelve la vista persistida de un incidente."""
        try:
            result = service.get_incident(incident_id)
        except IncidentNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return IncidentSnapshotModel(**asdict(result))

    @application.get(
        "/api/v1/incidents/{incident_id}/sla",
        response_model=SLAStatusResponseModel,
    )
    def incident_sla(
        incident_id: str, reference_time: str | None = None
    ) -> SLAStatusResponseModel:
        """Captura o valida la referencia y devuelve el estado de SLA."""
        try:
            captured_at = datetime.now()
            parsed_reference = parse_reference_time(
                reference_time, resolved_now=captured_at
            )
            reference = ReferenceTime(raw=reference_time, value=parsed_reference)
            result = service.get_incident_sla(incident_id, reference)
        except IncidentNotFound as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except InvalidReferenceTime as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return SLAStatusResponseModel(**asdict(result))

    return application


app = create_api_app(build_incident_service())
