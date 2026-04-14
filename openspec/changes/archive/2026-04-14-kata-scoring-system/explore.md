# Exploration: Kata Scoring System (WKF 2026)

## Source
Official PDF: `docs/WKF Kata Competition Rules 2026 MASTER COPY_V2.pdf`  
Articles reviewed: 3.1–3.10, 4.1–4.9, 5.1–5.14, 6.1–6.12, Appendix 2, Appendix 4

---

## 1. Panel de Jueces

### Composición (Art. 4.1, 4.9)

| Formato | Jueces |
|---------|--------|
| Eliminación | 5 jueces (electrónico) |
| Round-Robin | 7 jueces (electrónico) |
| Medallas | 7 jueces (electrónico) |
| Sin sistema electrónico | 5 jueces + banderas manuales |

- No hay "Árbitro/Referee" en Kata → el panel es exclusivamente de **Jueces** (Judges).
- Un juez es designado **Tatami Manager** por competición (no tiene rol distinto en puntuación).
- Art. 4.8: jueces no pueden ser de la misma NF que algún competidor.

### Diferencia con Kumite
En Kumite: 1 Árbitro central + jueces. En Kata: **solo panel de jueces**, ninguno con autoridad de árbitro. El Tatami Manager coordina logística, no arbitraje.

---

## 2. Sistema de Puntuación Numérica (Art. 5.4, 5.5)

### Escala (Art. 5.4.1)
- Rango: **5.0 a 10.0** en incrementos de **0.1**
- 5.0 = desempeño mínimo aceptado
- 10.0 = perfección
- 0.0 = descalificación

### Guía de aplicación (Art. 5.5.3)
| Rango | Calidad |
|-------|---------|
| 10 | Perfecto |
| 9.0 – 9.9 | Excelente |
| 8.0 – 8.9 | Muy bueno |
| 7.0 – 7.9 | Bueno |
| 6.0 – 6.9 | Aceptable |
| 5.0 – 5.9 | Insuficiente |
| 0.0 | Descalificado |

### Cálculo del Ganador (Art. 5.4.2, 5.5.1)
- **NO hay promedio publicado** como dato primario del ganador.
- Cada juez vota al ganador relativo (basado en su propio puntaje comparado entre AKA y AO).
- El ganador se determina por **mayoría de votos** de jueces.
- Round-Robin: ganador obtiene **3 Victory Points** (VP), perdedor 0 VP (Art. 5.5.2).
- No se permiten empates (Art. 5.5.2: "No draws are allowed").

### Implicación clave
La app necesita: (1) registrar score numérico de cada juez para cada performer, (2) derivar el voto de cada juez comparando sus dos scores, (3) contar mayoría de votos para determinar ganador.

---

## 3. Sistema de Banderas FLAG (Art. 5.14)

### Cuándo aplica
- Solo cuando **NO hay sistema electrónico disponible** (Art. 5.14.1).
- Alternativa de contingencia — no modo principal.

### Procedimiento (Art. 5.14.2)
1. Ambos AKA y AO completan su Kata.
2. Head Judge toca silbato → todos los 5 jueces levantan bandera simultáneamente (roja=AKA, azul=AO).
3. Se registran resultados hasta segundo silbato.
4. Resultado: cuenta de banderas determina mayoría.

### Diferencia con modo numérico
- FLAG: 5 jueces, voto directo sin score numérico.
- Numérico: 5 o 7 jueces, score 5.0-10.0, voto derivado del score.

---

## 4. Criterios de Evaluación (Art. 5.6)

### Kata Performance (Individual y Equipos)
1. Stances (posiciones)
2. Techniques (técnicas)
3. Transitional movements (movimientos de transición)
4. Timing and synchronisation (timing y sincronización)
5. Correct breathing (respiración correcta)
6. Focus — KIME
7. Conformance: consistencia con KIHON
8. Strength (fuerza)
9. Speed (velocidad)
10. Balance (equilibrio)

### Bunkai Performance (solo equipos en bouts de medalla)
1. Stances
2. Techniques
3. Transitional movements
4. Timing & distance (MA-AI)
5. Control
6. Focus — KIME
7. Conformance to Kata: usar los movimientos reales del Kata
8. Strength
9. Speed
10. Balance

### Notas
- Bunkai solo aplica en **Team medal matches** (Art. 5.4.3).
- Bunkai = igual importancia que el Kata (Art. 5.4.3).
- Tiempo máximo combinado Kata + Bunkai = **5 minutos** (Art. 3.5.6).

---

## 5. Reglas de Desempate en Kata

### Individual — Round-Robin (Art. 5.11)
En orden de precedencia:
1. Mayor cantidad de **Victory Points** (bouts ganados).
2. Ganador del bout **entre los atletas empatados**.
3. Mayor **suma de votos** de jueces (de todos los bouts del grupo).
4. Mayor **World Ranking**.
5. **Extra Kata**: atleta adicional si aún hay empate.
→ Para cada caso de empate: **volver al criterio 2**.

### Equipos — Round-Robin (Art. 5.12)
1. Mayor Victory Points.
2. Ganador del match entre equipos empatados.
3. Mayor suma de votos.
4. Extra Kata.
→ Volver a criterio 2.

### Runner-Ups entre grupos distintos (Art. 5.13)
1. Mayor **diferencia** (votos a favor - votos en contra).
2. Si 3+ empatados: los 2 con mayor ranking avanzan.
3. Extra Kata si sigue el empate.

### Eliminación (Art. 5.10)
- Ganador: mayor suma de votos de jueces (mayoría simple de 5 o 7).

### KIKEN (no presentación)
- El oponente gana con **4 votos** (Art. 5.11 nota al pie).

---

## 6. Kata Individual vs. Kata por Equipos

| Aspecto | Individual | Equipos |
|---------|------------|---------|
| Competidores | 1 | 3 de 4 (Art. 3.5.1) |
| Bunkai | Solo en medallas (opcional por reglamento) | Obligatorio en medal matches (Art. 3.5.4) |
| Tiempo | Sin límite explícito para Kata solo | 5 min combinado Kata+Bunkai (Art. 3.5.6) |
| Sincronización | N/A | Criterio de evaluación (timing & sync) |
| Jueces | 5 (elim) / 7 (RR) | Mismo |
| Desempate RR | Art. 5.11 (con WR) | Art. 5.12 (sin WR) |
| SHIKKAKU | Descalifica al atleta | Puede descalificar al equipo |
| Disq. técnica (3.7.10) | Extra kata | Extra kata sin Bunkai |

---

## 7. Modelos Nuevos Necesarios vs Existentes

### Modelos EXISTENTES que se reutilizan

| Modelo | Uso en Kata |
|--------|-------------|
| `TournamentCategory` | `modality=KATA_INDIVIDUAL/KATA_TEAM`, `judge_panel_size`, `scoring_type`, `flag_count` |
| `Match` | Estructura del bout/match (AKA vs AO) |
| `MatchScore` | Registra score numérico por juez — **campo score_value (float) ya existe** |
| `Referee` | Usado como "Juez" en Kata (mismo modelo, diferente rol) |

### Campos EXISTENTES útiles en `TournamentCategory`
- `judge_panel_size: int` (3 o 5 actualmente, necesita soportar 5 y 7)
- `scoring_type: Optional[str]` (STANDARD, FLAG)
- `flag_count: Optional[int]` (1-3 flags, para modo FLAG)
- `has_bunkai: bool`

### Gaps en modelos existentes

#### Gap 1: `MatchScore` — estructura inadecuada para Kata
**Actual**: `MatchScore` tiene `participant` (AKA/AO), `score_type` (IPPON/WAZA_ARI/YUKO...), `score_value`.  
**Kata necesita**: score numérico (5.0–10.0) **por performer** (AKA o AO) **por juez**.  
→ El campo `score_value: float` sirve. El `score_type` no aplica (Kata no tiene tipos). Se puede usar con `score_type=KATA_SCORE` nuevo enum.

#### Gap 2: No existe `KataMatchScore` ni forma de registrar el **voto** derivado
La app necesita almacenar:
- `score_aka: float` — puntaje del juez para AKA
- `score_ao: float` — puntaje del juez para AO  
- `vote: str` — AKA | AO (derivado de comparación)

Opciones:
- A) Reutilizar `MatchScore` con dos registros por juez (uno para AKA, uno para AO) + derivar voto en servicio.
- B) Crear nuevo modelo `KataJudgeScore` con `score_aka`, `score_ao`, `vote`, `judge_id`, `match_id`.

#### Gap 3: Match no tiene campo para **Victory Points** acumulados
En Round-Robin, atleta acumula VP a través de múltiples bouts. Match individual gana 3 VP.  
→ `TournamentCategory` o un modelo auxiliar necesita acumular VP por atleta/equipo.

#### Gap 4: No existe `KataRoundResult` (resultados por ronda)
Para desempate necesitamos historial de votos por bout por atleta en todo el grupo.

#### Gap 5: `judge_panel_size` acepta 3 — en WKF Kata debe ser 5 o 7
Actualmente el campo existe pero acepta 3. Validación a corregir.

#### Gap 6: Kata por equipos — sin modelo de Equipo como "participante" del Match
`Match.aka_id` y `Match.ao_id` apuntan a `athletes.id`. Para Kata equipos necesitamos `Match.aka_team_id` y `Match.ao_team_id`.  
→ Ya existe `Team` model. Match no tiene `aka_team_id/ao_team_id`.

---

## 8. Gaps Clave: Existente vs Requerido

| # | Gap | Severidad | Solución |
|---|-----|-----------|---------|
| G1 | `MatchScore` no modela score-por-juez-por-performer bidireccional | ALTA | Nuevo modelo `KataJudgeScore` |
| G2 | No hay tracking de Victory Points por atleta/equipo en RR | ALTA | Campo o modelo auxiliar `KataRoundStanding` |
| G3 | `Match.aka_id/ao_id` solo soporta atleta individual | MEDIA | Agregar `aka_team_id`, `ao_team_id` nullable |
| G4 | `ScoreType` enum no tiene valor Kata | BAJA | Agregar `KATA_SCORE = "KATA_SCORE"` |
| G5 | `judge_panel_size` no valida 5 o 7 en Kata | BAJA | Validación en servicio Kata |
| G6 | No existe `KataScoringService` | ALTA | Crear nuevo servicio |
| G7 | No existe lógica de desempate Kata (WR, VP, extra kata) | ALTA | En `KataScoringService` |
| G8 | FLAG mode no tiene flujo implementado | MEDIA | Variante en `KataScoringService` |
| G9 | Bunkai no tiene tracking de tiempo (5 min) | MEDIA | Campo en Match o en servicio |
| G10 | Extra Kata (desempate final) no tiene flujo | BAJA | Estado especial en Match |

---

## Current State Summary

### Qué funciona ya para Kata
- `TournamentCategory` tiene campos Kata: `scoring_type`, `flag_count`, `has_bunkai`, `judge_panel_size`.
- `Match` estructura bout AKA vs AO — suficiente para individual.
- `MatchScore` puede registrar scores numéricos (score_value float).
- `Referee` model ya existe para jueces.
- Modality enum ya tiene `KATA_INDIVIDUAL` y `KATA_TEAM`.

### Qué NO existe
- `KataJudgeScore` model (score por juez, para AKA y AO, con voto).
- `KataRoundStanding` o equivalente (Victory Points en RR).
- `KataScoringService` (lógica de scoring, votación, desempate).
- `Match` con soporte de equipos (aka_team_id, ao_team_id).
- Validación de `judge_panel_size` = 5 o 7 para Kata.

---

## Recommendation

**Approach A — Modelo dedicado `KataJudgeScore` + Servicio nuevo**

```
KataJudgeScore (nuevo modelo):
  match_id → matches.id
  judge_id → referees.id
  applied_by_id → users.id (quién registró en app)
  score_aka: float  # 5.0–10.0 o 0.0
  score_ao: float   # 5.0–10.0 o 0.0
  vote: str         # AKA | AO (derivado, persistido para auditoría)
  is_flag_mode: bool
  created_at: datetime

KataRoundStanding (nuevo modelo):
  category_id → tournament_categories.id
  athlete_id → athletes.id (nullable)
  team_id → teams.id (nullable)
  victory_points: int = 0
  total_votes_for: int = 0
  total_votes_against: int = 0
  world_ranking: Optional[int]
  round_number: int

KataScoringService (nuevo servicio):
  - record_judge_score(match_id, judge_id, score_aka, score_ao) → KataScoringResult
  - finalize_bout(match_id) → BoutResult  # calcula mayoría de votos
  - get_round_standings(category_id) → list[KataRoundStanding]
  - resolve_tiebreaker(category_id, athlete_ids) → TiebreakerResult
  - record_flag_vote(match_id, judge_id, vote: AKA|AO) → FlagResult
```

**Pros**: Separación limpia, no rompe Kumite, full auditabilidad.  
**Cons**: 2 migraciones nuevas, más complejidad.  
**Effort**: Medium-High.

**Approach B — Reutilizar `MatchScore` con convención**

Usar 2 registros por juez: uno `participant=AKA`, otro `participant=AO`.  
Agregar campo `score_type=KATA_SCORE`. Derivar voto en servicio.

**Pros**: Menos modelos nuevos.  
**Cons**: Semántica confusa, VP tracking igual necesita modelo nuevo, difícil de auditar.  
**Effort**: Medium.

**→ Recomendación: Approach A.** Mismo patrón que `kumite_scoring_service.py` — servicio dedicado con modelos propios. Mantiene limpieza arquitectural.

---

## Affected Areas

- `kakumi_app/models/tournament_model.py` — agregar `ScoreType.KATA_SCORE`, posiblemente `aka_team_id/ao_team_id` en Match
- `kakumi_app/models/kata_model.py` (NUEVO) — `KataJudgeScore`, `KataRoundStanding`
- `kakumi_app/services/kata_scoring_service.py` (NUEVO) — `KataScoringService`
- `alembic/versions/` — 1-2 migraciones nuevas
- `tests/test_kata_scoring.py` (NUEVO) — suite de pruebas

---

## Risks

- **R1**: Kata equipos requiere `Match` con team refs — cambio en modelo base compartido con Kumite.
- **R2**: Desempate por World Ranking requiere dato externo — necesita campo en `Athlete` o `TournamentCategory`.
- **R3**: Extra Kata como mecanismo de desempate no tiene estado claro en `MatchStatus` actual.
- **R4**: `judge_panel_size=7` (Round-Robin WKF) puede no ser soportado en UI existente.

---

## Ready for Proposal
**Yes** — hallazgos suficientes para definir alcance, modelos y servicio.

**Siguiente fase sugerida**: `sdd-propose` → Definir scope, alcance v1 (individual eliminación first), roadmap para RR y equipos.
