"""Adaptador Typer para el triaje manual y el resumen de incidentes."""

import json
from dataclasses import asdict
from datetime import datetime

import typer

from src.application.services import (
    IncidentService,
    InvalidReferenceTime,
    InvalidTriageInput,
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

    return application


app = create_cli_app(build_incident_service())


if __name__ == "__main__":
    app()
