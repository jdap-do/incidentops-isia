"""Evaluación determinista de SLA conforme al ADR-002.

La auditoría integrada se ejecuta con ``python -m src.sla_calculator``.
Las fechas recibidas deben ser locales naive coherentes.
"""

from datetime import datetime, time, timedelta
from typing import Dict

from .models import Incident, SLAEvaluation, SLARule, SeverityLevel


SLA_POLICY_TABLE: Dict[SeverityLevel, SLARule] = {
    "P0": SLARule(severity="P0", max_resolution_minutes=60, operates_24x7=True),
    "P1": SLARule(severity="P1", max_resolution_minutes=240, operates_24x7=True),
    "P2": SLARule(severity="P2", max_resolution_minutes=480, operates_24x7=False),
    "P3": SLARule(severity="P3", max_resolution_minutes=1440, operates_24x7=False),
}


def get_sla_rule_for_severity(severity: SeverityLevel) -> SLARule:
    """Obtiene la regla de SLA aplicable a una severidad validada contra la tabla."""
    if severity not in SLA_POLICY_TABLE:
        raise ValueError(f"Severidad no válida: {severity}")
    return SLA_POLICY_TABLE[severity]


def _business_seconds(start: datetime, end: datetime) -> float:
    """Suma intersecciones diarias hábiles en O(D) tiempo y O(1) memoria."""
    current_date = start.date()
    final_date = end.date()
    total_seconds = 0.0
    while current_date <= final_date:
        if current_date.weekday() < 5:
            window_start = datetime.combine(current_date, time(8))
            window_end = datetime.combine(current_date, time(18))
            overlap_start = max(start, window_start)
            overlap_end = min(end, window_end)
            if overlap_end > overlap_start:
                total_seconds += (overlap_end - overlap_start).total_seconds()
        # Evita desbordar date.max después de procesar la última fecha.
        if current_date == final_date:
            break
        current_date += timedelta(days=1)
    return total_seconds


def evaluate_sla_status(incident: Incident, reference_time: datetime) -> SLAEvaluation:
    """Evalúa minutos, incumplimiento y escalamiento con el final efectivo.

    El cierre prevalece sobre la referencia. P0/P1 acumulan tiempo continuo;
    P2/P3 acumulan únicamente lunes a viernes de 08:00 a 18:00.
    Un intervalo invertido produce ValueError.
    """
    rule = get_sla_rule_for_severity(incident.severity)
    end_time = incident.resolved_at or reference_time
    if end_time < incident.created_at:
        raise ValueError("El tiempo de referencia no puede ser anterior a la creación.")

    if rule.operates_24x7:
        delta_seconds = (end_time - incident.created_at).total_seconds()
    else:
        delta_seconds = _business_seconds(incident.created_at, end_time)
    elapsed_minutes = int(delta_seconds // 60)
    remaining_minutes = rule.max_resolution_minutes - elapsed_minutes
    is_breached = elapsed_minutes > rule.max_resolution_minutes
    escalation_limit = int(rule.max_resolution_minutes * rule.escalation_threshold_ratio)
    requires_escalation = (
        incident.status != "RESOLVED" and elapsed_minutes >= escalation_limit
    )
    return SLAEvaluation(
        incident_id=incident.incident_id,
        severity=incident.severity,
        elapsed_minutes=elapsed_minutes,
        allowed_minutes=rule.max_resolution_minutes,
        remaining_minutes=remaining_minutes,
        is_breached=is_breached,
        requires_escalation=requires_escalation,
    )


def _run_audit() -> None:
    """Comprueba resultados mediante aserciones reproducibles sin dependencias."""
    if not __debug__:
        raise RuntimeError("La auditoría requiere Python sin -O para ejecutar aserciones.")
    friday = datetime(2026, 11, 6, 17)
    monday = datetime(2026, 11, 9, 9)
    cases = [
        ("fuera de horario", "P2", datetime(2026, 11, 6, 18, 30), datetime(2026, 11, 9, 8, 30), None, 30, False, False),
        ("creación sábado", "P2", datetime(2026, 11, 7, 10), monday, None, 60, False, False),
        ("fin de semana", "P2", friday, monday, None, 120, False, False),
        ("P0 continuo", "P0", friday, monday, None, 3840, True, True),
        ("umbral 75 %", "P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 14), None, 360, False, True),
        ("límite exacto", "P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 16), None, 480, False, True),
        ("vencido abierto", "P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 9, 17), None, 540, True, True),
        ("varios fines de semana", "P2", friday, datetime(2026, 11, 16, 9), None, 3120, True, True),
        ("resuelto", "P2", friday, datetime(2026, 11, 16, 9), monday, 120, False, False),
        ("P1 continuo", "P1", friday, monday, None, 3840, True, True),
        ("P3 hábil", "P3", friday, monday, None, 120, False, False),
        ("resuelto vencido", "P2", datetime(2026, 11, 9, 8), datetime(2026, 11, 16, 9), datetime(2026, 11, 9, 17), 540, True, False),
        ("intervalo vacío", "P2", monday, monday, None, 0, False, False),
        ("solo fin de semana", "P2", datetime(2026, 11, 7, 10), datetime(2026, 11, 8, 15), None, 0, False, False),
        ("segundos entre días", "P2", datetime(2026, 11, 6, 17, 59, 30), datetime(2026, 11, 9, 8, 0, 30), None, 1, False, False),
    ]
    for index, (name, severity, start, reference, resolved, minutes, breached, escalation) in enumerate(cases, 1):
        incident = Incident(
            incident_id=f"AUDIT-{index}", title=name, component="audit",
            severity=severity, status="RESOLVED" if resolved else "OPEN",
            created_at=start, resolved_at=resolved,
        )
        result = evaluate_sla_status(incident, reference)
        allowed = SLA_POLICY_TABLE[severity].max_resolution_minutes
        assert result.incident_id == incident.incident_id, name
        assert result.severity == severity, name
        assert result.elapsed_minutes == minutes, (name, result)
        assert result.allowed_minutes == allowed, (name, result)
        assert result.remaining_minutes == allowed - minutes, (name, result)
        assert result.is_breached is breached, (name, result)
        assert result.requires_escalation is escalation, (name, result)
        print(f"OK: {name}: {minutes} min; incumple={breached}; escala={escalation}")

    inverted = Incident(
        incident_id="AUDIT-INVERTED", title="Intervalo invertido", component="audit",
        severity="P2", status="OPEN", created_at=monday,
    )
    try:
        evaluate_sla_status(inverted, friday)
    except ValueError:
        print("OK: intervalo invertido rechazado con ValueError")
    else:
        raise AssertionError("El intervalo invertido no produjo ValueError")
    print(f"Auditoría completada: {len(cases) + 1} casos correctos.")


if __name__ == "__main__":
    _run_audit()
