# WKF Shikkaku Rules - Extractos Literales

## Artículo 3.7.3 (WKF Kumite Competition Rules 2026)

> **ARTICLE 3: REFEREEING**
>
> **3.7. In case the number of competitors in the Round-robin reduces to 3 for any reason, the following rules apply:**
>
> 3.7.1. When the competition has already started, and the number of competitors reduces to 3, the competition continues until the round-robin is finalised. The athlete who had already competed with the eliminated athlete will have their match results annulled, and the results of athletes competing after are not counted.
>
> 3.7.2. In case the number of competitors in the Round-robin reduces to 2 for any reason, the matches are concluded, and the winner and runner-up are decided by Hantei.
>
> **3.7.3. If an individual is disqualified or is unable to complete all bouts in the Round-robin, the scores of completed or current bouts will be nullified, and their victory points forfeited, unless it is the last bout of the Round-robin, in which case, all previous results and points remain unchanged.**

### Cita Textual Exacta (Art. 3.7.3)

> "If an individual is disqualified or is unable to complete all bouts in the Round-robin, the scores of completed or current bouts will be nullified, and their victory points forfeited, unless it is the last bout of the Round-robin, in which case, all previous results and points remain unchanged."

---

## Artículo 10.7.2 - SHIKKAKU Definition

> **ARTICLE 10: PROHIBITED BEHAVIOUR**
>
> 10.7. SHIKKAKU is imposed when a contestant commits an act which harms the prestige and honour of Karate-Do or when any other act is considered to violate the rules and purposes of the tournament.
>
> 10.7.1. Shikkaku infers the total disqualification from the event and the tournament and future WKF events. Shikkaku is invoked when a contestant:
> - a) Does not obey the instructions of the Referee Panel
> - b) Conducts himself/herself in a manner which harms the prestige and honour of Karate-Do
> - c) Commits other acts which are considered to violate the rules and purposes of the tournament
>
> 10.7.2. **In team matches, when a contestant is given Shikkaku, the opponent's score will be set to 8-0, and the match will be recorded as a win for the opponent. The team of the disqualified contestant will be withdrawn from the tournament, and the scores of previous matches will be nullified.**

---

## Aclaración

### SHIKKAKU en Round-Robbin - Bifurcación de Comportamiento

El Artículo 3.7.3 establece una **excepción crítica**: el tratamiento de los resultados previos depende de si la descalificación ocurre en el **último encuentro** del competidor o no.

| Escenario | Resultados Previos | Puntos de Victoria |
|-----------|---------------------|-------------------|
| SHIKKAKU en ÚLTIMO bout del RR | Se MANTIENEN | Se conservan |
| SHIKKAKu en NO-último bout | Se ANULAN | Se pierden |

**Implicancia de diseño**: El sistema debe determinar si el bout actual es el último del competidor descalificado en el RR para decidir qué hacer con los resultados anteriores.

### SHIKKAKU en Equipos (Art. 10.7.2)

Cuando un competidor recibe SHIKKAKU en match de equipos:
1. Score del oponente → 8-0
2. Match → WIN para oponente
3. **Equipo** del descalificado → retirado del torneo
4. Scores de matches previos → anulados

**Nota**: Art. 10.7.2 dice "scores of previous matches will be nullified" sin la excepción del último encuentro. Esto difiere de 3.7.3.

---

## Nota de Corrección

> **CORRECCIÓN**: La memoria previa en `openspec/changes/penalty-system/explore.md` (líneas 98-103) indicaba incorrectamente que el Artículo 3.7.3 no existía en el reglamento de Kumite. Esta afirmación era **errónea**.
>
> El Artículo 3.7.3 **SÍ ESTÁ PRESENTE** en el WKF 2026 Kumite Competition Rules y establece explícitamente la regla de anulación de scores en caso de descalificación durante Round-Robbin, con la excepción del último bout.
>
> **Acción tomada**: Actualizada la observación en Engram con el contenido correcto del Art. 3.7.3 y la bifurcación de comportamiento correspondiente.

---

## Referencias Cruzadas Relevantes

| Artículo | Contexto | Aplicación |
|----------|----------|------------|
| 3.7.1 | RR reduce a 3 competidores | Anula resultados del que ya compitió con eliminado |
| 3.7.3 | Descalificación en RR | Anula scores salvo último bout |
| 10.7.2 | SHIKKAKU en equipos | Retira equipo, anula scores previos |
| 10.6 | HANSOKU | Termina match, YUKO al rival |
| 3.6 | Ganador por penalización | Decisión por HANSOKU/SHIKKAKU |

---

## Fuente

- **Documento**: WKF 2026 Kumite Competition Rules MASTER COPY_V11.pdf
- **Ubicación**: `/var/home/yhoxr/Documentos/kakumi-app/docs/`
- **Fecha extracción**: 2026-04-16