# KAKUMI TOURNAMENT MANAGER - Technical Specifications

---

## 1. Descripción General

### 1.1 Propósito

Aplicación web para la gestión completa de torneos de Karate-Do, implementando estrictamente el Reglamento Oficial de Competición WKF 2026 vigente. El sistema abarca desde la inscripción de atletas hasta la generación de resultados oficiales, incluyendo arbitraje, puntuación en tiempo real y visualización de brackets.

### 1.2 Tecnologías Principales

| Componente    | Tecnología                              |
| ------------- | --------------------------------------- |
| Lenguaje      | Python 3.10+                            |
| Framework     | Reflex (frontend y backend 100% Python) |
| Base de Datos | SQLite con SQLModel                     |
| Migraciones   | Alembic                                 |
| Frontend      | Componentes Reflex (sin JS/TS manual)   |

### 1.3 Alcance Funcional

- Gestión integral de atletas, árbitros y torneos
- Sistemas de puntuación para Kata y Kumite según WKF 2026
- Generación automática de brackets y emparejamientos
- Pantalla de puntuación en tiempo real para monitores externos
- Importación y exportación de datos en formatos CSV/JSON
- Sistema de roles y autenticación

---

## 2. Modelos de Datos

### 2.1 Atleta (Athlete)

#### 2.1.1 Estructura de Datos

| Campo            | Tipo        | Requerido | Descripción                                                                                 |
| ---------------- | ----------- | --------- | ------------------------------------------------------------------------------------------- |
| `id`             | Integer     | Sí        | Identificador único autoincremental                                                         |
| `name`           | String(255) | Sí        | Nombre completo del atleta                                                                  |
| `email`          | String(255) | No        | Correo electrónico único                                                                    |
| `date_of_birth`  | Date        | Sí        | Fecha de nacimiento                                                                         |
| `gender`         | Enum        | Sí        | MALE / FEMALE                                                                               |
| `weight_kg`      | Float       | No        | Peso en kilogramos (para categorías de Kumite)                                              |
| `belt_rank`      | String(50)  | No        | Grado/cinturón (ej: "Kyu 1", "Dan 3", o colores de "Blanco" a "Negro" para mayor facilidad) |
| `dojo`           | String(255) | No        | Dojo o asociación a la que pertenece                                                        |
| `nationality`    | String(3)   | No        | Código de país ISO 3166-1 alpha-3                                                           |
| `license_number` | String(50)  | No        | Número de licencia WKF o federal                                                            |
| `is_active`      | Boolean     | Sí        | Indica si el atleta puede competir                                                          |
| `created_at`     | DateTime    | Sí        | Fecha de creación del registro                                                              |
| `updated_at`     | DateTime    | Sí        | Fecha de última modificación                                                                |

#### 2.1.2 Relaciones

- Un atleta puede pertenecer a una categoría de Kata (relación opcional)
- Un atleta puede pertenecer a una categoría de Kumite (relación opcional)
- Un atleta puede ser miembro de múltiples equipos (relación N:N mediante tabla TeamMember)
- Un atleta puede tener un arbitro asignado (relación 1:1 opcional)

#### 2.1.3 Restricciones

- `name` debe ser único en el sistema
- `email` debe ser único si se proporciona
- `date_of_birth` no puede ser futura
- `weight_kg` debe ser positivo si se proporciona (rango válido: 40.0 - 120.0 kg)

### 2.2 Equipo (Team)

#### 2.2.1 Estructura de Datos

| Campo          | Tipo        | Requerido | Descripción                                       |
| -------------- | ----------- | --------- | ------------------------------------------------- |
| `id`           | Integer     | Sí        | Identificador único autoincremental               |
| `name`         | String(255) | Sí        | Nombre del equipo                                 |
| `dojo`         | String(255) | No        | Dojo o asociación representada                    |
| `category_id`  | Integer     | Sí        | Foreign key a KataCategory                        |
| `member_count` | Integer     | Sí        | Número de miembros activos (3-8 para competencia) |
| `is_active`    | Boolean     | Sí        | Indica si el equipo puede competir                |
| `created_at`   | DateTime    | Sí        | Fecha de creación                                 |

#### 2.2.2 Miembros de Equipo (TeamMember - Tabla de intersección)

| Campo        | Tipo    | Requerido | Descripción                    |
| ------------ | ------- | --------- | ------------------------------ |
| `id`         | Integer | Sí        | Identificador único            |
| `team_id`    | Integer | Sí        | Foreign key a Team             |
| `athlete_id` | Integer | Sí        | Foreign key a Athlete          |
| `position`   | Integer | Sí        | Orden de participación (1-8)   |
| `is_reserve` | Boolean | Sí        | Indica si es titular o reserva |

#### 2.2.3 Restricciones

- Un equipo debe tener entre 3 y 8 miembros para competir
- Los miembros deben cumplir requisitos de edad de la categoría
- Un atleta solo puede pertenecer a un equipo por categoría

### 2.3 Torneo (Tournament)

#### 2.3.1 Estructura de Datos

| Campo                   | Tipo        | Requerido | Descripción                                                                  |
| ----------------------- | ----------- | --------- | ---------------------------------------------------------------------------- |
| `id`                    | Integer     | Sí        | Identificador único autoincremental                                          |
| `name`                  | String(255) | Sí        | Nombre oficial del torneo                                                    |
| `description`           | Text        | No        | Descripción o bases del torneo                                               |
| `venue`                 | String(255) | Sí        | Lugar de realización                                                         |
| `start_date`            | Date        | Sí        | Fecha de inicio                                                              |
| `end_date`              | Date        | Sí        | Fecha de finalización                                                        |
| `status`                | Enum        | Sí        | PLANIFICADO / INSCRIPCION / VERIFICACION / EN_CURSO / FINALIZADO / ARCHIVADO |
| `organizing_federation` | String(255) | No        | Federación organizadora                                                      |
| `license_number`        | String(50)  | No        | Número de licencia del evento                                                |
| `tatami_count`          | Integer     | Sí        | Número de tatamis disponibles (1-8)                                          |
| `is_public`             | Boolean     | Sí        | Visible para espectadores                                                    |
| `viewer_code`           | String(8)   | No        | Código para acceso de espectadores                                           |
| `created_by`            | Integer     | Sí        | Foreign key a User                                                           |
| `created_at`            | DateTime    | Sí        | Fecha de creación                                                            |
| `updated_at`            | DateTime    | Sí        | Fecha de última modificación                                                 |

#### 2.3.2 Estados del Torneo

```
PLANIFICADO -> INSCRIPCION -> VERIFICACION -> EN_CURSO -> FINALIZADO -> ARCHIVADO
     ^            |              |             |            |
     |            v              v             v            v
     +------------+--------------+-------------+------------+
                    (retroceso permitido con validación)
```

### 2.4 Categoría (Category)

#### 2.4.1 Categoría Base (BaseCategory)

| Campo                | Tipo        | Requerido | Descripción                                                   |
| -------------------- | ----------- | --------- | ------------------------------------------------------------- |
| `id`                 | Integer     | Sí        | Identificador único                                           |
| `name`               | String(255) | Sí        | Nombre de la categoría                                        |
| `tournament_id`      | Integer     | Sí        | Foreign key a Tournament                                      |
| `modality`           | Enum        | Sí        | KATA_INDIVIDUAL / KATA_TEAM / KUMITE_INDIVIDUAL / KUMITE_TEAM |
| `gender`             | Enum        | Sí        | MALE / FEMALE / MIXED                                         |
| `min_age`            | Integer     | Sí        | Edad mínima (inclusive)                                       |
| `max_age`            | Integer     | Sí        | Edad máxima (inclusive)                                       |
| `min_belt_rank`      | String(10)  | No        | Grado mínimo (ej: "Kyu 3", "Dan 1")                           |
| `max_belt_rank`      | String(10)  | No        | Grado máximo                                                  |
| `min_weight_kg`      | Float       | No\*      | Peso mínimo (solo Kumite)                                     |
| `max_weight_kg`      | Float       | No\*      | Peso máximo (solo Kumite)                                     |
| `competition_system` | Enum        | Sí        | ROUND_ROBIN / ELIMINATION / DOUBLE_ELIMINATION                |
| `bracket_size`       | Integer     | Sí        | Tamaño del bracket (4, 8, 16, 32)                             |
| `status`             | Enum        | Sí        | PENDING / READY / IN_PROGRESS / COMPLETED                     |
| `first_place_id`     | Integer     | No        | Foreign key a Athlete/Team (ganador)                          |
| `second_place_id`    | Integer     | No        | Foreign key a Athlete/Team (subcampéon)                       |
| `third_place_ids`    | JSON        | No        | Array de IDs para terceros lugares                            |
| `created_at`         | DateTime    | Sí        | Fecha de creación                                             |

\*Requerido para categorías de Kumite individual

#### 2.4.2 KataCategory (hereda de BaseCategory)

| Campo              | Tipo    | Requerido | Descripción                        |
| ------------------ | ------- | --------- | ---------------------------------- |
| `flag_count`       | Integer | Sí        | Cantidad de flags a realizar (1-3) |
| `has_bunkai`       | Boolean | Sí        | Indica si incluye Bunkai           |
| `judge_panel_size` | Integer | Sí        | Número de jueces (3 o 5)           |
| `scoring_type`     | Enum    | Sí        | STANDARD / FLAG                    |

#### 2.4.3 KumiteCategory (hereda de BaseCategory)

| Campo                        | Tipo    | Requerido | Descripción                                 |
| ---------------------------- | ------- | --------- | ------------------------------------------- |
| `match_duration_seconds`     | Integer | Sí        | Duración del encuentro (180-300)            |
| `extension_duration_seconds` | Integer | Sí        | Duración de extensión/Golden Point (60-180) |
| `has_weight_tolerance`       | Boolean | Sí        | Indica si permite tolerancia de peso        |
| `weight_tolerance_kg`        | Float   | No        | Tolerancia de peso en kg                    |

### 2.5 Encuentro (Match)

#### 2.5.1 Estructura de Datos

| Campo            | Tipo     | Requerido | Descripción                                              |
| ---------------- | -------- | --------- | -------------------------------------------------------- |
| `id`             | Integer  | Sí        | Identificador único                                      |
| `category_id`    | Integer  | Sí        | Foreign key a Category                                   |
| `round`          | Integer  | Sí        | Ronda del bracket (1=primera, 2=cuartos, etc.)           |
| `match_number`   | Integer  | Sí        | Número de encuentro dentro de la ronda                   |
| `position`       | Integer  | Sí        | Posición en el bracket                                   |
| `match_type`     | Enum     | Sí        | ELIMINATION / BRONZE / FINAL / ROUND_ROBIN               |
| `aka_id`         | Integer  | Sí\*      | Foreign key a Athlete/Team (Rojo)                        |
| `ao_id`          | Integer  | Sí\*      | Foreign key a Athlete/Team (Azul)                        |
| `aka_score`      | Integer  | Sí        | Puntuación total de Aka                                  |
| `ao_score`       | Integer  | Sí        | Puntuación total de Ao                                   |
| `winner_id`      | Integer  | No        | Foreign key a Athlete/Team                               |
| `status`         | Enum     | Sí        | PENDING / READY / IN_PROGRESS / COMPLETED / DISQUALIFIED |
| `start_time`     | DateTime | No        | Hora de inicio del encuentro                             |
| `end_time`       | DateTime | No        | Hora de finalización                                     |
| `tatami_id`      | Integer  | No        | Foreign key a Tatami                                     |
| `referee_id`     | Integer  | No        | Árbitro principal asignado                               |
| `judge_panel_id` | Integer  | No        | Panel de jueces asignado                                 |
| `notes`          | Text     | No        | Notas u observaciones                                    |

\*Solo uno requerido: para-bye, ambos requeridos para combate

#### 2.5.2 Estados del Encuentro

```
PENDING -> READY -> IN_PROGRESS -> COMPLETED
                |                 |
                v                 v
           DISQUALIFIED <--------+
```

### 2.6 Puntuación de Encuentro (MatchScore)

#### 2.6.1 Estructura de Datos

| Campo            | Tipo     | Requerido | Descripción                                            |
| ---------------- | -------- | --------- | ------------------------------------------------------ |
| `id`             | Integer  | Sí        | Identificador único                                    |
| `match_id`       | Integer  | Sí        | Foreign key a Match                                    |
| `participant`    | Enum     | Sí        | AKA / AO                                               |
| `judge_id`       | Integer  | Sí        | Foreign key a Judge                                    |
| `score_value`    | Float    | Sí        | Puntuación otorgada                                    |
| `score_type`     | Enum     | Sí        | En Kumite: IPPON / WAZA_ARI / YUKO / PENALTY / WARNING |
| `technique_time` | Integer  | No        | Tiempo del combate cuando se marcó (segundos)          |
| `is_valid`       | Boolean  | Sí        | Validado por el árbitro                                |
| `created_at`     | DateTime | Sí        | Fecha de registro                                      |

### 2.7 Árbitro (Referee)

#### 2.7.1 Estructura de Datos

| Campo              | Tipo        | Requerido | Descripción                                   |
| ------------------ | ----------- | --------- | --------------------------------------------- |
| `id`               | Integer     | Sí        | Identificador único                           |
| `name`             | String(255) | Sí        | Nombre completo                               |
| `license_number`   | String(50)  | Sí        | Número de licencia de arbitraje               |
| `license_level`    | Enum        | Sí        | NATIONAL / INTERNATIONAL                      |
| `role`             | Enum        | Sí        | REFEREE / JUDGE / TABLE_OFFICIAL / SUPERVISOR |
| `tatami_certified` | JSON        | No        | Array de tatamis certificados                 |
| `is_available`     | Boolean     | Sí        | Disponible para asignación                    |
| `dojo`             | String(255) | No        | Dojo o federación representada                |
| `email`            | String(255) | No        | Correo electrónico                            |
| `phone`            | String(20)  | No        | Teléfono de contacto                          |

#### 2.7.2 Roles de Árbitros

| Rol            | Abreviatura | Descripción                                |
| -------------- | ----------- | ------------------------------------------ |
| REFEREE        | RF          | Árbitro principal, inicia/detiene combate  |
| JUDGE          | JD          | Juez de kata o kumite, otorga puntuaciones |
| TABLE_OFFICIAL | TO          | Oficial de mesa, gestiona datos            |
| SUPERVISOR     | SP          | Supervisor general del tatami              |

### 2.8 Penalización (Penalty)

#### 2.8.1 Estructura de Datos

| Campo                | Tipo        | Requerido | Descripción                              |
| -------------------- | ----------- | --------- | ---------------------------------------- |
| `id`                 | Integer     | Sí        | Identificador único                      |
| `match_id`           | Integer     | Sí        | Foreign key a Match                      |
| `participant`        | Enum        | Sí        | AKA / AO / BOTH                          |
| `penalty_type`       | Enum        | Sí        | CHUI / HANSOKU_CHUI / HANSOKU / SHIKKAKU |
| `reason`             | String(255) | Sí        | Razón de la penalización                 |
| `rule_reference`     | String(50)  | No        | Referencia al artículo WKF               |
| `is_accumulated`     | Boolean     | Sí        | Indica si es por acumulación             |
| `given_by`           | Integer     | Sí        | Foreign key a Referee                    |
| `match_time_seconds` | Integer     | No        | Tiempo del combate cuando se impuso      |
| `created_at`         | DateTime    | Sí        | Fecha de registro                        |

### 2.9 Usuario (User)

#### 2.9.1 Estructura de Datos

| Campo           | Tipo        | Requerido | Descripción               |
| --------------- | ----------- | --------- | ------------------------- |
| `id`            | Integer     | Sí        | Identificador único       |
| `username`      | String(50)  | Sí        | Nombre de usuario único   |
| `email`         | String(255) | Sí        | Correo electrónico único  |
| `password_hash` | String(255) | Sí        | Hash de contraseña        |
| `full_name`     | String(255) | Sí        | Nombre completo           |
| `role`          | Enum        | Sí        | ADMIN / OPERATOR / VIEWER |
| `is_active`     | Boolean     | Sí        | Cuenta activa             |
| `last_login`    | DateTime    | No        | Último acceso             |
| `created_at`    | DateTime    | Sí        | Fecha de creación         |

### 2.10 Tatami (TournamentArea)

#### 2.10.1 Estructura de Datos

| Campo              | Tipo        | Requerido | Descripción                |
| ------------------ | ----------- | --------- | -------------------------- |
| `id`               | Integer     | Sí        | Identificador único        |
| `tournament_id`    | Integer     | Sí        | Foreign key a Tournament   |
| `name`             | String(50)  | Sí        | Nombre (ej: "Tatami 1")    |
| `location`         | String(255) | No        | Ubicación dentro del venue |
| `is_active`        | Boolean     | Sí        | En uso                     |
| `current_match_id` | Integer     | No        | Encuentro activo           |

---

## 3. Sistema de Puntuación (WKF 2026)

### 3.1 Puntuación en Kumite

#### 3.1.1 Valores de Puntuación

| Técnica  | Valor | Abreviatura | Descripción                                                                                          |
| -------- | ----- | ----------- | ---------------------------------------------------------------------------------------------------- |
| Ippon    | 3     | IPPON       | Técnica perfecta, patada a la cabeza/cuello, o proyecciones al suelo seguidas de una técnica de mano |
| Waza-ari | 2     | WAZA ARI    | Patada puntuable al área válida (chudan)                                                             |
| Yuko     | 1     | YUKO        | Golpe de puño al área válida (chudan o jodan)                                                        |

#### 3.1.2 Criterios de Validez

Una técnica debe cumplir TODOS los siguientes requisitos:

- **Buena forma**: Técnica con características de karate tradicional.
- **Actitud deportiva**: Comportamiento no malicioso.
- **Aplicación vigorosa**: Fuerza y velocidad en la técnica.
- **Zanshin**: Conciencia situacional y preparación para continuar.
- **Tiempo apropiado**: Ejecución en el momento preciso.
- **Distancia correcta**: Ejecución a la distancia adecuada.

Estas técnicas solo serán evaluadas de forma física por los árbitros.

#### 3.1.3 Proceso de Puntuación

```
1. Juez observa y marca técnica válida (banderín)
2. Referee evalúa y confirma o rechaza
3. Si confirma, se registra el punto
4. Sistema actualiza puntuación en tiempo real
5. Al finalizar tiempo, se declara ganador
```

### 3.2 Puntuación en Kata

#### 3.2.1 Escala de Puntuación

| Rango     | Puntuación | Descripción                          |
| --------- | ---------- | ------------------------------------ |
| Excelente | 10.0 - 8.0 | Ejecución perfecta, espíritu fuerte  |
| Muy bueno | 7.9 - 7.0  | Pequeños errores, técnica sólida     |
| Bueno     | 6.9 - 6.0  | Errores moderados, comprensión clara |
| Regular   | 5.9 - 5.0  | Errores significativos               |

#### 3.2.2 Sistema de Decisión por Mayoría

Para determinar el ganador de un encuentro de Kata:

1. **Con panel de 5 jueces**:
   - Se eliminan la puntuación más alta y la más baja
   - Se promedia las 3 puntuaciones restantes
   - Gana quien tenga el promedio mayor

2. **Con panel de 3 jueces**:
   - Se promedian las 3 puntuaciones directamente
   - En caso de empate, decide el árbitro principal

3. **Sistema de Banderas (Flag) físico**:
   - Cada juez levanta bandera por el atleta que considere ganador
   - Gana quien obtenga mayoría (3 de 5, o 2 de 3)

4. **Sistema de Banderas (Flag) virtual con votos**:
   - En una eliminatoria por llaves, cada juez da su puntuación luego de que un competidos haya terminado su Kata.
   - Gana quien obtenga la puntuación más favorable de cada juez (por ejemplo, AKA obtuvo 9.1, 9.3, 9.3, 9.2 y 9.0 y AO obtuvo 9.2, 9.2, 9.2, 9.1 y 9.3. Ya que tres jueces terminaron teniendo una puntuación favorable a AKA, mientras que dos jueces tuvieron una puntuación más favorable a AO, gana AKA por mayoría de puntuaciones favorables.)

#### 3.2.3 Modo de Todos Contra Todos informal

- En este modo, siempre se utiliza el sistema de puntuación por panel de 5 jueces (ver Sistema 1 del punto 3.2.2). Los participantes de la categoría pasan uno por uno a ejecutar su respectivo Kata, y los jueces dan sus respectivas puntuaciones a cada atleta y se registran en una tabla.

- El podio (1°, 2° y 3° puesto) de la categoría se define del que haya obtenido el mayor promedio en la tabla.

## 4. Sistema de Penalidades (WKF 2026)

### 4.1 Tipos de Penalización

#### 4.1.1 Penalizaciones Leves (warnings)

| Tipo            | Código | Descripción                       |
| --------------- | ------ | --------------------------------- |
| **Chui** (注意) | C      | Amonestación por infracción menor |

#### 4.1.2 Penalizaciones Graves

| Tipo                        | Código | Descripción                                                                                                                                |
| --------------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **Hansoku Chui** (犯則注意) | HC     | Infracción grave o cuarta infracción menor. **NO otorga puntos al oponente** - es únicamente una advertencia (warning) de descalificación. |
| **Hansoku** (反則)          | H      | Descalificación del combate actual                                                                                                         |
| **Shikkaku** (失格)         | S      | Descalificación permanente del torneo                                                                                                      |

### 4.2 Infracciones por Categoría

#### 4.2.1 Infracciones en Kumite

Estas infracciones se marcan en el panel de scoring de acuerdo a lo evaluado **de manera presencial por los Jueces**:

| Categoría  | Infracción                                                                                                                     | Penalización                                                                                                                                                                  |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Prohibidas | Técnicas excesivas                                                                                                             | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Golpear zona no válida                                                                                                         | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Técnicas con mano abierta                                                                                                      | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Golpear oponente caído con técnica de patada                                                                                   | HANSOKU                                                                                                                                                                       |
| Prohibidas | Técnicas a la cara con la mano abierta                                                                                         | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Técnicas de derribo peligrosas o prohibidas                                                                                    | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Técnicas ejecutadas después de que el árbitro diga WAKARETE y antes de que diga TSUZUKETE                                      | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Ponerse en riesgo a sí mismo intentando forzar una lesión por parte del oponente o no tomar medidas de autoprotección (MUBOBI) | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Pasividad (no tener intención de realizar técnicas)                                                                            | CHUI/HANSOKU al competidor que va perdiendo, si no hay SENSHU, se penaliza a ambos competidores                                                                               |
| Prohibidas | Clinch, agarres prolongados o empujones                                                                                        | CHUI/HANSOKU                                                                                                                                                                  |
| Prohibidas | Técnicas no controladas o con fuerza desmedida                                                                                 | CHUI/HANSOKU                                                                                                                                                                  |
| Conducción | Evitar combate                                                                                                                 | CHUI/SHIKKAKU (al faltar 15 segundos del combate)                                                                                                                             |
| Conducción | Fingir lesión                                                                                                                  | SHIKKAKU                                                                                                                                                                      |
| Conducción | Salir del tatami (JOGAI)                                                                                                       | CHUI/HANSOKU CHUI (al faltar 15 segundos del combate)/HANSOKU                                                                                                                 |
| Conducción | Conducta antideportiva                                                                                                         | CHUI/SHIKKAKU                                                                                                                                                                 |
| Conducción | Hablar o desobediencia al árbitro                                                                                              | CHUI                                                                                                                                                                          |
| Uniforme   | Karategi incorrecto                                                                                                            | Se le da un máximo de dos minutos al atleta para corregir su Karategi; si excede dicho tiempo, se penaliza con KIKEN al competidor y su oponente es declarado ganador         |
| Uniforme   | Kit protector incorrecto                                                                                                       | Se le da un máximo de dos minutos al atleta para corregir su equipo protector; si excede dicho tiempo, se penaliza con KIKEN al competidor y su oponente es declarado ganador |

#### 4.2.2 Infracciones en Kata

Las siguientes faltas deben ser consideradas **de manera presencial por los jueces**:

| N°  | Penalización                                                                                                                                                                                                                                                                                                  |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Anunciar el Kata antes, durante o después del saludo                                                                                                                                                                                                                                                          |
| 2   | Pérdida menor del equilibrio                                                                                                                                                                                                                                                                                  |
| 3   | Ejecutar un movimiento de manera incorrecta o incompleta (por ejemplo, no ejecutar un bloqueo incorrectamente o una técnica de golpe fuera del objetivo)                                                                                                                                                      |
| 4   | Movimientos asíncronos, como ejecutar una técnica antes de terminar la transición del cuerpo, o en el caso de Kata por Equipos, fallar en la ejecución de un movimiento al unísono                                                                                                                            |
| 5   | Uso de señas auditivas (de cualquier otra persona, incluyendo otros miembros del equipo) para guiar el tempo de la ejecución                                                                                                                                                                                  |
| 6   | Cualquier teatralidad como pisotones con los pies al suelo, golpearse el pecho, brazos o el Karategi, o exhalación inapropiada, deben considerarse faltas grabes por los jueces al evaluar la ejecución de un Kata - al mismo nivel en el que se penalizaría una pérdida significativa o mayor del equilibrio |
| 7   | Kiai incorrecto (el Kiai debe ser corto y concentrado, y en simultáneo con la técnica)                                                                                                                                                                                                                        |
| 8   | Afloje del cinturón hasta el punto de desprenderse completamente de las caderas durante la ejecución                                                                                                                                                                                                          |
| 9   | Pérdidas de tiempo, incluyendo marcha prolongada, saludo de reverencia excesivo, o pausas prolongadas antes de empezar la ejecución, incluyendo el uso de más de los 35 segundos reglamentarios desde que se anuncia el nombre del atleta hasta el primer movimiento después del saludo                       |
| 10  | Causar una lesión por falta de control en la técnica durante el Bunkai (aplica solo para Kata por Equipos)                                                                                                                                                                                                    |
| 11  | Simular inconsciencia durante más de 2 segundos durante el Bunkai (aplica solo para Kata por Equipos)                                                                                                                                                                                                         |

### 4.3 Reglas de Acumulación

#### 4.3.1 Kumite

**Secuencia de acumulación según WKF 2026 Artículo 10:**

```
1ra infracción menor   -> CHUI 1 (amonestación)
2da infracción menor  -> CHUI 2 (segunda amonestación)
3ra infracción menor  -> CHUI 3 (tercera amonestación)
4ta infracción menor  -> HANSOKU CHUI (cuarta amonestación - **ADVERTENCIA DE DESCALIFICACIÓN, SIN PUNTOS**)
5ta infracción menor  -> HANSOKU (descalificación)
```

**Nota importante:** HANSOKU CHUI es exclusivamente una advertencia (warning). NO otorga puntos al oponente. La acumulación de cuatro CHUI resulta en HANSOKU CHUI (advertencia de descalificación), y una quinta infracción resulta en HANSOKU (descalificación).

#### 4.3.2 Kata

```
Deben ser evaluadas físicamente por los jueces.
```

### 4.4 Flujo de Descalificación

```
1. Arbitro identifica infracción grave
2. Arbitro consulta con panel de jueces
3. Se registra la penalización en sistema
4. Se muestra mensaje de descalificación
5. Se actualiza estado del encuentro a DISQUALIFIED
6. Se registra el ganador por defecto
7. Se notifica al atleta/equipo afectado
```

---

## 5. Reglas de Desempate (Tie-Breaking)

### 5.1 Desempate en Kumite

#### 5.1.1 Criterios de Desempate en Kumite Individual en modo de TODOS CONTRA TODOS (en orden)

En casos donde hay un empate entre **dos o más atletas** en un grupo o en el modo de todos contra todos, teniendo el mismo número de **puntos de victoria**, los siguientes criterios serán aplicados en el mismo orden. Esto quiere decir que, **SI** se encuentra un ganador tras aplicar un criterio, los demás **NO TENDRÁN QUE APLICARSE**.

| Orden | Criterio                                                                                                                                                 |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | El que haya ganado el encuentro entre los atletas involucrados en el empate                                                                              |
| 2     | Mayor número total de puntos marcados a favor durante todos los encuentros                                                                               |
| 3     | Menor número total de puntos marcados en contra durante todos los encuentros                                                                             |
| 4     | Mayor número de IPPON marcados a favor durante todos los encuentros                                                                                      |
| 5     | Menor número de IPPON marcados en contra durante todos los encuentros                                                                                    |
| 6     | Mayor número de WAZA ARI marcados a favor durante todos los encuentros                                                                                   |
| 7     | Menor número de WAZA ARI marcados en contra durante todos los encuentros                                                                                 |
| 8     | Mayor puesto en el RANKING MUNDIAL ala fecha de la competición (No aplica para este caso pues es un sistema para torneos regionales)                     |
| 9     | Encuentro extra, se permite HANTEI (Desempate por decisión arbitral basada en el desempeño de los atletas. Debe realizarse físicamente por los árbitros) |

Al realizar las comparaciones, los criterios deben ser aplicados **desde el comienzo de la lista**

#### 5.1.2 Criterios de Desempate en Equipos de Kumite en modo de TODOS CONTRA TODOS (en orden)

En casos donde hay un empate entre **dos o más Equipos** en un grupo o en un modo de todos contra todos, teniendo el mismo múmero de **puntos de victoria**, los siguientes criterios serán aplicados en el siguiente orden. Esto quiere decir que, **SI** el ganador se encuentra tras aplicar un criterio, los demás **NO TENDRÁN QUE APLICARSE**.

| Orden | Criterio                                                                                                                                                                                                                       |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1     | El que haya ganado el encuentro entre los Equipos que hayan quedado en empate                                                                                                                                                  |
| 2     | Mayor número de victorias durante toda la etapa                                                                                                                                                                                |
| 3     | Mayor número de puntos marcados a favor en combates durante toda la etapa                                                                                                                                                      |
| 4     | Menor número de puntos marcados en contra del Equipo durante toda la etapa                                                                                                                                                     |
| 5     | Mayor número de IPPON marcados a favor por el Equipo durante toda la etapa                                                                                                                                                     |
| 6     | Menor número de IPPON marcados en contra del Equipo durante toda la etapa                                                                                                                                                      |
| 7     | Mayor número de WAZA ARI marcados por el Equipo durante toda la etapa                                                                                                                                                          |
| 8     | Menor número de WAZA ARI marcados por el Equipo durante toda la etapa                                                                                                                                                          |
| 9     | Un encuentro adicional entre uno de los miembros de cada Equipo - de ser necesario, se decide por HANTEI (Desempate por decisión arbitral basada en el desempeño de los atletas. Debe realizarse físicamente por los árbitros) |

Al realizar las comparaciones, los criterios deben ser aplicados **desde el comienzo de la lista**

#### 5.1.3 Criterios para decidir un Equipo ganador por medio de eliminación

1. El Equipo ganador es el que haya obtenido la mayor cantidad de encuentros ganados, incluyendo los que se han ganado por SENSHU. Si ambos equipos tienen el mismo número de victorias, entonces el Equipo ganador será el que haya obtenido más puntos.
2. Si ambos Equipos tienen el mismo número de victorias y puntos, entonces se llevará a cabo un encuentro decisivo. Cada Equipo debe nominar a cualquier atleta miembro de su Equipo, sin importar que ese atleta haya peleado en un encuentro previo entre los dos Equipos.
3. Si en el encuentro extra no se determina un ganador por superioridad de puntos, ni por SENSHU, el encuentro extra se decide por HANTEI al igual que en los encuentros individuales. El resultado del HANTEI en este encuentro extra también determinará el resultado del duelo por Equipos.
4. En duelos por Equipos, cuando un Equipo ha ganado suficientes encuentros o marcado suficientes puntos para ser declarado ganador, entonces el duelo se declara terminado, y no se pelearán los encuentros restantes, **excepto** en round-robin o modo de todos contra todos, donde **todos** los encuentros deben llevarse a cabo.
5. En duelos por Equipos, si un miembro del Equipo es descalificado (HANSOKU o SHIKKAKU), su puntuación, si la hay, se reducirá a cero, y la puntuación del oponente será de ocho puntos.

### 5.2 Desempate en Kata

#### 5.2.1 Sistema de Desempate Individual en modo de TODOS CONTRA TODOS

Para determinar el ganador de una categoría individual en modo de TODOS CONTRA TODOS con el sistema de puntuación con banderas virtuales cuando hay un empate, se consideran los siguientes criterios **en orden** para determinar al ganador:

| Orden | Criterio                                                                                                   |
| ----- | ---------------------------------------------------------------------------------------------------------- |
| 1     | Mayor número de puntos obtenidos por encuentros ganados durante toda la categoría                          |
| 2     | El ganador del encuentro entre los atletas involucrados en un empate                                       |
| 3     | Mayor suma de votos de los Jueces que escogieron al atleta como ganador a lo largo de todos los encuentros |
| 4     | Ejecución de un Kata extra si los atletas siguen en empate                                                 |

Para determinar el ganador de una categoría individual en modo de TODOS CONTRA TODOS con el sistema de puntuación de panel de 3 o de 5 Jueces, se consideran los siguientes criterios **en orden** para determinar al ganador:

| Orden | Criterio                                                                                                                                                                |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Mayor número de puntos obtenidos por encuentros ganados durante toda la categoría                                                                                       |
| 2     | El ganador del encuentro entre los atletas involucrados en un empate                                                                                                    |
| 3     | La cantidad más alta de la suma de los Jueces que escogieron al atleta como ganador a lo largo de todos los encuentros (es decir, mejor puncuación individual más alta) |
| 4     | Ejecución de un Kata extra si los atletas siguen en empate                                                                                                              |

#### 5.2.2 Sistema de Desempate por Equipos

Para determinar el ganador de una categoría por Equipos en modo de TODOS CONTRA TODOS con el sistema de puntuación de banderas virtuales, se consideran los siguientes criterios **en orden** para determinar al ganador:

| Orden | Criterio                                                                                                   |
| ----- | ---------------------------------------------------------------------------------------------------------- |
| 1     | Mayor número de puntos obtenidos por encuentros ganados durante toda la categoría                          |
| 2     | El ganador del encuentro entre los Equipos involucrados en un empate                                       |
| 3     | Mayor suma de votos de los Jueces que escogieron al Equipo como ganador a lo largo de todos los encuentros |
| 4     | Ejecución de un Kata extra si los Equipos siguen en empate                                                 |

Para determinar el ganador de una categoría por equipos en modo de TODOS CONTRA TODOS con el sistema de puntuación de panel de 3 o de 5 Jueces, se consideran los siguientes criterios **en orden** para determinar al ganador:

| Orden | Criterio                                                                                                                                                                |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | Mayor número de puntos obtenidos por encuentros ganados durante toda la categoría                                                                                       |
| 2     | El ganador del encuentro entre los Equipos involucrados en un empate                                                                                                    |
| 3     | La cantidad más alta de la suma de los Jueces que escogieron al Equipo como ganador a lo largo de todos los encuentros (es decir, mejor puncuación individual más alta) |
| 4     | Ejecución de un Kata extra si los Equipos siguen en empate                                                                                                              |

---

## 6. Flujo de Torneo

### 6.1 Fases del Torneo

```
┌─────────────┐
│  PLANIFICADO │
└──────┬──────┘
       │ Crear tournament
       v
┌─────────────┐
│ INSCRIPCION │ <- Registro de atletas y árbitros
└──────┬──────┘
       │ Cerrar inscripciones
       v
┌─────────────┐
│ VERIFICACION│ <- Validar categorías, pesos, licencias
└──────┬──────┘
       │ Aprobar participantes
       v
┌─────────────┐
│ EN_CURSO    │ <- Competición activa
└──────┬──────┘
       │ Finalizar última categoría
       v
┌─────────────┐
│ FINALIZADO  │ <- Resultados oficiales
└──────┬──────┘
       │ Archivar
       v
┌─────────────┐
│  ARCHIVADO  │
└─────────────┘
```

### 6.2 Transiciones de Estado

| Desde        | Hacia        | Condición                                                              |
| ------------ | ------------ | ---------------------------------------------------------------------- |
| PLANIFICADO  | INSCRIPCION  | Usuario con rol OPERATOR/ADMIN ejecuta "Abrir inscripciones"           |
| INSCRIPCION  | VERIFICACION | Sistema cierra inscripciones automáticamente o manualmente             |
| VERIFICACION | EN_CURSO     | ADMIN ejecuta "Iniciar competición"                                    |
| EN_CURSO     | FINALIZADO   | Todas las categorías completadas                                       |
| FINALIZADO   | ARCHIVADO    | ADMIN ejecuta "Archivar torneo"                                        |
| Cualquiera   | PLANIFICADO  | ADMIN ejecuta "Cancelar/Reiniciar" (solo si no hay encuentros activos) |

### 6.3 Ciclo de Vida de Categoría

```
PENDING -> READY -> IN_PROGRESS -> COMPLETED
  |          |          |
  |          |          v
  |          |      (vuelve a READY si hay más rondas)
  |          v
  |    (inicia primera ronda)
  v
(generación de brackets)
```

### 6.4 Flujo de Encuentro

```
1. Sistema carga encuentro desde cola
2. Se asignan árbitros disponibles al tatami
3. Se llama a atletas/equipos al tatami
4. Verificación de identidad y equipamiento
5. Inicio de encuentro:
   - Kumite: Timer inicia
   - Kata: Reproducción de BGM si aplica
6. Puntuación en tiempo real
7. Fin de encuentro:
   - Validación final de puntuaciones
   - Registro de resultado
   - Actualización de bracket
8. Siguiente encuentro
```

---

## 7. Generación de Brackets

### 7.1 Algoritmo de Seeding

#### 7.1.1 Criterios de Seed

| Prioridad | Criterio           | Descripción                                |
| --------- | ------------------ | ------------------------------------------ |
| 1         | Ranking WKF        | Posición en ranking oficial                |
| 2         | Resultados previos | Victorias en tournaments anteriores        |
| 3         | Sorteo             | Aleatorio para participantes sin historial |

#### 7.1.2 Distribución de Seeds

Para un bracket de 8:

- Posición 1: Seed #1
- Posición 2: Seed #8
- Posición 3: Seed #4
- Posición 4: Seed #5
- Posición 5: Seed #2
- Posición 6: Seed #7
- Posición 7: Seed #3
- Posición 8: Seed #6

### 7.2 Bye Rounds

Cuando el número de participantes no es potencia de 2:

| Participantes | Rounds con Bye | Equipos Directos       |
| ------------- | -------------- | ---------------------- |
| 5             | 3              | 3 acceden directamente |
| 6             | 2              | 2 acceden directamente |
| 7             | 1              | 1 accede directamente  |
| 9             | 7              | 7 acceden directamente |
| 10            | 6              | 6 acceden directamente |
| 11            | 5              | 5 acceden directamente |
| 12            | 4              | 4 acceden directamente |
| 13            | 3              | 3 acceden directamente |
| 14            | 2              | 2 acceden directamente |
| 15            | 1              | 1 accede directamente  |

### 7.3 Tipos de Sistema por Modalidad

#### 7.3.1 Kata Individual

| Sistema             | Participantes | Descripción                |
| ------------------- | ------------- | -------------------------- |
| Eliminación directa | 4, 8, 16, 32  | Single elimination bracket |
| Round Robin         | 3-6           | Todos contra todos         |
| Mixto               | 7-15          | Round robin + eliminación  |

#### 7.3.2 Kata por Equipos

| Sistema             | Equipos  | Descripción        |
| ------------------- | -------- | ------------------ |
| Eliminación directa | 4, 8, 16 | Single elimination |
| Round Robin         | 3-6      | Todos contra todos |

#### 7.3.3 Kumite Individual

| Sistema             | Participantes | Descripción               |
| ------------------- | ------------- | ------------------------- |
| Eliminación directa | 4, 8, 16, 32  | Con repechaje para bronce |
| Double elimination  | 4-16          | Una derrota no elimina    |

#### 7.3.4 Kumite por Equipos

| Sistema             | Equipos | Descripción             |
| ------------------- | ------- | ----------------------- |
| Eliminación directa | 4, 8    | 3 encuentros por equipo |
| Round Robin         | 3-5     | Todos contra todos      |

### 7.4 Integración de Penalizaciones en Brackets

- Atleta con **HANSOKU** en encuentros previos: No puede ser seed top 4
- Atleta con **SHIKKAKU**: Excluido del tournament
- Equipos con múltiples penalizaciones: Ordenados por menor cantidad de Hansoku Chui

---

## 8. Sistema de Arbitraje

### 8.1 Roles y Funciones

#### 8.1.1 Árbitro Principal (Referee)

| Función                 | Descripción                            |
| ----------------------- | -------------------------------------- |
| Iniciar/detener combate | Señal de inicio y stop                 |
| Validar puntuaciones    | Aprueba o rechaza puntos               |
| Imponer penalizaciones  | Decide sobre warnings y hansoku        |
| Decisiones finales      | Desempates, decisiones controversiales |

#### 8.1.2 Jueces (Judges)

| Función                | Descripción                    |
| ---------------------- | ------------------------------ |
| Observar técnicas      | Marcan con banderines          |
| Registrar puntuaciones | Entrada de puntos en sistema   |
| Evaluar kata           | Otorgan puntuaciones numéricas |

#### 8.1.3 Oficial de Mesa (Table Official)

| Función           | Descripción                  |
| ----------------- | ---------------------------- |
| Control de timer  | Gestión del cronómetro       |
| Registro de datos | Entrada de información       |
| Gestión de tatami | Coordina flujo de encuentros |

### 8.2 Reglas de Asignación

#### 8.2.1 Asignación Manual

- ADMIN/OPERATOR selecciona árbitros específicos para cada tatami
- Se valida que el árbitro tenga licencia vigente
- Se valida que el árbitro esté certificado para el tatami

#### 8.2.2 Asignación Automática

```
1. Obtener lista de árbitros disponibles
2. Filtrar por rol requerido (referee/judge)
3. Filtrar por certificación de tatami
4. Ordenar por:
   - Menor número de encuentros asignados hoy
   - Mayor antigüedad (para finales)
5. Asignar según rotación
```

### 8.3 Rotación de Árbitros

| Tipo de Encuentro | Rotación                   |
| ----------------- | -------------------------- |
| Preliminares      | Cambio cada 2-3 encuentros |
| Cuartos de final  | Cambio cada encuentro      |
| Semifinales       | Cambio obligatorio         |
| Finales           | Nuevos árbitros asignados  |

### 8.4 Panel de Jueces

#### 8.4.1 Kata

| Nivel         | Tamaño Panel |
| ------------- | ------------ |
| Nacional      | 3 jueces     |
| Internacional | 5 jueces     |

#### 8.4.2 Kumite

| Posición        | Ubicación                 |
| --------------- | ------------------------- |
| Árbitro central | Centro del tatami         |
| Juez 1          | Lateral A                 |
| Juez 2          | Lateral B                 |
| Juez 3          | Lateral C                 |
| Juez 4          | Lateral D (si panel de 5) |

---

## 9. Importación y Exportación

### 9.1 Formato de Importación de Atletas (CSV)

#### 9.1.1 Estructura del Archivo

```csv
name,date_of_birth,gender,weight_kg,belt_rank,dojo,nationality,license_number
Juan Pérez,2005-03-15,MALE,65.5,Kyu 2,Dojo Central,ARG,ABC123456
María García,2008-07-22,FEMALE,52.0,Dan 1,Dojo Norte,ESP,DEF789012
```

#### 9.1.2 Validaciones

| Campo          | Regla                                    |
| -------------- | ---------------------------------------- |
| name           | Obligatorio, 2-255 caracteres            |
| date_of_birth  | Formato ISO 8601 (YYYY-MM-DD), no futuro |
| gender         | Valores válidos: MALE, FEMALE            |
| weight_kg      | Número positivo, 40.0-120.0              |
| belt_rank      | Formato: "Kyu 1-8" o "Dan 1-10"          |
| dojo           | Opcional, máximo 255 caracteres          |
| nationality    | Código ISO 3166-1 alpha-3 (opcional)     |
| license_number | Opcional, único si se proporciona        |

#### 9.1.3 Formato JSON

```json
{
  "athletes": [
    {
      "name": "Juan Pérez",
      "date_of_birth": "2005-03-15",
      "gender": "MALE",
      "weight_kg": 65.5,
      "belt_rank": "Kyu 2",
      "dojo": "Dojo Central",
      "nationality": "ARG",
      "license_number": "ABC123456"
    }
  ]
}
```

### 9.2 Exportación de Resultados

#### 9.2.1 Formato JSON de Resultados

```json
{
  "tournament": {
    "id": 1,
    "name": "Campeonato Nacional 2026",
    "date": "2026-03-30",
    "status": "COMPLETED"
  },
  "category": {
    "id": 1,
    "name": "Kumite Masculino -60kg",
    "modality": "KUMITE_INDIVIDUAL",
    "gender": "MALE"
  },
  "bracket": {
    "type": "ELIMINATION",
    "size": 16
  },
  "matches": [
    {
      "id": 1,
      "round": 1,
      "match_number": 1,
      "aka": {
        "id": 1,
        "name": "Atleta A"
      },
      "ao": {
        "id": 2,
        "name": "Atleta B"
      },
      "aka_score": 3,
      "ao_score": 1,
      "winner_id": 1,
      "status": "COMPLETED",
      "penalties": [
        {
          "participant": "AO",
          "type": "CHUI",
          "reason": "Evadir combate"
        }
      ]
    }
  ],
  "podium": {
    "first_place": { "id": 1, "name": "Atleta A" },
    "second_place": { "id": 3, "name": "Atleta C" },
    "third_places": [
      { "id": 5, "name": "Atleta E" },
      { "id": 7, "name": "Atleta G" }
    ]
  }
}
```

#### 9.2.2 Exportación CSV de Resultados

```csv
category_name,modality,round,match_number,aka_name,ao_name,aka_score,ao_score,winner,penalties_aka,penalties_ao
Kumite Masculino -60kg,KUMITE_INDIVIDUAL,1,1,Juan Pérez,María García,3,1,Juan Pérez,0,1
```

### 9.3 Exportación de Inscripciones

```json
{
  "tournament": {
    "id": 1,
    "name": "Campeonato Nacional 2026"
  },
  "registration_date": "2026-03-01",
  "athletes": [
    {
      "category": "Kumite Masculino -60kg",
      "name": "Juan Pérez",
      "dojo": "Dojo Central",
      "weight_kg": 65.5,
      "date_of_birth": "2005-03-15",
      "status": "CONFIRMED"
    }
  ],
  "statistics": {
    "total_athletes": 150,
    "total_categories": 24,
    "dojos_represented": 12
  }
}
```

---

## 10. Autenticación y Roles de Usuario

### 10.1 Roles Definidos

| Rol      | Descripción               | Ámbito              |
| -------- | ------------------------- | ------------------- |
| ADMIN    | Administrador del sistema | 全局                |
| OPERATOR | Operador de tournament    | Tournament asignado |
| VIEWER   | Espectador                | Tournament público  |

### 10.2 Matriz de Permisos

| Función                        | ADMIN | OPERATOR | VIEWER |
| ------------------------------ | ----- | -------- | ------ |
| Crear/editar/eliminar usuarios | ✓     | ✗        | ✗      |
| Crear tournament               | ✓     | ✗        | ✗      |
| Editar tournament              | ✓     | ✗        | ✗      |
| Eliminar tournament            | ✓     | ✗        | ✗      |
| Gestionar categorías           | ✓     | ✓        | ✗      |
| Inscribir atletas              | ✓     | ✓        | ✗      |
| Importar/exportar datos        | ✓     | ✓        | ✗      |
| Iniciar encuentros             | ✓     | ✓        | ✗      |
| Registrar puntuaciones         | ✓     | ✓        | ✗      |
| Ver resultados en tiempo real  | ✓     | ✓        | ✓      |
| Ver tournament público (QR)    | ✓     | ✓        | ✓      |

### 10.3 Flujo de Autenticación

```
1. Usuario abre aplicación
2. Si no hay sesión activa -> página de login
3. Usuario ingresa username/password
4. Sistema valida credenciales
5. Si válido -> crear sesión, redirigir a dashboard
6. Si inválido -> mostrar error, máximo 5 intentos
7. Sesión expira después de 8 horas de inactividad
```

### 10.4 Gestión de Sesiones

| Aspecto                  | Valor                 |
| ------------------------ | --------------------- |
| Duración de sesión       | 8 horas               |
| Máximo intentos fallidos | 5                     |
| Bloqueo por intentos     | 15 minutos            |
| Timeout de inactividad   | 30 minutos            |
| Tokens de sesión         | JWT con refresh token |

---

## 11. Interfaz de Usuario

### 11.1 Inventario de Pantallas

#### 11.1.1 Autenticación

| Pantalla | Ruta    | Descripción                |
| -------- | ------- | -------------------------- |
| Login    | /login  | Página de inicio de sesión |
| Logout   | /logout | Cierra sesión              |

#### 11.1.2 Dashboard

| Pantalla            | Ruta                       | Descripción                                    |
| ------------------- | -------------------------- | ---------------------------------------------- |
| Dashboard Principal | /dashboard                 | Vista general de tournaments y accesos rápidos |
| Tournament Reciente | /dashboard/tournament/{id} | Vista de tournament activo                     |

#### 11.1.3 Gestión de Atletas

| Pantalla          | Ruta                | Descripción                                     |
| ----------------- | ------------------- | ----------------------------------------------- |
| Lista de Atletas  | /athletes           | Tabla con todos los atletas, filtros y búsqueda |
| Detalle de Atleta | /athletes/{id}      | Información completa del atleta                 |
| Crear Atleta      | /athletes/new       | Formulario de nuevo atleta                      |
| Editar Atleta     | /athletes/{id}/edit | Formulario de edición                           |
| Importar Atletas  | /athletes/import    | Carga masiva de atletas                         |

#### 11.1.4 Gestión de Árbitros

| Pantalla           | Ruta           | Descripción                   |
| ------------------ | -------------- | ----------------------------- |
| Lista de Árbitros  | /referees      | Tabla de árbitros registrados |
| Detalle de Árbitro | /referees/{id} | Información y certificaciones |
| Crear Árbitro      | /referees/new  | Formulario de nuevo árbitro   |

#### 11.1.5 Gestión de Torneos

| Pantalla              | Ruta                         | Descripción                       |
| --------------------- | ---------------------------- | --------------------------------- |
| Lista de Torneos      | /tournaments                 | Todos los tournaments con filtros |
| Detalle de Torneo     | /tournaments/{id}            | Vista completa del tournament     |
| Crear Torneo          | /tournaments/new             | Formulario de nuevo tournament    |
| Editar Torneo         | /tournaments/{id}/edit       | Modificar tournament              |
| Gestión de Categorías | /tournaments/{id}/categories | CRUD de categorías                |

#### 11.1.6 Gestión de Equipos

| Pantalla          | Ruta        | Descripción                |
| ----------------- | ----------- | -------------------------- |
| Lista de Equipos  | /teams      | Todos los equipos          |
| Detalle de Equipo | /teams/{id} | Miembros y categoría       |
| Crear Equipo      | /teams/new  | Formulario de nuevo equipo |

#### 11.1.7 Competición

| Pantalla              | Ruta                           | Descripción                    |
| --------------------- | ------------------------------ | ------------------------------ |
| Panel de Competición  | /competition/{category_id}     | Vista de categoría con bracket |
| Pantalla de Encuentro | /competition/match/{id}        | Scoring del encuentro activo   |
| Pantalla de Kata      | /competition/match/{id}/kata   | Scoring específico para kata   |
| Pantalla de Kumite    | /competition/match/{id}/kumite | Scoring específico para kumite |
| Pantalla de Bracket   | /tournaments/{id}/bracket      | Visualización de bracket       |
| Cronómetro            | /competition/timer             | Vista de timer independiente   |

#### 11.1.8 Resultados

| Pantalla                  | Ruta                     | Descripción                   |
| ------------------------- | ------------------------ | ----------------------------- |
| Resultados por Categoría  | /results/category/{id}   | Resultados de una categoría   |
| Resultados por Tournament | /results/tournament/{id} | Todos los resultados          |
| Podios                    | /results/podiums         | Vista de podios por categoría |
| Estadísticas              | /results/statistics      | Estadísticas del tournament   |

#### 11.1.9 Visualización Pública

| Pantalla         | Ruta                    | Descripción        |
| ---------------- | ----------------------- | ------------------ |
| Viewer Login     | /viewer/login           | Acceso con código  |
| Viewer Dashboard | /viewer/{tournament_id} | Resultados en vivo |

### 11.2 Flujo de Navegación

Se deben establecer rutas **según lo mostrado en esta estructura de flujo**.

```
Login
  |
  v
Dashboard (Muestra el menú principal y resúmenes de los 4 últimos resultados en las categorías en curso de torneos recientemente terminados)
  |
  +---> Atletas
  |     +---> Crear/Editar/Ver
  |     +---> Importar
  |
  +---> Árbitros
  |     +---> Crear/Editar/Ver
  |
  +---> Torneos
  |     +---> Crear/Editar
  |     +---> Categorías
  |     +---> Bracket
  |     +---> Competición
  |
  +---> Exhibición
  |     +---> Modo de Kata con AKA y AO, sin relevancia eliminatoria (no hace falta registrar nombres para este modo)
  |     +---> Modo de Kumite con AKA y AO, sin relevancia eliminatoria (no hace falta registrar nombres para este modo)
  |
  +---> Equipos
  |     +---> Crear/Editar
  |
  +---> Resultados
        +---> Por categoría
        +---> Podios
```

### 11.3 Requisitos de Responsividad

| Breakpoint | Dispositivo  | Ancho          |
| ---------- | ------------ | -------------- |
| Mobile     | Teléfonos    | < 768px        |
| Tablet     | Tablets      | 768px - 1024px |
| Desktop    | Computadoras | > 1024px       |

#### 11.3.1 Adaptaciones por Dispositivo

| Componente | Mobile            | Tablet             | Desktop            |
| ---------- | ----------------- | ------------------ | ------------------ |
| Menú       | Hamburger         | Sidebar colapsable | Sidebar visible    |
| Tablas     | Scroll horizontal | Scroll horizontal  | Columnas completas |
| Forms      | Una columna       | Dos columnas       | Tres columnas      |
| Bracket    | Zoom horizontal   | Scroll horizontal  | Vista completa     |
| Scoring    | Botones grandes   | Botones medianos   | Botones estándar   |

### 11.4 Pantalla de Scoring en Tiempo Real

#### 11.4.1 Componentes Visuales

| Elemento               | Descripción                      |
| ---------------------- | -------------------------------- |
| Nombre de competidores | Nombres grandes y visibles       |
| Puntuación             | Números grandes (mínimo 72px)    |
| Cronómetro             | Visible en centro (mínimo 120px) |
| Banderas/Aka Ao        | Colores distintivos (Rojo/Azul)  |
| Historial de puntos    | Lista de últimos puntos marcados |
| Penalizaciones         | Lista de warnings y hansoku      |

#### 11.4.2 Modo de Pantalla Completa (Aplicable para mostrar el componente visual de los encuentros de Kata y Kumite en un monitor externo o proyector)

- Ocultar controles de navegador
- Maximizar área de visualización
- Actualización automática cada segundo
- Compatible con proyectores y pantallas grandes

---

## 12. Apéndice: Glosario de Términos

| Término      | Definición                                                                                                                            |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| Aka          | Competidor/equipo rojo                                                                                                                |
| Ao           | Competidor/equipo azul                                                                                                                |
| Bunkai       | Aplicación práctica de kata                                                                                                           |
| Chui         | Primera amonestación                                                                                                                  |
| Hansoku      | Descalificación                                                                                                                       |
| Hansoku Chui | Infracción grave o cuarta infracción menor acumulada. Es una ADVERTENCIA (warning) de descalificación - NO otorga puntos al oponente. |
| Ippon        | Punto completo (3 puntos)                                                                                                             |
| Kata         | Formulario/sequencia de movimientos                                                                                                   |
| Kumite       | Combate                                                                                                                               |
| Shikkaku     | Descalificación permanente                                                                                                            |
| Waza-ari     | Casi-ippon (2 puntos)                                                                                                                 |
| Yuko         | Punto válido (1 punto)                                                                                                                |
| Golden Point | Tiempo extra, primer punto gana                                                                                                       |
| Bye          | Clasificación directa sin combate                                                                                                     |
| Seed         | Posición pre-asignada en bracket                                                                                                      |

---

## 13. Referencias Normativas

### 13.1 Documentos WKF 2026

- WKF Kata Competition Rules 2026 (referenciado en ./docs/WKF Kata Competition Rules 2026 MASTER COPY_V2.pdf)
- WKF Kumite Competition Rules 2026 (referenciado en ./docs/WKF 2026 Kumite Competition Rules MASTER COPY_V11.pdf)

### 13.2 Artículos Aplicables

| Regla               | Artículo WKF |
| ------------------- | ------------ |
| Puntuación Kumite   | Art. 8       |
| Puntuación Kata     | Art. 5       |
| Penalidades Kumite  | Art. 9       |
| Penalidades Kata    | Art. 6       |
| Duración encuentros | Art. 3       |
| Equipamiento        | Art. 4       |
| Árbitros            | Art. 10-14   |

---

_Documento generado según propuesta SPECS_UPDATE_PROPOSAL.md_
_Versión: 1.0_
_Fecha: 2026-03-30_
