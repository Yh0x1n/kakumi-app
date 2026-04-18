# Delta Spec: Penalty System (Kumite)

STRICT TDD MODE IS ACTIVE. Test runner: `source .venv/bin/activate && python -m pytest tests/ -q`

## ADDED Requirements

### Requirement: Aplicación de Penalidades WKF
El sistema MUST permitir asignar penalidades oficiales WKF (Chui, Hansoku Chui, Hansoku, Shikkaku).
El sistema MUST detener el timer localmente ANTES de enviar la solicitud para evitar desincronización.

#### Scenario: Escalamiento de Penalidades
- GIVEN un competidor tiene Chui
- WHEN recibe nueva penalidad
- THEN escala a Hansoku Chui.

#### Scenario: Descalificación por Hansoku
- GIVEN un match en curso
- WHEN competidor A recibe Hansoku
- THEN match termina, competidor B es declarado ganador, A no es descalificado del torneo.

#### Scenario: Penalidad a AMBOS (BOTH)
- GIVEN un match en curso
- WHEN ambos competidores reciben una penalidad que resulta en Hansoku para ambos
- THEN el match termina y ambos son descalificados del match.

#### Scenario: Concurrent Penalty Application
- GIVEN 2 requests simultáneos de penalidad al mismo competidor
- WHEN ambos llegan al server
- THEN DB lock serializa, primer request aplica, segundo es rechazado o evaluado sobre nuevo estado.

### Requirement: Regla de SHIKKAKU
El sistema MUST descalificar al competidor del torneo completo al recibir SHIKKAKU.
En Round-Robin (RR), el sistema MUST anular TODOS los scores previos del competidor descalificado y reasignar los puntos a los oponentes, EXCEPTO si es su último combate, en cuyo caso los scores de combates anteriores se mantienen.

#### Scenario: SHIKKAKU en RR — NO último bout
- GIVEN torneo en RR y competidor no está en su último encuentro
- WHEN recibe Shikkaku
- THEN match termina, scores previos se anulan, oponente recibe victoria máxima. Avance futuro cancelado.

#### Scenario: SHIKKAKU en RR — último bout
- GIVEN torneo en RR y competidor está en su último encuentro
- WHEN recibe Shikkaku
- THEN match termina, scores de combates ANTERIORES se mantienen. Avance futuro cancelado.

### Requirement: Restricción de Tatami Múltiple
El sistema MUST prohibir que un competidor compita en 2 tatamis simultáneamente.

#### Scenario: Double tatami
- GIVEN un competidor activo en el Tatami 1 (Match IN_PROGRESS)
- WHEN se intenta iniciar un match con el mismo competidor en el Tatami 2
- THEN el sistema rechaza la acción con un error de concurrencia de atleta.

### Requirement: Remoción de Penalidades
El sistema MUST permitir la remoción de la última penalidad asignada ÚNICAMENTE si el estado del match es `IN_PROGRESS`.

#### Scenario: remove_last_penalty guard
- GIVEN un match con status distinto a IN_PROGRESS
- WHEN se intenta invocar `remove_last_penalty`
- THEN el sistema lanza una excepción `PenaltyRemovalNotAllowedError`.

## Non-Functional Requirements
- **RNF-01 [MUST] Concurrency**: DB locks para evitar double-penalty por lag.
- **RNF-02 [MUST] Traceability**: Trazabilidad de cada penalidad aplicada (quién, cuándo, a quién).
- **RNF-03 [MUST] Timer Sync**: Frontend debe pausar el timer localmente al iniciar flujo de penalidad y sincronizar.
- **RNF-04 [MUST] Scheduling Constraint**: Evitar estado IN_PROGRESS concurrente para el mismo atleta en distintos tatamis.

## Out of Scope
- Penalidades para Kata.
- Sanciones a coaches.