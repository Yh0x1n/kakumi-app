# Proposal: Tournament Frontend Redesign - Sequential Card Flow

## Resumen Ejecutivo

Reemplazar grid 2-columnas con 5 cards siempre visibles por flujo secuencial de 1 card a la vez.
TournamentState gana step machine simple (step_index + step_count). UI existente (categorias, tatamis, ciclo) se reutiliza dentro de cada card. Sin cambios en backend/models/services.

---

## 1. Problema Actual

Grid `rx.grid(columns="2")` muestra 5 cards simultaneas:

- Selector torneo
- Lifecycle controls
- Categorias (con tabla + formulario inline)
- Tatamis (con tabla + formulario inline)
- QR

**Problemas**:
- UX abrumador para operadores nuevos
- Estado torneo avanzado (INSCRIPCION+) muestra controles que no aplican en misma pantalla
- Creacion torneo fuerza scroll vertical excesivo
- No hay progresion guiada: crear torneo → categorias → tatamis → iniciar
- Mobile responsive pobre con 2-columnas

---

## 2. Alcance

### Incluye

- Flujo secuencial de cards (1 card visible a la vez)
- Step machine en TournamentState (step_index, step_count, next/back handlers)
- TournamentSelectionCard (Card 1) - selector torneo + acciones crear/editar
- TournamentStatusCard (Card 2) - resumen + ciclo de vida + bracket link
- TournamentFormCard (Card Crear) - reusa `_tournament_form()` de registries.py
- TournamentEditChoiceCard (Card Eleccion) - editar categorias vs editar datos torneo
- CategoriesCard (Card Categorias) - reusa `_categories_card()` existente
- TatamisCard (Card Tatamis) - reusa `_tatami_card()` existente
- Navigation: solo Previous/Next steps, sin saltos
- Torneos avanzados (INSCRIPCION+): cards 1+2 visibles, resto readonly
- WCAG AA, i18n ES/EN, responsive mobile-first

### NO Incluye

- Cambios en Tournament/TournamentCategory/Tatami models
- Cambios en TournamentService
- Cambios en TournamentCategoryState/TournamentTatamiState
- Cambios en TournamentCrudState
- Nuevos endpoints API
- Bracket generation UI
- Nuevos permisos RBAC

---

## 3. Flujo de Usuario Detallado

### 3.1 Entrada a /tournament

```
→ on_load: load_workspace()
→ Siempre empieza en Card 1 (step_index = 0)
→ Lista torneos desde BD visible en tournaments[]
```

### 3.2 Card 1 - TournamentSelectorCard

```
┌─────────────────────────────────────┐
│  Torneos disponibles                │
│                                     │
│  [Lista torneos como botones]       │
│  - Torneo Alpha         [seleccion] │
│  - Torneo Beta          [seleccion] │
│                                     │
│  [Crear torneo]  [Editar torneo]    │
│                                     │
│  → Boton "Siguiente" (disabled      │
│    hasta seleccionar torneo)        │
└─────────────────────────────────────┘

Acciones:
- Click torneo → set_current_tournament(id)
- "Crear torneo" → jump to TournamentFormCard (crear mode)
- "Editar torneo" → si no hay seleccion, mostrar toast "Selecciona torneo primero"
                     si hay seleccion, jump to EditChoiceCard
- "Siguiente" → step_index = 1 (StatusCard)
```

### 3.3 Card 2 - TournamentStatusCard

```
┌─────────────────────────────────────┐
│  Estado del Torneo                  │
│                                     │
│  Torneo: Alpha                      │
│  Estado: BORRADOR                   │
│  Sede: Dojo Central                 │
│  Tatamis: 4                         │
│  Categorias: 6                      │
│                                     │
│  [Ver bracket / Competencia]        │
│                                     │
│  ── Controles de ciclo ──          │
│  [Abrir inscripciones] [Cerrar...]  │
│  [Iniciar competencia] [Finalizar]  │
│  [Archivar] [Reabrir] [Cancelar]   │
│                                     │
│  ← Anterior     Siguiente →         │
└─────────────────────────────────────┘

Nota: lifecycle controls reusan logica existente de TournamentState
      (show_open_registrations_action, etc.)
```

### 3.4 Flujo Crear Torneo

```
Card 1 → [Crear torneo] → TournamentFormCard
  ↓
  [Guardar] → crea torneo BD, status PLANIFICADO
  ↓
  auto-avanza → CategoriesCard (step crear_categorias)
  ↓
  [Siguiente] → TatamisCard (step crear_tatamis)
  ↓
  [Siguiente] → RegistrationControlCard (confirmacion cierre inscripciones)
  ↓
  [Comenzar torneo] → transition_to(EN_CURSO) → Card 2 (StatusCard)
```

Cada paso puede regresar al anterior. Progreso persistente en servidor (torneo ya creado en BD).

### 3.5 Flujo Editar Torneo

```
Card 1 → [Editar torneo] →

  ┌─ Si estado BORRADOR ──────────────────┐
  │  EditChoiceCard:                      │
  │  [Editar categorias]                  │
  │     → CategoriesCard (step editable)  │
  │  [Editar datos torneo]                │
  │     → TournamentFormCard (edit mode)  │
  └───────────────────────────────────────┘

  ┌─ Si INSCRIPCION ─────────────────────┐
  │  Solo edicion categorias permitida   │
  │  → CategoriesCard (readonly campos   │
  │     torneo, categorias editables)    │
  └──────────────────────────────────────┘

  ┌─ Si EN_CURSO o ARCHIVADO ───────────┐
  │  Solo visualizacion / Ver bracket   │
  │  → TournamentStatusCard (readonly)  │
  └──────────────────────────────────────┘
```

### 3.6 Torneos Avanzados (INSCRIPCION+)

- Cards 1+2 visibles en secuencia normal
- CategoriesCard y TatamisCard visibles pero en modo readonly
- Campos de formulario deshabilitados segun estado
- Solo bracket link activo

---

## 4. Arquitectura Propuesta

### 4.1 TournamentPage Structure

```python
# kakumi_app/pages/tournament.py

# Layout unico
def tournament() -> rx.Component:
    return registry_page_shell(
        body=rx.container(
            _workspace_header(),
            _step_indicator(),           # progress dots: ● ● ○ ○ ○
            _active_card(),              # rx.match(state.step_index, ...)
            _navigation_bar(),           # ← Anterior  [Siguiente →]
            max_width="800px",
        )
    )
```

### 4.2 Step Machine (en TournamentState)

```python
# New vars on TournamentState
step_index: int = 0
step_count: int = 2  # minimo; crece segun flujo
is_creating: bool = False  # True durante flujo crear
is_editing_categories: bool = False
max_reached_step: int = 0  # registro para readonly check

# Step definitions (not enum, just constants)
STEPS = {
    "SELECTION": 0,       # Card 1: selector
    "STATUS": 1,          # Card 2: status + lifecycle
    "FORM": 2,            # Create/Edit form
    "EDIT_CHOICE": 2,     # Edit choice (overlaps FORM index)
    "CATEGORIES": 3,      # Categories CRUD
    "TATAMIS": 4,         # Tatamis CRUD
}
```

### 4.3 Card Resolution via rx.match

```python
def _active_card() -> rx.Component:
    return rx.match(
        TournamentState.step_index,
        0, _selector_card(),
        1, _status_card(),
        2, rx.match(
            TournamentState.is_creating,
            _tournament_form_card(),      # reusa _tournament_form()
            _edit_choice_card(),
        ),
        3, _categories_card(),            # reusa _categories_card() existente
        4, _tatamis_card(),               # reusa _tatami_card() existente
        _selector_card(),                  # default fallback
    )
```

---

## 5. Componentes

| Componente | Archivo | Responsabilidad | Reuso |
|-----------|---------|----------------|-------|
| `TournamentSelectorCard` | `tournament.py` | Lista torneos, seleccion, actions crear/editar | Nuevo |
| `TournamentStatusCard` | `tournament.py` | Resumen torneo + lifecycle controls + bracket link | Reusa `_selection_summary` + lifecycle |
| `TournamentFormCard` | `tournament.py` | Wrapper de form registries | Reusa `_tournament_form()` de registries.py |
| `EditChoiceCard` | `tournament.py` | Eleccion editar categorias/datos | Nuevo |
| `CategoriesCard` | `tournament.py` | Tabla categorias + form inline | Reusa `_categories_card()` existente |
| `TatamisCard` | `tournament.py` | Tabla tatamis + form inline | Reusa `_tatami_card()` existente |
| `StepIndicator` | `tournament.py` | Dots de progreso (● ● ○ ○ ○) | Nuevo |
| `NavigationBar` | `tournament.py` | Botones ← Anterior / Siguiente → | Nuevo |

---

## 6. Estados y Datos

### TournamentState - vars nuevas

```python
# Step machine
step_index: int = 0
step_count: int = 2
is_creating: bool = False
is_editing_categories: bool = False
max_reached_step: int = 0  # para readonly gate

# Flujo crear
create_flow_step: int = 0  # 0=form, 1=categories, 2=tatamis, 3=confirm

# UI state
previous_step_allowed: bool = True  # rx.var
next_step_allowed: bool = False     # rx.var (depende de validacion)
```

### TournamentState - handlers nuevos

```python
# Navigation
@rx.event def go_next(self) -> None
@rx.event def go_previous(self) -> None
@rx.event def go_to_step(self, step: int) -> None  # solo para crear/editar jumps

# Computed
@rx.var def can_go_next(self) -> bool
@rx.var def can_go_previous(self) -> bool
@rx.var def current_step_name(self) -> str
@rx.var def is_readonly_mode(self) -> bool  # torneo avanzado

# Flow triggers
@rx.event def start_create_flow(self) -> None
@rx.event def start_edit_tournament(self) -> None
@rx.event def start_edit_categories(self) -> None
@rx.event def complete_create_flow(self) -> None
```

### No se modifican

- TournamentCategoryState (509 lines) - sin cambios
- TournamentTatamiState (298 lines) - sin cambios
- TournamentCrudState (469 lines) - sin cambios
- Tournament model - sin cambios
- TournamentService - sin cambios

---

## 7. API / Eventos

### Handlers existentes reutilizados

```
TournamentState:
  load_workspace()          → on_load
  set_current_tournament()  → seleccion torneo
  open_registrations()      → lifecycle
  close_registrations()     → lifecycle
  start_competition()       → lifecycle
  finish_competition()      → lifecycle
  archive_tournament()      → lifecycle
  cancel_tournament()       → lifecycle
  reopen_registrations()    → lifecycle
  generate_qr()             → QR (si se mantiene)
  regenerate_qr()           → QR

TournamentCategoryState:
  set_form_values()         → crear/editar categoria
  save_category()           → guardar
  delete_category()         → eliminar
  cancel_category_form()    → cerrar form
  set_form_values()         → editar

TournamentTatamiState:
  set_form_values()         → crear/editar tatami
  save_tatami()             → guardar
  delete_tatami()           → eliminar
  cancel_tatami_form()      → cerrar form
  toggle_tatami_active()    → activar/desactivar

TournamentCrudState:
  _tournament_form()        → component reutilizado
  save_tournament()         → crear/editar torneo
  cancel_form()             → cancelar
```

### Inputs adicionales (event chains)

```
set_current_tournament(id) →
  TournamentCategoryState.set_tournament_context(id) +
  TournamentTatamiState.set_tournament_context(id)
  (ya existe via TournamentState - sync en handler actual)

save_tournament() success →
  auto-avance a CategoriesCard (is_creating=True)
```

---

## 8. Reglas de Negocio

| Regla | Condicion | Comportamiento |
|-------|-----------|----------------|
| Step navigation | Siempre | Solo prev/next. Sin saltos. |
| Card 1 requirement | step=0 | Torneo debe estar seleccionado para habilitar "Siguiente" |
| Create flow entry | Click "Crear torneo" | Salta a TournamentFormCard (step=2, is_creating=True) |
| Edit tournament | Click "Editar torneo" | Sin seleccion → toast. Con seleccion → EditChoiceCard o StatusCard segun estado |
| BORRADOR edit | status=PLANIFICADO | EditChoiceCard: editar categorias OR datos torneo |
| INSCRIPCION edit | status=INSCRIPCION | Solo edicion categorias permitida |
| EN_CURSO/ARCHIVADO | status avanzado | Readonly. Solo visualizacion + bracket link |
| Create flow steps | is_creating=True | Form → Categories → Tatamis → Confirm → Status |
| Guardar torneo success | save_tournament OK | Auto-avance a Categories card |
| Guardar categoria success | save_category OK | Permanecer en Categories card (no auto-avance) |
| Guardar tatami success | save_tatami OK | Permanecer en Tatamis card (no auto-avance) |
| Comenzar torneo | create flow end | Llama start_competition(), redirige a StatusCard |

---

## 9. Requisitos No Funcionales

| Requisito | Implementacion |
|-----------|---------------|
| **WCAG AA** | roles ARIA en cards, focus management al cambiar step, skip links, contraste 4.5:1 |
| **i18n ES/EN** | Textos con `rx.cond(lang, "ES text", "EN text")` o `gettext` wrapper existente |
| **Responsive** | Card unico = natural mobile. Container max_width=800px. Botones full-width en mobile. |
| **Performance** | Paginacion si >50 torneos en lista. Lazy load categories/tatamis solo cuando se visita su card. |
| **Tests unitarios** | Step navigation, create flow, edit flow, state guards (readonly mode) |
| **Tests e2e** | Flujo completo crear torneo, navegacion steps, validaciones de estado |
| **Accessibility** | Keyboard navigation entre steps (Tab + Enter/Arrow), anuncios de cambio de paso para screen readers |

---

## 10. Criterios de Aceptacion (Gherkin)

```gherkin
FEATURE: Tournament Sequential Card Flow

  SCENARIO: Navigate through cards sequentially
    Given I am on the tournament page
    When I see Card 1 (Selection)
    Then Card 2 (Status) should NOT be visible
    And the "Siguiente" button should be disabled

  SCENARIO: Select tournament enables next step
    Given I am on Card 1 (Selection)
    When I select an existing tournament
    Then the "Siguiente" button becomes enabled
    And clicking it shows Card 2 (Status)

  SCENARIO: Create tournament flow
    Given I am on Card 1 (Selection)
    When I click "Crear torneo"
    Then I see the tournament form (Card Form)
    When I fill required fields and save
    Then a new tournament is created in BORRADOR status
    And I am advanced to the Categories card
    When I add categories and proceed
    Then I see the Tatamis card
    When I configure tatamis and proceed
    Then I see the registration confirmation card

  SCENARIO: Edit tournament in BORRADOR
    Given a tournament exists in BORRADOR status
    When I select it and click "Editar torneo"
    Then I see the Edit Choice card
    And I can choose to edit categories or tournament data

  SCENARIO: View advanced tournament (readonly)
    Given a tournament exists in EN_CURSO status
    When I navigate to Card 3 (Categories)
    Then the category form fields are disabled
    And I cannot create or delete categories

  SCENARIO: Cannot skip steps
    Given I am on Card 1 (Selection)
    When I try to navigate directly to Card 4
    Then I stay on Card 1
    And navigation enforces sequential order

  SCENARIO: Previous step navigation
    Given I am on Card 2 (Status)
    When I click "Anterior"
    Then I return to Card 1 (Selection)
    And my tournament selection is preserved

  SCENARIO: Back after creating tournament returns to Card 1
    Given I created a tournament through the create flow
    And I completed the flow back to Card 1
    When I view the tournament list
    Then my newly created tournament appears in the list
```

---

## 11. Riesgos

| Riesgo | Probabilidad | Impacto | Mitigacion |
|--------|-------------|---------|------------|
| **State coupling**: 3 substates (TournamentState, TournamentCategoryState, TournamentTatamiState) deben syncronizar step navigation | Alta | Media | Centralizar step_index en TournamentState. Substates solo reciben eventos via parent. Tests de sync. |
| **Form reuso**: `_tournament_form()` de registries usa TournamentCrudState, no TournamentState | Media | Alta | TournamentFormCard renderiza el form component pero necesita bridge entre states. Alternativa: TournamentState copia form vars necesarias o usa TournamentCrudState como submix. |
| **Regresion QR**: Card QR actual podria desaparecer o necesitar reubicacion | Baja | Baja | QR mantiene su card como paso opcional al final del flujo, o se integra en StatusCard. Decidir en design phase. |

---

## 12. Affected Areas

| Area | Impacto | Descripcion |
|------|---------|-------------|
| `kakumi_app/pages/tournament.py` | **Major** | Reescritura completa del layout. De grid a sequential cards. |
| `kakumi_app/states/tournament_state.py` | **Major** | +~150 lines: step machine, navigation handlers, computed guards. |
| `kakumi_app/states/tournament_category_state.py` | **Minor** | Integracion con step readonly mode (nuevo flag `_readonly_mode`). |
| `kakumi_app/states/tournament_tatami_state.py` | **Minor** | Integracion con step readonly mode. |
| `kakumi_app/tests/` | **Major** | +50-80 tests: step navigation, flow integration, state guards. |

---

*Artifact: proposal*
*Change: tournament-frontend-redesign*
*Branch: chore/tournament-frontend-redesign*
*Generated: 2026-06-30*
