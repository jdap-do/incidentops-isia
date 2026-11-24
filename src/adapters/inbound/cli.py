"""Adaptador Typer para triaje, ciclo de vida de incidentes y SLA."""

import json
from dataclasses import asdict
from datetime import datetime

import typer

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


def create_cli_app(service: IncidentService) -> typer.Typer:
    """Construye una CLI con el servicio inyectado."""
    application = typer.Typer(add_completion=False)

    @application.callback()
    def main() -> None:
        """Punto de entrada CLI de IncidentOps."""

    @application.command("triage")
    def triage(
        incident_id: str = typer.Option(..., "--incident-id"),
        raw_text: str = typer.Option(..., "--raw-text"),
    ) -> None:
        """Delega el triaje en el caso de uso compartido."""
        try:
            result = service.triage_incident(incident_id, raw_text)
        except InvalidTriageInput as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps(asdict(result), ensure_ascii=False))

    @application.command("summary")
    def summary(
        component: str | None = typer.Option(None, "--component"),
        reference_time: str | None = typer.Option(None, "--reference-time"),
    ) -> None:
        """Captura o valida el instante y serializa el resumen del servicio."""
        try:
            resolved_reference = parse_reference_time(
                reference_time, resolved_now=datetime.now()
            )
            result = service.get_active_incidents_summary(component, resolved_reference)
        except InvalidReferenceTime as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps(asdict(result), ensure_ascii=False))

    @application.command("register")
    def register(
        title: str = typer.Option("", "--title"),
        raw_text: str = typer.Option("", "--raw-text"),
        incident_id: str | None = typer.Option(None, "--incident-id"),
        created_at: str | None = typer.Option(None, "--created-at"),
        status: str | None = typer.Option(None, "--status"),
    ) -> None:
        """Registra un incidente y muestra la confirmación compartida."""
        captured_at = datetime.now()
        try:
            resolved_created = parse_created_at(created_at, resolved_now=captured_at)
            result = service.register_incident(
                RegistrationInput(
                    title=title,
                    raw_text=raw_text,
                    incident_id=incident_id,
                    created_at=resolved_created,
                    status=status,
                ),
                registered_at=captured_at,
            )
        except (InvalidRegistrationInput, InvalidCreatedAt, DuplicateIncidentId) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps(asdict(result), ensure_ascii=False))

    @application.command("show")
    def show(incident_id: str) -> None:
        """Muestra la vista persistida de un incidente."""
        try:
            result = service.get_incident(incident_id)
        except IncidentNotFound as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps(asdict(result), ensure_ascii=False))

    @application.command("sla")
    def sla(
        incident_id: str,
        reference_time: str | None = typer.Option(None, "--reference-time"),
    ) -> None:
        """Serializa el estado de SLA del incidente solicitado."""
        try:
            parsed_reference = parse_reference_time(
                reference_time, resolved_now=datetime.now()
            )
            reference = ReferenceTime(raw=reference_time, value=parsed_reference)
            result = service.get_incident_sla(incident_id, reference)
        except (IncidentNotFound, InvalidReferenceTime) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        typer.echo(json.dumps(asdict(result), ensure_ascii=False))

    return application


app = create_cli_app(build_incident_service())


if __name__ == "__main__":
    app()
