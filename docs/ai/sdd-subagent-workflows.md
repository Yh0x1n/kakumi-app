# Workflows obligatorios de skills para subagentes SDD

Este estándar es **obligatorio** para cualquier delegación SDD del proyecto.
El orquestador **debe inyectar** estas skills y reglas en cada subagente antes de ejecutar una fase.

## Ruta rápida del orquestador

1. Identificá la fase SDD (`explore`, `propose`, `spec`, `design`, `tasks`, `apply`, `verify`).
2. Inyectá siempre la skill `caveman`.
3. Inyectá además las skills obligatorias de la fase (tabla de abajo).
4. Inyectá reglas globales de ejecución (`uv`, `uv run reflex run`, timeout 45s).
5. Si la fase es `apply` o `verify`, reforzá reglas críticas (sección dedicada).

## Skills obligatorias por fase

> Regla base para todas las fases: **siempre cargar `caveman`**.

| Fase | Skills obligatorias |
|---|---|
| `explore` | `caveman`, `python-pro`, `reflex-dev`, `reflex-code-review-expert` |
| `propose` | `caveman`, `python-pro`, `reflex-dev`, `frontend-design` |
| `spec` | `caveman`, `python-pro`, `reflex-dev` |
| `design` | `caveman`, `python-pro`, `reflex-dev`, `seo`, `frontend-design` |
| `tasks` | `caveman`, `python-pro`, `reflex-dev` |
| `apply` | `caveman`, `python-pro`, `reflex-dev`, `python-executor`, `sqlalchemy-orm`, `pydantic`, `pytest`, `python-testing-patterns` |
| `verify` | `caveman`, `python-pro`, `reflex-dev`, `sqlalchemy-orm`, `sqlalchemy-alembic-expert-best-practices-code-review`, `pytest`, `reflex-code-review-expert` |

## Reglas globales obligatorias (todas las fases)

- Usá `uv` para gestión de virtualenv y dependencias.
- Para instalar dependencias, usá `uv pip install`.
- Para levantar servidor Reflex, usá siempre: `uv run reflex run`.
- El comando de servidor Reflex debe ejecutarse con timeout de 45 segundos.

Checklist de cumplimiento:

- [ ] El subagente usa `uv` para entorno y dependencias.
- [ ] El subagente usa `uv run reflex run` para servidor Reflex.
- [ ] El subagente aplica timeout de 45s al comando de servidor.

## Reglas críticas extra para `apply` y `verify`

Las fases `apply` y `verify` son críticas para integridad del proyecto.
En estas fases, el orquestador y el subagente deben tratar estas reglas como **no negociables**:

- Reiterar explícitamente obligación de `uv`.
- Reiterar explícitamente `uv run reflex run` para servidor Reflex.
- Reiterar explícitamente timeout de 45 segundos en ejecución de servidor.
- No continuar la fase si estas condiciones no están inyectadas en el prompt del subagente.

## Plantilla mínima de inyección para delegación

Usá este bloque al delegar una fase SDD:

```text
Delegación SDD - fase: <FASE>

Skills obligatorias:
- caveman
- <skills específicas de fase según tabla>

Reglas obligatorias:
1) Usar uv para virtualenv/dependencias; si hace falta instalar paquetes, usar `uv pip install`.
2) Si se ejecuta servidor Reflex, usar `uv run reflex run`.
3) Aplicar timeout de 45s al comando uv run reflex run.

Regla extra (solo apply/verify):
- Fase crítica: cumplimiento estricto y permanente de reglas uv/reflex/timeout.
```

## Subagentes de Review Técnica (4R System)

Después de `sdd-apply`, el orquestador puede lanzar subagentes de review especializados.
Cada uno tiene un lente distinto, contexto fresco, y es **read-only**.

### Clasificación de lentes

| Subagente | Lente | Señal de riesgo |
|---|---|---|
| `review-risk` | R1 — Seguridad y arquitectura | Permisos, data exposure, dependencias, vulnerabilidades |
| `review-resilience` | R2 — Resiliencia y recovery | Fallas parciales, retry/backoff, degraded modes, rollback |
| `review-readability` | R3 — Legibilidad y mantenibilidad | Naming, complejidad, estructura, intention revealing |
| `review-reliability` | R4 — Confiabilidad y tests | Tests, edge cases, determinismo, regresiones, contratos |

### Reglas de ejecución

- Cada reviewer recibe un **snapshot completo inmutable** del diff.
- Devuelve hallazgos estructurados siguiendo el **Frozen Findings Ledger** (ver `docs/ai/review-contract.md`).
- Hallazgos inferenciales severos pasan por `review-refuter` adversarial antes de decidir acción.
- Después de corrección, un **scoped validator** verifica solo el fix delta (no reabre la review completa).
- Los reviewers **nunca** editan código, lanzan correcciones, ni inician otros reviewers.

### Inyección para delegaciones de review

```text
Delegación - review: <LENTE>

Roles:
- Eres read-only. No edites código, no sugieras fixes inline.
- Recibes un snapshot inmutable del diff.
- Devuelve hallazgos en formato Frozen Findings Ledger.
- No agregues narrativa persuasiva — solo claims neutrales + proof_refs concretos.
- Si no encontrás hallazgos, devolvé un ledger vacío explícito.

Skills obligatorias:
- caveman
- python-pro
- reflex-dev

Referencia obligatoria:
- docs/ai/review-contract.md (contrato completo de review)
```

## Criterio de verificación rápida para reviewers

### Para fases SDD

- [ ] La delegación incluye `caveman`.
- [ ] La delegación incluye skills correctas de la fase.
- [ ] La delegación incluye reglas `uv` + `uv run reflex run` + timeout 45s.
- [ ] En `apply`/`verify`, la delegación marca explícitamente criticidad y cumplimiento estricto.

### Para review técnica (4R)

- [ ] El reviewer es read-only y recibe snapshot inmutable.
- [ ] La delegación especifica el lente exacto (risk/resilience/readability/reliability).
- [ ] La delegación referencia `docs/ai/review-contract.md`.
- [ ] Hallazgos siguen el schema Frozen Findings Ledger.
- [ ] No hay narrativa persuasiva — solo claims neutrales + proof_refs.
- [ ] Los hallazgos inferenciales severos se enrutan al refuter.
