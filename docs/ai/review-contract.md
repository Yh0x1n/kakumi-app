# Contrato de Review Técnica — 4R System

Este documento define las **hard rules** del sistema de revisión técnica post-implementación.
Es de cumplimiento obligatorio para el orquestador y todos los subagentes de review.

---

## 1. Trigger de Review

La review se lanza **exclusivamente** después de `sdd-apply`, y **solo si no existe un receipt válido**.

Los lifecycle gates NO lanzan review nueva:
- **Pre-commit**: valida receipt existente — nunca lanza reviewer.
- **Pre-push**: valida receipt contra commits salientes — nunca lanza reviewer.
- **Pre-PR**: valida receipt contra candidate tree + base — nunca lanza reviewer.
- **Release**: valida receipt + evidence freshness + publication boundary — nunca lanza reviewer.

Si el receipt está `missing`, `scope-changed`, `invalidated` o `escalated`, el gate falla con mensaje machine-readable.
No se crea un nuevo presupuesto de review automáticamente.

---

## 2. Clasificación de Riesgo (Determinística)

El orquestador clasifica el diff **antes** de seleccionar lentes. Es una decisión determinística, no un consejo.

### Paso 1: ¿Es trivial?

```text
SI el diff contiene SOLAMENTE (una o más de):
  - documentación, comentarios
  - cambios de formato
  - typo fixes en strings (cero código ejecutable)
  - cambios de configuración que no afectan lógica
  - archivos generados excluidos del authored threshold

→ NO correr ningún lente. Review skipped.
```

### Paso 2: ¿Es hot path?

```text
SI el diff toca auth/seguridad/pagos/update paths
O el authored diff >400 líneas (excluyendo goldens generados)

→ 4R completo: correr los 4 lentes iniciales.
```

### Paso 3: Es standard

```text
Para todo lo demás:
→ Correr EXACTAMENTE 1 lente — el que mejor matchee el riesgo dominante.
```

### Tabla de selección

| Señal de riesgo dominante | Lente |
|---|---|
| Naming, estructura, maintainability, refactors pequeños | `review-readability` |
| Comportamiento, estado, tests, determinismo, regresiones | `review-reliability` |
| Integración shell/process, fallas parciales, recovery, dependencias degradadas | `review-resilience` |
| Seguridad, permisos, exposición de datos, arquitectura, dependencias | `review-risk` |

Si múltiples señales empatan, elegir la de mayor impacto. Standard nunca escala a múltiples lentes.

---

## 3. Contrato de Ejecución de Review

### Operación

La review es explícita: `review/start(target)`. Recibe un snapshot completo inmutable.

### Cada reviewer es:

- **Read-only**: no edita código, no lanza correcciones, no inicia otros reviewers.
- **Detached**: contexto fresco, sin memoria de sesiones anteriores.
- **Terminal**: devuelve un resultado y termina. Un resultado por operación.

El orquestador selecciona 0, 1 o 4 lentes iniciales según la clasificación de riesgo.
Cada lente seleccionado corre exactamente un sweep exhaustivo.

---

## 4. Frozen Findings Ledger

Cada reviewer emite hallazgos estructurados. No narrativa persuasiva.

### Schema

```json
{
  "id": "{LENS}-{NNN}",
  "lens": "risk | readability | reliability | resilience | judgment-day | scoped-fix-validator",
  "location": "path/to/file.ext:line",
  "severity": "BLOCKER | CRITICAL | WARNING | SUGGESTION",
  "claim": "Neutral statement of observable incorrect behavior",
  "evidence_class": "deterministic | inferential | insufficient",
  "proof_refs": ["concrete command", "output hash", "file:line references"],
  "status": "open | corroborated | refuted | inconclusive | fixed | verified | info"
}
```

### Reglas

- WARNING y SUGGESTION son siempre `info` — nunca bloquean aprobación ni disparan corrección.
- Si no hay hallazgos, se persiste un ledger vacío explícito.
- El ledger se congela después de la review inicial de lentes seleccionados.

---

## 5. Enrutamiento de Evidencia

### Hallazgos determinísticos severos

Se marcan `corroborated` con proof — nunca pasan por refuter.

### Hallazgos inferenciales severos (BLOCKER / CRITICAL)

Se fusionan de **todos los lentes seleccionados** en **exactamente 1 operación refuter**. El refuter recibe:

- El target inmutable original
- Todos los claims neutrales + proof_refs

Devuelve un resultado por hallazgo: `corroborated | refuted | inconclusive`.

### Refuter

- Es read-only
- No puede agregar hallazgos nuevos ni cambiar scope
- Devuelve un resultado completo y termina
- Si el output del refuter falta, está malformado o incompleto → el hallazgo queda `inconclusive` (no se asume corroboración)

### Hallazgos insufficient

Se marcan `inconclusive` — nunca se auto-fixean.

---

## 6. Corrección y Validación

Solo el **orquestador** puede lanzar un actor de corrección o un scoped validator, y solo dentro de contadores de transacción nativos.

### Corrección

- Máximo **1 transacción de corrección** por review ordinaria.
- Compuesta de unidades de trabajo atómicas.
- Cada unidad registra: focused-test evidence, runtime evidence (o N/A justificado), rollback boundary independiente.
- La cantidad de work units no crea otro presupuesto de corrección.

### Scoped Validator

- Se corre después de la corrección (si hubo).
- Es detached, read-only.
- Recibe solo el frozen ledger original + el fix delta inmutable.
- Verifica solo las líneas tocadas por el fix.
- Puede agregar hallazgos causados por el fix (con proof).
- Solo puede devolver `approve` o `escalate`.
- No reabre el diff original, no lanza otra corrección, no itera.

---

## 7. Verificación Final Independiente

Es verificación independiente contra requerimientos/runtime:

- Requerimientos reales, escenarios, task completion
- Test/build evidence actual
- Frozen ledger resolution
- Snapshot identity
- Coherence de contadores

Si hay contradicción o check determinístico que falla → `escalated`.
No puede iniciar otro 4R, refuter, corrección, ni scoped validation loop.

Estados terminales de transacción: solo `approved | escalated`.

---

## 8. Receipt Validation (Lifecycle Gates)

### Gate Context

Cada gate binding contiene:

- Expected HEAD
- Genesis review
- Ordered chain identity
- Bundle digest

### Validación

1. Deriva el authoritative store root desde el repositorio.
2. Valida la cadena semántica completa (eventos, hashes, predecesores).
3. Deriva el target actual del repositorio.
4. Hashea policy, ledger, fix delta, verify evidence, release artifacts desde inputs persistidos.

Caller-authored store paths, transactions, trees, o hash assertions **nunca** son autoritativos.

### Resultados del gate

| Estado | Acción |
|---|---|
| `missing` | Fail closed — denial machine-readable |
| `scope-changed` | Fail closed — requiere nueva lineage |
| `invalidated` | Fail closed — requiere maintainer action explícita |
| `escalated` | Fail closed — stop |

---

## 9. Persistencia

### Artifacts (OpenSpec mode)

```
openspec/changes/{change-name}/reviews/
├── transaction.json
├── policy.md
├── ledger.json
├── receipt.json
├── chain-bundle.json
└── gate-context.json
```

### Canonical store (CAS)

```
<git-common-dir>/gentle-ai/review-transactions/v1/{lineage-id}/
```

El store autoritativo es append-only, content-addressed.
Los archivos en `openspec/` son espejos no autoritativos.

### Persistencia en Engram

```
sdd/{change-name}/review/transaction
sdd/{change-name}/review/policy
sdd/{change-name}/review/ledger
sdd/{change-name}/review/receipt
sdd/{change-name}/review/chain-bundle
sdd/{change-name}/review/gate-context
```

---

## 10. Recovery y Bundle Import

Para recuperación en clone limpio / workstation nueva:

1. Persistir el chain bundle completo (ordenado, content-addressed).
2. `review-bundle-import` valida:
   - Bundle digest
   - Cada event hash, predecessor, semantic transition
   - Lineage, generation, mode
   - Initial/final snapshot identities
   - Terminal fix-diff semantics
   - Expected gate chain identity

3. Antes de instalar en CAS, verifica que el target derivado actual matchee `final_candidate_tree` y el receipt/lineage path scope.
4. Si algo no matchea → fail closed. No auto-import.
5. `review-validate` nunca auto-importa.

---

## 11. Release Fast Path (protected `main`)

**No requiere receipt reusable** si TODO esto se cumple:

- El tag target es el SHA actual e inmutable de `origin/main`.
- CI requerido para ese SHA exacto es exitoso.
- El remote no ha avanzado antes del tag push.
- No hay nueva evidencia de vulnerabilidad, policy, provenance, signing, generated-artifact, o release que requiera escalation.

SI ALGO FALLA → fallback a native receipt validation → fail closed en missing/changed/invalidated/escalated.

Major releases y releases post-incidente requieren **extraordinary review** siempre, incluso si el fast path checks pasan.

---

## 12. Regla de Oro

> Review es para encontrar problemas, no para aprobar código.  
> El refuter es para verificar hallazgos, no para ganar discusiones.  
> El scoped validator es para confirmar fixes, no para reabrir la review.  
> Los lifecycle gates son para proteger el pipeline, no para crear presupuesto nuevo.
