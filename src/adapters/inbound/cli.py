"""Adaptador Typer para el triaje manual de IncidentOps."""

import json
from dataclasses import asdict

import typer

from src.application.services import IncidentService, InvalidTriageInput

app = typer.Typer(add_completion=False)
service = IncidentService()


@app.callback()
def main() -> None:
    """Punto de entrada CLI de IncidentOps."""


@app.command("triage")
def triage(
    incident_id: str = typer.Option(..., "--incident-id"),
    raw_text: str = typer.Option(..., "--raw-text"),
) -> None:
    try:
        result = service.triage_incident(incident_id, raw_text)
    except InvalidTriageInput as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(json.dumps(asdict(result), ensure_ascii=False))


if __name__ == "__main__":
    app()
