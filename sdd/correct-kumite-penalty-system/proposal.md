# Proposal: Correction of Kumite Penalty System in specs.md

## Intent

Corregir las incorrecciones en el sistema de penalizaciones de Kumite en specs.md para alinearlo estrictamente con el Artículo 10 del Reglamento WKF 2026. Las correcciones principales son:

1. **Secuencia de acumulación**: Aclarar que la progresión es CHUI → CHUI → CHUI → HANSOKU CHUI → HANSOKU (no SHUKOKU/KEIKOKU)
2. **HANSOKU CHUI**: Eliminar la falsa creencia de que otorga puntos al oponente — es SOLO una advertencia (warning), sin asignación de puntos

## Scope

### In Scope
- Section 4.1.2: Agregar clarificación que HANSOKU CHUI no otorga puntos
- Section 4.3.1: Aclarar/explicitar la secuencia correcta de acumulación
- Glosario (línea 1087): Corregir definición de "Hansoku Chui"
- Verificar que no haya otras menciones incorrectas sobre puntos en HANSOKU CHUI

### Out of Scope
- Cambios en el modelo de datos (Penalty model ya tiene los tipos correctos)
- Lógica de implementación en código
-其他 secciones de Kata o otras modalidades

## Approach

1. Revisar línea por línea las secciones afectadas usando los hechos del PDF WKF 2026
2. Actualizar texto para eliminar cualquier referencia a puntos por HANSOKU CHUI
3. Aclarar la progresión de warnings en Section 4.3.1
4. Mantener todo lo demás correcto del specs.md

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `specs.md:4.1.2` | Modified | Agregar nota sobre HANSOKU CHUI sin puntos |
| `specs.md:4.3.1` | Modified | Aclarar secuencia de acumulación |
| `specs.md:12 (Glosario)` | Modified | Corregir definición Hansoku Chui |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Confusión con KEIKOKU/SHUKOKU que aparecen en el modelo | Low | KEIKOKU es válido para otras situaciones, solo clarificar acumulación de CHUI |
| Inconsistencia con código existente | Low | Revisar que el código Penalty no asigne puntos por HANSOKU CHUI |

## Rollback Plan

1. Restaurar specs.md desde git: `git checkout HEAD -- specs.md`
2. Descartar cambios en el archivo proposal

## Dependencies

- `docs/WKF 2026 Kumite Competition Rules MASTER COPY_V11.pdf` — fuente autoritativa para Article 10

## Success Criteria

- [ ] Section 4.3.1 muestra claramente: CHUI → CHUI → CHUI → HANSOKU CHUI → HANSOKU
- [ ] No existe ninguna mención de "puntos para oponente" asociada a HANSOKU CHUI
- [ ] Glosario define HANSOKU CHUI como warning/advertencia, sin mención de puntos
- [ ] Distinción clara entre warnings (CHUI, HANSOKU CHUI) y descalificaciones (HANSOKU, SHIKKAKU)
