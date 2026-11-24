"""Clasificación y enrutamiento deterministas de reportes de IncidentOps."""

import json
import re
import unicodedata
from pathlib import Path

from .models import SeverityLevel, TriageResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_DATA_PATH = PROJECT_ROOT / "data" / "sample_incidents.json"

COMPONENT_SIGNALS = (
    ("database-cluster", r"\b(?:postgresql|base de datos|cluster de datos|pool de conexiones)\b"),
    ("infra-certificates", r"\b(?:certificados?|tls|ssl)\b"),
    ("frontend-ui", r"\b(?:boton(?:es)?|interfaz|color|icono|tipografia)\b"),
    ("auth-identity", r"\b(?:cuenta|autenticacion|iniciar sesion|credenciales|identidad|login)\b"),
    ("reporting-api", r"\b(?:reportes?|exportacion|excel|pdf|listado|historial|dashboard)\b"),
    ("payments-gateway", r"\b(?:pagos?|pagar|cobros?|cobrar|pasarela|tarjetas?|transacciones)\b"),
)

DEFAULT_TEAMS = {
    "payments-gateway": "Backend-Core",
    "auth-identity": "Security-IAM",
    "reporting-api": "Backend-Core",
    "frontend-ui": "Backend-Core",
    "database-cluster": "Data-DBA",
    "infra-certificates": "Platform-SRE",
}


def _normalize(raw_text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", raw_text.casefold())
    plain_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return " ".join(plain_text.split())


def classify_incident_report(incident_id: str, raw_text: str) -> TriageResult:
    """Clasifica por componente y señales de impacto en el texto."""
    text = _normalize(raw_text)

    def has(pattern: str) -> bool:
        return re.search(pattern, text) is not None

    component = next(
        (name for name, pattern in COMPONENT_SIGNALS if has(pattern)),
        "reporting-api",
    )
    cross_tenant = has(
        r"\b(?:otra(?:s)? (?:organizacion(?:es)?|empresa(?:s)?|tenant(?:s)?)"
        r"|entre (?:organizaciones|empresas|tenants)|cross[- ]tenant)\b"
    )
    exposure = has(
        r"\b(?:visualizar|ver|acceder|exposicion|fuga|filtracion|datos expuestos)\b"
    )
    unauthorized = has(r"\b(?:acceso indebido|acceso no autorizado)\b")
    payment_signal = has(COMPONENT_SIGNALS[-1][1])
    http_502 = has(r"\b(?:(?:http|error|codigo)\s*502|502\s+bad gateway)\b")
    outage = has(r"\b(?:cayo|caida|fuera de servicio|indisponible|no pueden? (?:pagar|cobrar)|ningun comercio puede cobrar)\b")
    connection_usage = re.search(
        r"\b(\d{1,3}(?:[.,]\d+)?)\s*%[^\n.]{0,45}\b(?:conexiones|pool)\b"
        r"|\b(?:conexiones|pool)[^\n.%]{0,45}\b(\d{1,3}(?:[.,]\d+)?)\s*%",
        text,
    )
    saturated_pool = connection_usage is not None and (
        90 < float((connection_usage[1] or connection_usage[2]).replace(",", ".")) <= 100
    )
    timeouts = has(r"\b(?:timeouts?|tiempos? de espera agotados?)\b")
    severe_degradation = has(r"\b(?:degradacion severa|saturacion (?:critica|severa)|riesgo (?:inminente )?de caida)\b")
    slow = has(r"\b(?:lent[oa]s?|tarda|demora|latencia|se queda pensando|\d+(?:[.,]\d+)?\s+segundos)\b")
    high_volume = has(r"\b(?:alto volumen|10[,. ]?000\s+(?:ordenes|registros))\b")
    identity_lockout = has(r"\b(?:bloquead[oa]s?|bloqueo)\b")

    severity: SeverityLevel
    if cross_tenant and (exposure or unauthorized):
        severity, symptom = "P0", "cross-tenant-access"
        rationale = "Se reporta acceso a datos de otra organización."
    elif payment_signal and (http_502 or outage) and not has(r"\b(?:staging|preproduccion)\b"):
        component = "payments-gateway"
        severity = "P0"
        if http_502 and outage:
            symptom = "http-502-outage"
        elif http_502:
            symptom = "http-502"
        else:
            symptom = "service-outage"
        rationale = "El reporte indica un fallo en el servicio crítico de pagos."
    elif component == "database-cluster" and (saturated_pool or (timeouts and severe_degradation)):
        severity, symptom = "P1", "connection-pool-saturation"
        rationale = "El pool de conexiones presenta degradación severa y riesgo para el servicio compartido."
    elif component == "infra-certificates" and severe_degradation:
        severity, symptom = "P1", "certificate-degradation"
        rationale = "Se reporta degradación severa asociada a la infraestructura de certificados."
    elif component == "auth-identity" and identity_lockout:
        severity, symptom = "P2", "account-lockout"
        rationale = "El reporte describe el bloqueo de una cuenta individual."
    elif slow:
        severity, symptom = "P2", "latency"
        rationale = "Se reporta lentitud con el servicio disponible."
        if component == "reporting-api" and high_volume:
            symptom = "high-volume-latency"
            rationale = "La lentitud de reportes coincide con un alto volumen de registros."
        elif component == "reporting-api" and has(r"\b(?:exportacion|exportar|excel|descarga)\b"):
            symptom = "export-latency"
    elif component == "frontend-ui" and has(r"\b(?:color|contraste|tipografia|estilo|cosmetico)\b"):
        severity, symptom = "P3", "cosmetic-change"
        rationale = "Se solicita un cambio visual de la interfaz."
    elif component == "infra-certificates" and has(r"\b(?:staging|preproduccion)\b") and has(
        r"\b(?:vencera|vencimiento|expira|caducidad|rotacion|renovacion)\b"
    ):
        severity, symptom = "P3", "certificate-renewal"
        rationale = "Se solicita mantenimiento preventivo de un certificado en staging."
    else:
        severity, symptom = "P3", "unclassified"
        rationale = "Se conserva el valor de respaldo P3 ante señales insuficientes para aplicar una regla."

    team = "Security-IAM" if unauthorized or symptom == "cross-tenant-access" else DEFAULT_TEAMS[component]
    return TriageResult(
        incident_id=incident_id,
        severity=severity,
        component=component,
        rationale=rationale,
        recommended_team=team,
        duplicate_group_key=f"{component}:{symptom}",
    )


# Los ID identifican casos de auditoría. El clasificador decide a partir del texto.
AUDIT_EXPECTATIONS = {
    "INC-1001": ("P0", "payments-gateway", "Backend-Core", "http-502-outage"),
    "INC-1002": ("P2", "auth-identity", "Security-IAM", "account-lockout"),
    "INC-1003": ("P2", "reporting-api", "Backend-Core", "high-volume-latency"),
    "INC-1004": ("P3", "frontend-ui", "Backend-Core", "cosmetic-change"),
    "INC-1005": ("P1", "database-cluster", "Data-DBA", "connection-pool-saturation"),
    "INC-1006": ("P0", "payments-gateway", "Backend-Core", "http-502-outage"),
    "INC-1007": ("P0", "reporting-api", "Security-IAM", "cross-tenant-access"),
    "INC-1008": ("P2", "reporting-api", "Backend-Core", "high-volume-latency"),
    "INC-1009": ("P2", "reporting-api", "Backend-Core", "export-latency"),
    "INC-1010": ("P3", "infra-certificates", "Platform-SRE", "certificate-renewal"),
}


def _run_triage_audit() -> None:
    """Comprueba los resultados esperados con el conjunto de datos del proyecto."""
    rows = json.loads(SAMPLE_DATA_PATH.read_text(encoding="utf-8"))
    reports = {row["id"]: row["raw_text"] for row in rows}
    if len(rows) != len(AUDIT_EXPECTATIONS) or reports.keys() != AUDIT_EXPECTATIONS.keys():
        raise SystemExit("La auditoría requiere una fila para cada ID de INC-1001 a INC-1010.")

    keys = {}
    failures = []
    for incident_id, (severity, component, team, symptom) in AUDIT_EXPECTATIONS.items():
        result = classify_incident_report(incident_id, reports[incident_id])
        keys[incident_id] = result.duplicate_group_key
        actual = (result.severity, result.component, result.recommended_team, keys[incident_id])
        expected = (severity, component, team, f"{component}:{symptom}")
        print(f"{incident_id} | {' | '.join(actual)}")
        if actual != expected:
            failures.append(f"{incident_id}: esperado {expected!r}, obtenido {actual!r}.")

    for first, second in (("INC-1001", "INC-1006"), ("INC-1003", "INC-1008")):
        if keys[first] != keys[second]:
            failures.append(f"{first} y {second}: las claves de correlación difieren.")

    if failures:
        raise SystemExit("\n".join(failures))
    print("Auditoría aprobada: 10 incidentes y 2 pares de correlación.")


if __name__ == "__main__":
    _run_triage_audit()
