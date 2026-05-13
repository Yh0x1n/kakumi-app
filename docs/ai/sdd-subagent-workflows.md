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

## Criterio de verificación rápida para reviewers

- [ ] La delegación incluye `caveman`.
- [ ] La delegación incluye skills correctas de la fase.
- [ ] La delegación incluye reglas `uv` + `uv run reflex run` + timeout 45s.
- [ ] En `apply`/`verify`, la delegación marca explícitamente criticidad y cumplimiento estricto.
