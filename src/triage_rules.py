"""Compatibilidad: el clasificador vive ahora en `src.domain.triage_rules`."""

from src.domain.triage_rules import (
    AUDIT_EXPECTATIONS,
    COMPONENT_SIGNALS,
    DEFAULT_TEAMS,
    PROJECT_ROOT,
    SAMPLE_DATA_PATH,
    _normalize,
    _run_triage_audit,
    classify_incident_report,
)

__all__ = [
    "AUDIT_EXPECTATIONS",
    "COMPONENT_SIGNALS",
    "DEFAULT_TEAMS",
    "PROJECT_ROOT",
    "SAMPLE_DATA_PATH",
    "_normalize",
    "_run_triage_audit",
    "classify_incident_report",
]


if __name__ == "__main__":
    _run_triage_audit()
