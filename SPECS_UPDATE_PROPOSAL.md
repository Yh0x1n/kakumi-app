# Propuesta de Cambio: Actualización de Especificaciones Técnicas

## Intención

El archivo `specs.md` actual carece de detalles técnicos fundamentales para la implementación del sistema de gestión de torneos de Karate-Do. Esta propuesta busca incorporar toda la información identificada en el análisis de brechas para que las especificaciones sirvan como guía completa para las fases de diseño e implementación.

**¿Por qué ahora?** El código actual del proyecto no puede avanzar sin definiciones claras en: modelos de datos, reglas de puntuación, sistema de penalidades, flujos de torneo y requisitos de interfaz. Actualmente hay un vacío entre lo que dice `specs.md` y lo que necesita un desarrollador para implementar correctamente cada módulo.

---

## Alcance

### Dentro del Alcance

| # | Entregable | Descripción |
|---|------------|-------------|
| 1 | Modelos de datos extendidos | Definición completa de Athlete, Tournament, Category, Match, Referee, Penalty, Team, MatchScore con todos los campos, relaciones y restricciones |
| 2 | Sistema de penalidades | Detalle específico de Chui, Hansoku Chui, Hansoku, Shikkaku para Kumite y Chui para Kata, incluyendo criterios de aplicación y acumulación |
| 3 | Sistema de puntuación | Puntuación detallada para Kata (escala 5.0-10, mayoría) y Kumite (Ippon=3, Waza-ari=2, Yuko=1), incluyendo penalizaciones y bonificaciones |
| 4 | Reglas de desempate | Criterios de desempate para Kata (puntuación media, criterio de jueces, etc.) y Kumite (Golden Point, penalties, etc.) |
| 5 | Asignación de árbitros | Roles de árbitros (Árbitros de tatami, Árbitros de mesa, Supervisor), reglas de asignación y rotación |
| 6 | Formatos de importación/exportación | Especificación de formatos CSV/JSON para atletas y resultados, incluyendo estructura de campos y validación |
| 7 | Roles de usuario y autenticación | Definición de Administrator, Operator, Viewer con permisos específicos, flujo de autenticación y gestión de sesiones |
| 8 | Fases del flujo de torneo | Estados del torneo (Inscripción, Verificación, En curso, Finalizado, Archivado) y transiciones entre ellos |
| 9 | Generación de brackets | Algoritmos de seeding, Bye rounds, integración de penalties en emparejamientos |
| 10 | Pantallas/UI requeridas | Listado detallado de todas las pantallas necesarias para cada función del sistema |

### Fuera del Alcance

- Implementación de código (solo especificaciones)
- Detalles de部署 o infraestructura
- Documentación de APIs REST (se abordará en fase de diseño)
- Reglas específicas de otras federaciones (solo WKF 2024-2025)
- Integración con sistemas externos de计时 o video

---

## Enfoque

### Metodología

1. **Análisis comparativo**: Revisar documentación WKF disponible en `/docs` para asegurar cumplimiento normativo
2. **Extensión modular**: Agregar secciones a `specs.md` sin reescribir contenido existente (preservar estructura actual)
3. **Validación cruzada**: Verificar que cada regla de puntuación/penalización sea implementable con los modelos de datos propuestos

### Estructura Propuesta para specs.md Actualizado

```
## Modelos de Datos (Nuevas secciones)
- 3.1 Atleta
- 3.2 Tournament
- 3.3 Category  
- 3.4 Match
- 3.5 Referee
- 3.6 Penalty
- 3.7 Team
- 3.8 MatchScore
```

```
## Sistema de Penalidades (Reemplaza sección actual)
- 4.1 Penalty Types
- 4.2 Accumulation Rules
- 4.3 Match Disqualification Flow
```

```
## Sistema de Puntuación (Amplía sección actual)
- 5.1 Kata Scoring
- 5.2 Kumite Scoring
- 5.3 Tie-Breaking Rules
```

```
## Flujo de Torneo (Nuevo)
- 6.1 Tournament Phases
- 6.2 Category Lifecycle
- 6.3 Match Flow
```

```
## Generación de Brackets (Nuevo)
- 7.1 Seeding Rules
- 7.2 Bye Placement
- 7.3 Bracket Types by Modality
```

```
## Arbitraje (Amplía sección actual)
- 8.1 Referee Roles
- 8.2 Assignment Rules
- 8.3 Rotation Schedule
```

```
## Importación/Exportación (Nuevo)
- 9.1 Athlete Import Format
- 9.2 Results Export Format
- 9.3 Validation Rules
```

```
## Autenticación y Roles (Amplía sección actual)
- 10.1 User Roles
- 10.2 Permission Matrix
- 10.3 Authentication Flow
```

```
## Interfaz de Usuario (Nuevo)
- 11.1 Screen Inventory
- 11.2 Navigation Flow
- 11.3 Responsive Requirements
```

---

## Áreas Afectadas

| Área | Impacto | Descripción |
|------|---------|-------------|
| `specs.md` | Modificado | Actualización y extensión de especificaciones |
| `/docs/*` | Referenciado | Regulations WKF para validación de reglas |
| Modelosedb en código | Afectado indirectamente | Los modelos deberán alinearse con specs actualizadas |

---

## Riesgos

| Riesgo | Probabilidad | Mitigación |
|--------|--------------|------------|
| Especificaciones contradictorias con WKF | Baja | Revisar documentación WKF existente antes de escribir |
| Modelos de datos incompatibles con UI | Media | Validar relaciones en fase de diseño antes de specs finales |
| Alcance demasiado amplio | Alta | Priorizar información crítica para MVP, diferir edge cases |
| Inconsistencia con código existente | Media | Verificar modelos actuales antes de proponer extensiones |

---

## Plan de Rollback

Si el proceso de actualización de specs revela conflictos fundamentales con el código existente o con las regulaciones WKF:

1. Preservar versión actual de `specs.md` como `specs.md.backup`
2. Crear nueva versión con marcar "DRAFT" hasta validación
3. Obtener aprobación del Product Owner antes de reemplazar versión estable

---

## Dependencias

- **Bloqueante**: Revisión de documentación WKF en `/docs` para confirmar reglas de puntuación y penalidades
- **Bloqueante**: Revisión de modelos de datos actuales en `kakumi_app/models/` para asegurar compatibilidad
- **Recomendado**: Revisión de estados existentes en `kakumi_app/states.py` para validar flujos

---

## Criterios de Éxito

- [ ] `specs.md` contiene definición completa de todos los modelos de datos mencionados
- [ ] Sistema de penalidades especifica criterios exactos para cada tipo de penalty
- [ ] Reglas de puntuación incluyen valores numéricos y criterios de mayoría
- [ ] Desempates detallados para Kata individual, Kata por equipos, Kumite individual, Kumite por equipos
- [ ] Formatos de import/export incluyen estructura de campos y ejemplos
- [ ] Matriz de permisos definida para cada rol de usuario
- [ ] Fases del torneo incluyen estados y transiciones válidas
- [ ] Algoritmo de generación de brackets especificado con ejemplos
- [ ] Inventario de pantallas cubre todas las funciones del sistema
- [ ] Specifications son implementables sin ambigüedad

---

## Estimación de Esfuerzo

| Componente | Complejidad | Estimación |
|------------|-------------|------------|
| Modelos de datos | Media | 1 día |
| Sistema de penalidades | Alta | 2 días |
| Sistema de puntuación | Alta | 2 días |
| Desempates | Alta | 1.5 días |
| Arbitraje | Media | 1 día |
| Import/Export | Baja | 0.5 días |
| Autenticación y Roles | Media | 1 día |
| Flujo de torneo | Alta | 1.5 días |
| Generación de brackets | Alta | 2 días |
| UI/Screens | Media | 1 día |

**Total estimado**: 13 días de trabajo de specs

---

## Próximo Paso

Esta propuesta está lista para la fase de **specs (sdd-spec)**. Una vez aprobada, se procederá a escribir las especificaciones detalladas para cada uno de los componentes identificados.
