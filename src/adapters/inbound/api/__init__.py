"""Adaptador REST inbound para IncidentOps."""

from .app import app, create_api_app

__all__ = ["app", "create_api_app"]
