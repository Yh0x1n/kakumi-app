# **KAKUMI TOURNAMENT MANAGER**

---

## **Descripción**

_Aplicación web para la gestión de torneos de Karate-Do, basada en el reglamento WKF vigente._

### **Tecnologías principales**

- Lenguaje: Python
- Framework: Reflex (frontend y backend)
- Base de Datos: SQLite con SQLModel, alembic (para migraciones)

### **Especificaciones**

#### **Dashboard principal**

#### **Sistema de Registros**

- Módulos principales:
  - Atletas: _Gestión de atletas y clasificación de los mismos por:_
    - _Edad_
    - _Sexo_
    - _Peso (opcional)_
    - _Cinturón o grado (opcional)_
    - _Dojo o asociación a la que pertenece_
      _Se pueden importar los atletas con un listado de una hoja de cálculo que cumpla con el formato determinado por las especificaciones. Asimismo se puede exportar cumpliendo ese mismo formato._
  - Torneos: _Gestion de los torneos en los que se crean y administran categorías dentro del mismo módulo, donde participan los atletas de acuerdo a:_
    - _Edad_
    - _Sexo_
    - _Peso (opcional)_
    - _Cinturón o grado_
      _Un torneo puede tener varias categorías, pero una categoría puede pertenecer únicamente al torneo dentro del cual se creó_
      _Al crear una categoría, se les puede asignar un nombre, modalidades (Kata, Kumite o ambas, individual o por equipos), el rango de edad, peso (si aplica para Kumite), y rango de grado o cinturón, basado en el reglamento WKF vigente._
  - Árbitros: _Gestión de oficiales que controlarán el desarrollo de los encuetros_
    - _Se les establece roles según los estipulados por el reglamento WKF vigente, ya sea manualmente o por medio de sorteos aleatorios._

#### **Sistema de Competición y de Encuentros**

- Módulos principales:
  - Modo de exhibición: _Ubicado en el dashboard principal. Se realizan encuentros de Kata o Kumite sin relevancia eliminatoria._
  - Modo de torneo: _Ubicado en el dashboard principal. Inicialización de torneos y sus respectivas categorías._
    - Moddalidades:
      - Kata:
        - Individual:
          - Todos contra todos: _Sistema simple de todos contra todos. Se define el podio de quienes hayan obtenido mayor puntuación entre todos los atletas de la categoría._
          - Eliminatorias directas: _Sistema de llaves. Se sortean los encuentros entre los participantes de la categoría. Gana quien obtenga mayor puntuación que el oponente._
        - Equipos:
          - Todos contra todos: _Sistema simple de todos contra todos. Se define el podio del equipo que haya obtenido mayor puntuación entre todos los equipos de la categoría._
          - Eliminatorias directas: _Sistema de llaves. Se sortean los encuentros entre los equipos participantes de la categoría. Gana el equipo que obtenga mayor puntuación que el equipo oponente._
      - Kumite:
        - Individual:
          - Eliminatorias directas: _Sistema de llaves. Se sortean los encuentros entre los participantes de la categoría. Se define el ganador del encuentro según la diferencia de puntuación o los criterios de desempate estipulados por el reglamento WKF._
        - Equipos:
          - Eliminatorias directas: _Sistema de llaves. Se sortean los encuentros entre los equipos participantes de la categoría. Se define el equipo ganador de la eliminatoria según la diferencia de victorias (de acuerdo al reglamento WKF)._

#### **Sistema de Puntuación**

- Kata:
  - _El ganador se define basándose en las puntuaciones que cada juez otorgó a cada uno de los dos atletas o equipos (en una escala de 5.0 a 10). El ganador se determina por mayoría de puntuaciones favorables de los jueces (ver artículo 5.4 del reglamento de Kata WKF)._

- Kumite:
  - _(Ver artículo 8 del reglamento de Kumite WKF)_

- _Al llevarse a cabo un encuentro, ambos sistemas de puntaje se muestran de dos maneras: en la pantalla principal donde se administan las puntuaciones, y en una segunda pantalla o monitor externo que muestre el resultado en directo._
