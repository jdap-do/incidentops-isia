<!--
## Sync Impact Report
- Version change: unversioned template → 1.0.0
- Modified principles: template principles 1–5 → I. Dominio determinista;
  II. Un solo caso de uso para REST y CLI; III. Persistencia detrás de un puerto;
  IV. SQLite como adaptador inicial; V. Criterios BDD y fronteras verificadas
- Added sections: Arquitectura y tecnología; Flujo de trabajo y compuertas de calidad;
  reglas de governance concretas
- Removed sections: none
- Follow-up TODOs:
  - TODO(RUFF_TOOLING): Ruff no está aún declarado ni configurado en `pyproject.toml`;
    el cumplimiento de este principio requiere añadir la dependencia de desarrollo y
    las reglas de fronteras de importación fuera de este cambio de constitución.
-->
# IncidentOps Constitution

## Core Principles

### I. Dominio determinista

`src/domain/` MUST be the single source of truth for triaje, SLA, valid teams,
incident states and the correlation key. Severity MUST be derived from normalized
signals in the report text, never from the incident ID. The same input and reference
time MUST always produce the same result.

SLA rules MUST be deterministic and follow the accepted ADRs: P0/P1 accumulate
continuous time; P2/P3 accumulate only Monday–Friday 08:00–18:00; `resolved_at`
takes precedence over `reference_time`; breach requires `elapsed > allowed`, so
reaching the exact limit is not a breach. Escalation activates at 75 % of the
allowed time and remains active after the deadline while the incident is open,
so breach and escalation MAY be true at the same time.

Rationale: centralizing these rules prevents REST, CLI and any future adapter from
silently disagreeing about the same incident.

### II. Un solo caso de uso para REST y CLI

REST and CLI MUST be inbound adapters that delegate to `IncidentService`; they
MUST NOT contain business rules or duplicate use-case sequences. For identical
input, both adapters MUST return the same decision and the same serialized result.
Operations that evaluate SLA MUST receive the reference instant as an explicit
parameter. A future MCP adapter MUST be able to reuse the same use cases without
copying domain logic.

Rationale: ADR-003 selects hexagonal architecture precisely so that interfaces
share decisions instead of reimplementing them.

### III. Persistencia detrás de un puerto

`IncidentService` and `IncidentRepositoryPort`, defined with `typing.Protocol`,
MUST reside in `src/application/`. The service MUST depend only on that port for
persistence and MUST invoke the domain rules directly. The domain MUST NOT import
from `src/application/` or `src/adapters/`. Application code MUST NOT import
concrete database or framework modules.

Rationale: the port keeps use cases stable when the storage engine changes and
prevents technology choices from leaking into the core.

### IV. SQLite como adaptador inicial

SQLite MUST be the initial outbound adapter implementing `IncidentRepositoryPort`.
Only that adapter MAY import `sqlite3` or contain SQL schema and query details.
Replacing the engine MUST be done by implementing the same port and MUST require
an ADR; application and domain code MUST NOT change for that replacement.

Rationale: SQLite is sufficient for the current delivery, but it is a technology
detail, not a dependency of the business rules.

### V. Criterios BDD y fronteras verificadas

Acceptance criteria MUST be written in BDD form (Given / When / Then) and MUST be
verified with `pytest`. Every use case exposed through more than one adapter MUST
have a test that proves REST and CLI produce the same result. Ruff MUST verify
layer boundaries with import rules that forbid domain→application/adapters and
application→adapters imports, and MUST pass before a change is merged.

Rationale: executable BDD criteria make the deterministic rules observable, while
Ruff turns the architectural constraints from prose into a repeatable check.

## Arquitectura y tecnología

The technology baseline is Python 3.10+ managed with `uv`. REST uses FastAPI and
Pydantic v2, CLI uses Typer, and the initial persistence adapter uses the standard
library `sqlite3`. `pytest` and Ruff are required development tools.

The mandatory layout is `src/domain/` for rules, `src/application/` for the
service and repository port, and `src/adapters/inbound/` and `src/adapters/outbound/`
for inbound and outbound adapters. Dependencies MUST point toward the domain, the
service or the port; concrete frameworks and database modules MUST stay in adapters.

`docs/constitution.md` remains a preserved reference document. ADR-003 governs the
hexagonal boundaries and ADR-002 governs the SLA calculation; changes to either
MUST be decided in an ADR before this constitution is amended.

## Flujo de trabajo y compuertas de calidad

Each specification MUST declare BDD acceptance criteria before implementation and
link them to `pytest` tests. A change is complete only when `uv run pytest` and
`uv run ruff check .` pass from the repository root and the results are reported
after execution. REST/CLI changes MUST include equivalence coverage.

Reviews MUST check that no business rule was added to an adapter, that no layer
import violates the Ruff boundaries, and that persistence changes still satisfy
`IncidentRepositoryPort`. New dependencies, engine changes or boundary exceptions
MUST be justified in an ADR and reflected here.

## Governance

This constitution is the operative governance document for Spec Kit and supersedes
conflicting local practices. `docs/constitution.md` is kept as a reference; when
both differ, this file together with the accepted ADRs prevails.

Amendments MUST be proposed with a rationale, reviewed, approved and recorded with
a Sync Impact Report at the top of this file. Changes to domain rules, architecture
or the persistence engine MUST first be accepted as an ADR. The report is temporary
review material and MUST be removed before the amended file is committed.

Versioning follows semantic versioning: MAJOR for removing or redefining a
principle, MINOR for adding a principle or materially expanding guidance, and PATCH
for clarifications or non-semantic refinements. Every change MUST update the version
and `Last Amended` date.

Compliance review happens in every pull request: reviewers MUST verify the
principles, require passing `pytest` and Ruff checks, and reject unjustified
complexity or layer violations. Use `AGENTS.md` for runtime development guidance.

**Version**: 1.0.0 | **Ratified**: 2026-11-24 | **Last Amended**: 2026-11-24
