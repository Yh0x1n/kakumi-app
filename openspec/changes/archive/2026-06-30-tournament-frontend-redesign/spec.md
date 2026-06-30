# Spec: Tournament Frontend Redesign - Sequential Card Flow

## 1. Resumen de Cambios

| Modulo | Archivo | Tipo Cambio | Descripcion |
|--------|---------|-------------|-------------|
| Page | `kakumi_app/pages/tournament.py` | **Reescritura** | Layout grid 2-col → sequential 1-card. _active_card() + _step_indicator() + _navigation_bar() reemplazan rx.grid. |
| Page | `kakumi_app/pages/tournament.py` | **Nuevo** | `TournamentSelectorCard`, `TournamentStatusCard`, `TournamentFormCard`, `EditChoiceCard` wrappers. |
| Page | `kakumi_app/pages/tournament.py` | **Nuevo** | `_step_indicator()` progress dots, `_navigation_bar()` prev/next buttons. |
| State | `kakumi_app/states/tournament_state.py` | **Nuevos vars** | `step_index`, `step_count`, `is_creating`, `is_editing_categories`, `max_reached_step` |
| State | `kakumi_app/states/tournament_state.py` | **Nuevos handlers** | `go_next`, `go_previous`, `go_to_step`, `start_create_flow`, `start_edit_tournament`, `start_edit_categories`, `complete_create_flow` |
| State | `kakumi_app/states/tournament_state.py` | **Nuevos computed** | `can_go_next`, `can_go_previous`, `current_step_name`, `is_readonly_mode` |
| State | `kakumi_app/states/tournament_state.py` | **Minor** | Integracion readonly mode en `load_workspace` + `set_current_tournament` |
| State | `kakumi_app/states/tournament_category_state.py` | **Minor** | Nuevo flag `_readonly_mode` que deshabilita form/tabla |
| State | `kakumi_app/states/tournament_tatami_state.py` | **Minor** | Nuevo flag `_readonly_mode` que deshabilita form/tabla |
| State | `kakumi_app/states/tournament_crud_state.py` | **Minor** | `save_tournament` success emite señal para auto-avance a Categories |
| Tests | `kakumi_app/tests/test_tournament_step_navigation.py` | **Nuevo** | Tests step machine, navegacion, flujos crear/editar, guards readonly |
| Config | `kakumi_app/states/__init__.py` | **Minor** | Export de nuevos estados si necesario |

---

## 2. Specs Funcionales por Card

### Spec: TournamentSelectorCard (Card 1)

- **ID**: TC-01
- **When**: usuario entra a `/tournament` o navega desde step anterior
- **Given**: `TournamentState.step_index == 0` siempre al entrar a `/tournament`
  - `TournamentState.tournaments[]` cargado via `load_workspace()` en `on_mount`
  - Ningun torneo seleccionado a menos que `current_tournament` venga de sesion previa
- **Then**:
  - Renderiza lista torneos como botones `variant="outline"` con nombre
  - Boton torneo seleccionado: `variant="solid"`, resto `"outline"`
  - Sin torneos: texto "No hay torneos cargados todavia."
  - Boton "Crear torneo" → `start_create_flow()` (salta a Card Form con `is_creating=True`)
  - Boton "Editar torneo" → si `current_tournament is None` → toast "Selecciona torneo primero"
    - Si `current_tournament` existe → `start_edit_tournament()` (salta segun estado a EditChoiceCard o StatusCard)
  - Boton "Siguiente" → `disabled=True` hasta que `state.current_tournament != None`
  - Boton "Siguiente" habilitado → `go_next()` setea `step_index = 1`
- **Validation**:
  - Torneo seleccionado persiste al navegar a Card 2 y volver
  - Lista torneos se refresca si hay cambios BD (crear/editar torneo en otro flujo)
- **Error states**:
  - Fallo carga torneos → toast error + lista vacia
  - Click "Editar torneo" sin seleccion → toast informativo
  - Click torneo que ya no existe en BD → toast "Torneo no encontrado", limpia seleccion

### Spec: TournamentStatusCard (Card 2)

- **ID**: TC-02
- **When**: `step_index == 1` despues de seleccionar torneo
- **Given**: `current_tournament` existe, campos `name`, `status`, `venue`, `tatami_count`, etc. disponibles
- **Then**:
  - Renderiza resumen torneo: nombre, estado, sede, tatamis declarados, categorias count
  - Link "Ver bracket / Pantalla de competencia" → href a `/tournaments/{id}/bracket`
  - Controles de ciclo: mismos que `_lifecycle_card()` actual
    - `show_lifecycle_controls` gate por RBAC
    - Botones visibles segun `show_*_action` computed vars
    - Botones `disabled` si no hay torneo seleccionado
  - Transicion error: muestra `callout` rojo con `transition_error`
  - Boton "Anterior" → `go_previous()` setea `step_index = 0`, preserva seleccion
  - Boton "Siguiente" → comportamiento depende de estado:
    - BORRADOR: `can_go_next = True` → va al paso que corresponda:
      - Si `is_creating=True` y `create_flow_step >= 1` → va Categories
      - Sino → va Categories
    - INSCRIPCION+/EN_CURSO: `can_go_next = True` → va Categories (readonly)
    - ARCHIVADO: `can_go_next = False` → boton oculto o disabled
- **Validation**:
  - Resumen refleja datos frescos de BD (via `refresh_current_tournament_snapshot`)
  - Lifecycle actions ejecutan transicion y refrescan estado
  - Count categorias/tatamis se actualiza al volver a esta card
- **Error states**:
  - Torneo eliminado mientras estaba seleccionado → toast + volver Card 1
  - Transicion falla → `transition_error` visible en callout + toast

### Spec: TournamentFormCard (Card Crear/Editar)

- **ID**: TC-03
- **When**: `step_index == 2` y `is_creating=True` (crear) o `step_index == 2` y `is_editing_categories=False` (editar datos)
- **Given**: `TournamentCrudState` disponible con form fields y handlers
- **Then**:
  - Renderiza `_tournament_form()` de registries.py (reuso directo del componente)
  - Card title: "Crear torneo" (crear) o "Editar torneo" (editar)
  - Form campos: name, venue, start_date, end_date, tatami_count
  - Crear mode: `TournamentCrudState.set_form_values(_, None)` → form limpio
  - Editar mode: `TournamentCrudState.set_form_values(_, tournament)` → form precargado
  - Boton "Guardar" → `TournamentCrudState.save_tournament()`
  - Boton "Cancelar" → `TournamentCrudState.cancel_form()` + volver a Card de origen
  - **Crear success**: `save_tournament()` → auto-avance a CategoriesCard
    - `TournamentState.step_index = 3`, `create_flow_step = 1`
    - `is_creating=True` se mantiene
    - Toast success "Torneo creado"
  - **Editar success**: toast "Torneo actualizado" → vuelve a Card 2 (StatusCard)
  - Boton "Anterior" → segun contexto:
    - Crear flow: volver a Card 1
    - Edit flow: volver a EditChoiceCard o Card 1
- **Validation**:
  - Form validacion existente en `_validate_form()` se mantiene
  - Campos requeridos: name, venue, start_date, end_date
  - Nombre duplicado → error toast
  - Auto-avance solo ocurre en crear exitoso, jamas en editar
- **Error states**:
  - Error BD al guardar → mensaje error en form (no avanza)
  - Nombre torneo duplicado → toast + permanece en form
  - Fechas invalidas → mensaje validacion

### Spec: TournamentCategoriesCard (Card Categorias)

- **ID**: TC-04
- **When**: `step_index == 3`
- **Given**: `TournamentCategoryState.has_selected_tournament_context == True` (sync via `set_current_tournament`)
- **Then**:
  - Renderiza `_categories_card()` existente (reuso directo con wrapper)
  - Si `is_readonly_mode == True`:
    - Boton "Nueva categoria" oculto o disabled
    - Form categorias no se muestra (`show_form` force False)
    - Tabla categorias visible pero botones Editar/Eliminar ocultos
  - Si `is_readonly_mode == False`:
    - CRUD completo: crear, editar, eliminar categorias
    - Misma funcionalidad que existe actualmente
  - Boton "Anterior" → segun flujo:
    - Crear flow (`is_creating=True`): volver a Form card
    - Edit flow: volver a EditChoiceCard o Card 2
  - Boton "Siguiente" → `step_index = 4` (TatamisCard)
  - `can_go_next` siempre True (no requiere categorias minimas)
- **Validation**:
  - Guardar categoria exitoso: permanece en misma card (no auto-avance)
  - Eliminar categoria exitoso: tabla refresca
  - Readonly mode sincronizado con `TournamentState.is_readonly_mode`
- **Error states**:
  - Error guardar categoria → mensaje error en card
  - Error sync tournament context → texto "Selecciona un torneo para administrar sus categorias."
  - Readonly mode: toast si operador intenta editar via URL/event directo

### Spec: TournamentTatamisCard (Card Tatamis)

- **ID**: TC-05
- **When**: `step_index == 4`
- **Given**: `TournamentTatamiState.has_selected_tournament_context == True`
- **Then**:
  - Renderiza `_tatami_card()` existente (reuso directo con wrapper)
  - Readonly mode: mismo patron que CategoriesCard
    - Boton "Nuevo tatami" oculto
    - Form no disponible
    - Tabla solo lectura (sin Editar/Eliminar/Activar)
  - Boton "Anterior" → `step_index = 3` (CategoriesCard)
  - Boton "Siguiente" → comportamiento segun flujo:
    - Crear flow (`is_creating=True`): si hay mas pasos → `complete_create_flow()`
      - `complete_create_flow`: llama `start_competition()` o muestra confirmacion
      - Post-confirmacion → `step_index = 1` (StatusCard), `is_creating = False`
    - Edit flow: `step_index = 1` (StatusCard)
    - Flujo normal: boton oculto o pasa a siguiente paso configurado
- **Validation**:
  - Guardar tatami exitoso: permanece en misma card
  - Crear flow: ultimo paso antes de iniciar torneo
  - Transition to EN_CURSO sigue misma validacion que `start_competition`
- **Error states**:
  - Error al iniciar torneo → toast error, permanece en TatamisCard
  - Sin torneo contexto → texto informativo

### Spec: EditChoiceCard (Card Eleccion Editar)

- **ID**: TC-06
- **When**: `step_index == 2`, `is_creating=False`, `is_editing_categories=False`
- **Given**: `current_tournament.status == PLANIFICADO`
- **Then**:
  - Renderiza 2 botones grandes:
    - "Editar categorias" → `start_edit_categories()` (setea `is_editing_categories=True`, `step_index=3`)
    - "Editar datos torneo" → `go_to_step(2)` con modo editar datos (form)
  - Texto informativo: "Elige qué deseas editar del torneo '{nombre}'"
  - Boton "Anterior" → `step_index = 1` (o 0 segun de donde vino)
  - No hay boton "Siguiente" (es pantalla de eleccion)
- **Validation**:
  - Solo se muestra si `status == PLANIFICADO`
  - Si status INSCRIPCION: saltar directo a CategoriesCard (readonly categories)
  - Si status EN_CURSO/ARCHIVADO: saltar directo a StatusCard (readonly)
- **Error states**:
  - Estado torneo cambio entre Card 1 y eleccion → recalcular, si ya no es editable → toast + redirect a StatusCard

---

## 3. Specs de Navegacion

### Step Machine Behavior

```
step_index: int = 0        # card activa actual
step_count: int = 2         # total pasos disponibles (min)
max_reached_step: int = 0   # paso maximo alcanzado en esta sesion
```

**go_next()**:
- Valida `can_go_next` antes de avanzar
- Incrementa `step_index` en 1
- Actualiza `max_reached_step = max(max_reached_step, step_index)`
- Si paso destino tiene prerequisito (ej: sync categories/tatamis), ejecuta sync
- Si `step_index >= step_count`, no avanza (boton oculto/disabled)

**go_previous()**:
- Valida `can_go_previous` (step_index > 0)
- Decrementa `step_index` en 1
- No modifica `max_reached_step`

**can_go_next** (computed var):
```
False si:
  - step_index >= step_count
  - step_index == 0 AND current_tournament is None
  - current_tournament.status == ARCHIVADO AND step_index > 1
True en cualquier otro caso
```

**can_go_previous** (computed var):
```
True si step_index > 0
False si step_index == 0
```

**go_to_step(step: int)**:
- Solo llamado por eventos internos (crear flow, edit jumps)
- NO expuesto como navegacion de usuario
- Setea `step_index = step` directamente (sin validacion secuencial)
- Usado para saltar de Card 1 a Form/Categories/EditChoice segun accion

### Secuencial Estricto

- Usuario SOLO puede navegar paso adyacente (step+1 o step-1)
- Click "Siguiente" → step_index + 1
- Click "Anterior" → step_index - 1
- Sin botones de salto directo a Card 3 o Card 5
- Sin navegacion por URL params (step=? no existe)
- Excepcion: `go_to_step()` para eventos de crear/editar (saltos internos controlados)

### Reset al Entrar a /tournament

- `on_mount` / `load_workspace()`:
  ```python
  step_index = 0
  step_count = 2
  is_creating = False
  is_editing_categories = False
  max_reached_step = 0
  create_flow_step = 0
  ```
- `current_tournament` se recarga de BD (primer torneo auto-seleccionado)
- Siempre empieza en Card 1 (step_index = 0)

---

## 4. Specs de Permisos

### RBAC por Transicion de Estado

| Accion | Handler | Rol Requerido | Card |
|--------|---------|---------------|------|
| Navegar steps | `go_next/go_previous` | Cualquier autenticado | Todas |
| Seleccionar torneo | `set_current_tournament` | Cualquier autenticado | Card 1 |
| Crear torneo | `start_create_flow` + `save_tournament` | OPERADOR+ | Card Form |
| Editar torneo datos | `save_tournament` (edit mode) | OPERADOR+ | Card Form |
| Editar categorias | `save_category`/`delete_category` | OPERADOR+ | Card 3 |
| Editar tatamis | `save_tatami`/`delete_tatami` | OPERADOR+ | Card 4 |
| Transition lifecycle | `open_registrations`, etc. | OPERADOR+ (via `MANAGE_TOURNAMENT_STATUS_ROLE`) | Card 2 |
| Cancelar torneo | `cancel_tournament` | ADMIN | Card 2 |

### Acciones que Requieren Rol OPERADOR

- Crear/editar torneo
- CRUD categorias
- CRUD tatamis
- Transiciones de ciclo de vida (abrir/cerrar inscripciones, iniciar/finalizar competencia)
- Gestion de QR

**Sin permisos**: usuario autenticado puede ver cards y navegar, pero no modificar nada.

### Readonly Mode para Torneos Avanzados

- `is_readonly_mode` computed var:
  ```python
  @rx.var
  def is_readonly_mode(self) -> bool:
      status = self._current_status()
      if not status:
          return False
      return status in {
          TournamentStatus.INSCRIPCION,
          TournamentStatus.VERIFICACION,
          TournamentStatus.EN_CURSO,
          TournamentStatus.FINALIZADO,
          TournamentStatus.ARCHIVADO,
      }
  ```

- Modo readonly afecta:
  - CategoriesCard: tabla solo lectura, sin botones crear/editar/eliminar
  - TatamisCard: tabla solo lectura, sin botones crear/editar/activar
  - FormCard: campos deshabilitados si se accede desde editar
  - Lifecycle controls: siguen siendo visibles segun `show_*_action` (no cambian)

- `is_readonly_mode` se sincroniza a substates via `set_current_tournament`:
  - `TournamentCategoryState._readonly_mode = TournamentState.is_readonly_mode`
  - `TournamentTatamiState._readonly_mode = TournamentState.is_readonly_mode`

---

## 5. Specs de UI/UX

### Transiciones Animadas entre Cards

- Cada card wrapper usa:
  ```python
  rx.box(
      _card_content(),
      opacity="1",
      transform="translateX(0)",
      transition="all 0.3s ease",
  )
  ```
- Transicion slide horizontal:
  - `go_next`: card actual slide out left → nueva card slide in from right
  - `go_previous`: card actual slide out right → prev card slide in from left
- **Simplificacion**: usar `rx.motion` con `animate={{ opacity: 1, x: 0 }}` si Reflex lo soporta. Alternativa: CSS classes via `class_name`.

### Step Indicator

- Dots de progreso en horizontal:
  ```python
  def _step_indicator() -> rx.Component:
      steps = ["Seleccion", "Estado", "Categorias", "Tatamis"]
      return rx.hstack(
          rx.foreach(
              steps,
              lambda step, i: rx.hstack(
                  rx.box(
                      width="12px", height="12px",
                      border_radius="50%",
                      bg=rx.cond(i <= step_index, "blue.500", "gray.300"),
                  ),
                  rx.text(step, font_size="xs"),
              ),
          ),
          spacing="2",
      )
  ```
- Note: dot activo = paso completado o actual
- Dot futuro = gris
- Mobile: solo dots, sin labels de texto

### Responsive (Mobile + Desktop)

| Breakpoint | Comportamiento |
|------------|----------------|
| Desktop (>=768px) | Card centrado, max-width 800px. Step indicator horizontal arriba. Navigation bar horizontal abajo. |
| Mobile (<768px) | Card full-width. Step indicator horizontal (solo dots, sin labels). Navigation bar vertical stack o botones full-width. |
| Botones | Desktop: inline con espaciado. Mobile: `width="100%"` stack vertical. |

### i18n (ES/EN)

- Todos los textos de UI usan patron existente:
  ```python
  rx.cond(
      State.lang == "en",
      "English text",
      "Texto español",
  )
  ```
- Strings clave a traducir:
  - Step labels: "Seleccion"/"Selection", "Estado"/"Status", "Categorias"/"Categories", "Tatamis"/"Tatamis"
  - Botones: "Siguiente"/"Next", "Anterior"/"Back", "Crear torneo"/"Create tournament", "Editar torneo"/"Edit tournament"
  - Estados torneo: "BORRADOR"/"DRAFT", etc.
  - Mensajes info/error: "No hay torneos cargados"/"No tournaments loaded", etc.

### Accesibilidad WCAG AA

| Requisito | Implementacion |
|-----------|----------------|
| Roles ARIA | `role="region"` en cada card con `aria-label` descriptivo |
| Focus management | `ref` + `focus()` en primer elemento interactivo al cambiar step |
| Skip links | Saltar navegacion repetitiva |
| Contraste | 4.5:1 ratio texto/fondo |
| Keyboard nav | Tab entre steps via arrows keys |
| Screen reader | `aria-live="polite"` en area de card para anunciar cambios |
| Botones | `aria-disabled` en lugar de `disabled` para mantener focus |
| Step indicator | `aria-current="step"` en dot activo |

---

## 6. Criterios de Aceptacion (Gherkin)

```gherkin
FEATURE: Tournament Sequential Card Flow

  SCENARIO: Happy path crear torneo completo
    Given estoy en Card 1 (Seleccion)
    When click "Crear torneo"
    Then veo TournamentFormCard con form vacio
    When lleno campos requeridos y click "Guardar"
    Then torneo creado en estado PLANIFICADO
    And auto-avanzo a CategoriesCard
    When creo una categoria y click "Guardar"
    Then permanezco en CategoriesCard
    And click "Siguiente"
    Then veo TatamisCard
    When configuro un tatami y click "Siguiente"
    Then veo StatusCard con resumen del torneo
    And el torneo aparece en la lista de Card 1

  SCENARIO: Happy path editar torneo BORRADOR
    Given existe un torneo en PLANIFICADO
    And estoy en Card 1 con ese torneo seleccionado
    When click "Editar torneo"
    Then veo EditChoiceCard
    When click "Editar datos torneo"
    Then veo TournamentFormCard con datos precargados
    When modifico nombre y click "Guardar"
    Then torneo actualizado
    And vuelvo a StatusCard con datos nuevos

  SCENARIO: Seleccionar torneo y ver estado
    Given estoy en Card 1 (Seleccion)
    When selecciono un torneo existente
    Then boton "Siguiente" se habilita
    When click "Siguiente"
    Then veo Card 2 (StatusCard) con resumen del torneo
    And veo controles de ciclo segun permisos
    When click "Anterior"
    Then vuelvo a Card 1
    And el torneo sigue seleccionado

  SCENARIO: Navegacion atras/adelante secuencial
    Given estoy en Card 2 (StatusCard)
    When click "Anterior"
    Then estoy en Card 1 (Seleccion)
    When click "Siguiente"
    Then estoy en Card 2 otra vez
    When intento navegar directamente a Card 4 via URL
    Then permanezco en Card 2
    And la navegacion secuencial se mantiene

  SCENARIO: Intento editar torneo EN_CURSO
    Given existe un torneo en EN_CURSO
    When lo selecciono y click "Editar torneo"
    Then veo StatusCard (no EditChoiceCard)
    When navego a CategoriesCard
    Then tabla categorias visible pero solo lectura
    And botones crear/editar/eliminar ocultos
    When navego a TatamisCard
    Then misma restriccion readonly

  SCENARIO: Operador sin permisos intenta transicion
    Given estoy en Card 2
    And no tengo rol OPERADOR
    Then no veo controles de ciclo
    And veo texto "No tienes permisos para operar ciclo de torneo."
    When click "Siguiente" (si existe)
    Then veo CategoriesCard en modo readonly

  SCENARIO: Volver a /tournament siempre muestra Card 1
    Given estaba en Card 4 (TatamisCard)
    When navego a otra pagina y vuelvo a /tournament
    Then veo Card 1 (Seleccion)
    And step_index es 0
    And is_creating es False
```
