"""Aplicación FastAPI para el triaje manual de IncidentOps."""

from dataclasses import asdict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.application.services import IncidentService, InvalidTriageInput
from src.domain.models import SeverityLevel

app = FastAPI(title="IncidentOps Triage API", version="0.1.0")
service = IncidentService()


class TriageRequest(BaseModel):
    incident_id: str
    raw_text: str


class TriageResponse(BaseModel):
    incident_id: str
    severity: SeverityLevel
    component: str
    rationale: str
    consistency_ratio: float
    recommended_team: str
    duplicate_group_key: str


@app.post("/api/v1/incidents/triage", response_model=TriageResponse)
def triage_incident(request: TriageRequest) -> TriageResponse:
    try:
        result = service.triage_incident(request.incident_id, request.raw_text)
    except InvalidTriageInput as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return TriageResponse(**asdict(result))
