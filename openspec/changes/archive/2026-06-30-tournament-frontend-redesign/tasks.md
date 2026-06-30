# Tasks: Tournament Frontend Redesign - Sequential Card Flow

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~978 (gross) / ~602 (net) |
| 400-line budget risk | **High** |
| Chained PRs recommended | **Yes — 2 PRs recommended** (PR1: Phase 1+2, PR2: Phase 3+4+5) |
| Decision needed before apply | **Yes** — confirm bridge pattern for TournamentCrudState (wrapper handler vs. rx.cond chain) |

### Line count breakdown

| File | Lines added | Lines removed | Net change |
|------|-------------|---------------|------------|
| `kakumi_app/states/tournament_state.py` | ~185 | 0 | +185 |
| `kakumi_app/pages/tournament.py` | ~355 | ~188 | +167 |
| `tests/test_tournament_step_navigation.py` | ~250 | 0 | +250 |

---

## Phase 1: State Foundation

**Prereq**: none
**Files**: `kakumi_app/states/tournament_state.py`
**Goal**: Add step machine vars, handlers, computed guards, and flow handlers to TournamentState. No UI changes yet.

---

### T-01: Add step machine constants and state vars

**File**: `kakumi_app/states/tournament_state.py`

**What**:
- Add step index constants at module level (before class):
  ```python
  SELECTION_STEP = 0
  STATUS_STEP = 1
  FORM_STEP = 2
  CATEGORIES_STEP = 3
  TATAMIS_STEP = 4
  CONFIRM_STEP = 5
  EDIT_CHOICE_STEP = 6
  ```
- Add new state vars to TournamentState:
  ```python
  step_index: int = 0
  step_count: int = 7
  create_mode: bool = False
  edit_mode: bool = False
  _form_saved_tournament_id: int = 0
  ```

**Completion criteria**:
- Constants accessible as `SELECTION_STEP`, `STATUS_STEP`, etc.
- State vars present with correct defaults on fresh TournamentState()
- All vars JSON-serializable (int/bool)

**Estimate**: +12 lines

---

### T-02: Add navigation handlers (go_next, go_previous, go_to_step)

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add three @rx.event handlers:

**go_next()**:
- Validate `can_go_next` before advancing
- Increment `step_index` by 1
- Update `max_reached_step = max(max_reached_step, step_index)` (note: `max_reached_step` not in spec vars — confirm if needed or drop)
- If step >= step_count, block (no-op)

**go_previous()**:
- Validate `can_go_previous` (step_index > 0)
- Decrement `step_index` by 1
- No change to `max_reached_step`

**go_to_step(target_step: int)**:
- Internal-only handler (not exposed as user navigation)
- Set `step_index = target_step` directly (no sequential validation)
- Used by create/edit flow jumps

**Completion criteria**:
- `go_next()` increments step_index when can_go_next is True
- `go_next()` does nothing when step_index >= step_count - 1
- `go_previous()` decrements step_index when step_index > 0
- `go_previous()` does nothing when step_index == 0
- `go_to_step(3)` sets step_index = 3 regardless of current step

**Estimate**: +30 lines

---

### T-03: Add computed guards (can_go_next, can_go_previous, is_readonly_mode)

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add three @rx.var computed properties:

**can_go_next → bool**:
- `False` if `step_index >= step_count - 1`
- `False` if `step_index == 0 AND current_tournament is None`
- `False` if `_current_status() == ARCHIVADO AND step_index > 0`
- Otherwise `True`

**can_go_previous → bool**:
- `True` if `step_index > 0`
- `False` if `step_index == 0`

**is_readonly_mode → bool**:
- `False` if no `current_tournament`
- `True` if tournament status in {INSCRIPCION, VERIFICACION, EN_CURSO, FINALIZADO, ARCHIVADO}
- `False` for PLANIFICADO

**Completion criteria**:
- All three vars return correct bool for each state combination
- `is_readonly_mode` returns True for INSCRIPCION, VERIFICACION, EN_CURSO, FINALIZADO, ARCHIVADO
- `can_go_next` returns False when step_index 0 and no tournament selected
- `can_go_previous` returns False at step_index 0

**Estimate**: +25 lines

---

### T-04: Add transition validation (_validate_step_transition)

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add private method `_validate_step_transition(self, from_step: int, to_step: int) -> bool`.

Transition map:
```
Normal: step_n ↔ step_n±1 (always allowed within [0, step_count-1])
Create shortcut: 0 → 2 (when create_mode=True)
Create flow: 2→3, 3→4, 4→5 (when create_mode=True)
Create done: 5→1
Edit shortcut: 0→6 (when edit_mode=True)
Edit→form: 6→2 (when edit_mode=True)
Edit→categories: 6→3 (when edit_mode=True)
Form saved (edit): 2→1 (when not create_mode)
Categories done: 3→1 (when edit_mode=True)
Cancel form: 2→0 (when not create_mode)
Edit cancel: 6→1, 6→0 (when edit_mode=True)
```

Guard: if `to_step >= 1` and `not has_selected_tournament` and `to_step not in (0, 6)`, return False.

**Completion criteria**:
- `abs(to - from) == 1` always allowed within [0, step_count-1]
- Special transitions return True only when mode flags match
- Invalid transitions return False
- Guard blocks step >= 1 without tournament selected

**Estimate**: +45 lines

---

### T-05: Add flow handlers (start_create_flow, start_edit_flow, complete_create_flow, advance_after_form_saved)

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add four @rx.event handlers:

**start_create_flow()**:
- `create_mode = True`, `edit_mode = False`
- Reset `TournamentCrudState` form (via `TournamentCrudState.set_form_values(_, None)`)
- `go_to_step(FORM_STEP)` (jump to form card)

**start_edit_flow()**:
- If no `current_tournament`: toast "Selecciona torneo primero", return
- `edit_mode = True`, `create_mode = False`
- If `_current_status() == PLANIFICADO`: `go_to_step(EDIT_CHOICE_STEP)` (show edit choice)
- Else if `is_readonly_mode`: `go_to_step(CATEGORIES_STEP)` (direct to readonly categories)
- Else: `go_to_step(STATUS_STEP)` (fallback)

**complete_create_flow()**:
- Get tournament_id via `_get_tournament_id()`
- Call `_execute_transition(EN_CURSO)` (start competition)
- On success: `create_mode = False`, `go_to_step(STATUS_STEP)`
- On failure: stay on current step, show toast error

**advance_after_form_saved()**:
- If `create_mode`: `TournamentState.create_mode` stays True, `_form_saved_tournament_id` is set, `go_to_step(CATEGORIES_STEP)`
- If not `create_mode` (edit): `go_to_step(STATUS_STEP)`
- If save failed (error_message), don't advance

**Completion criteria**:
- `start_create_flow()` sets create_mode=True, jumps to step 2 (FORM_STEP)
- `start_edit_flow()` on PLANIFICADO tournament jumps to step 6 (EDIT_CHOICE_STEP)
- `start_edit_flow()` on EN_CURSO tournament jumps to step 3 (CATEGORIES_STEP, readonly)
- `advance_after_form_saved()` with create_mode goes to CATEGORIES_STEP
- `advance_after_form_saved()` without create_mode goes to STATUS_STEP
- `complete_create_flow()` transitions tournament to EN_CURSO and goes to STATUS_STEP

**Estimate**: +45 lines

---

### T-06: Add bridge handler (handle_form_submit)

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add @rx.event handler `handle_form_submit()` that wraps `TournamentCrudState.save_tournament()`.

```python
@rx.event
async def handle_form_submit(self) -> None:
    """Bridge: delegates to TournamentCrudState, advances step on success."""
    crud = await self.get_state(TournamentCrudState)
    await crud.save_tournament()

    if not crud.show_form and not crud.error_message:
        self._form_saved_tournament_id = (
            crud.current_tournament.get("id", 0) if crud.current_tournament else 0
        )
        await self.advance_after_form_saved()
```

Also need import: add `TournamentCrudState` to imports.

**Completion criteria**:
- `handle_form_submit()` calls `crud.save_tournament()` via get_state
- On success (show_form=False, no error), sets `_form_saved_tournament_id` and calls advance
- On failure, does not advance
- Import of `TournamentCrudState` added

**Estimate**: +20 lines (+1 import line)

---

### T-07: Modify load_workspace to reset step machine

**File**: `kakumi_app/states/tournament_state.py`

**What**: Add reset lines at beginning of `load_workspace()`:
```python
self.step_index = 0
self.create_mode = False
self.edit_mode = False
self._form_saved_tournament_id = 0
```

**Completion criteria**:
- After `load_workspace()`, all step machine vars are at initial values
- Existing load_workspace behavior preserved (load tournaments, auto-select first)

**Estimate**: +5 lines

---

## Phase 2: Page Layout Restructure

**Prereq**: Phase 1
**Files**: `kakumi_app/pages/tournament.py`
**Goal**: Replace rx.grid with sequential card flow. Add _active_card(), _step_indicator(), _navigation_bar(). New card placeholders initially empty.

---

### T-08: Add _step_indicator() component

**File**: `kakumi_app/pages/tournament.py`

**What**: Add function returning progress dots:

```python
def _step_indicator() -> rx.Component:
    """Progress dots. Hidden on step 0. Show active/visited dots in brand red."""
    state = TournamentState
    return rx.cond(
        TournamentState.step_index > 0,
        rx.hstack(
            rx.foreach(
                TournamentState._step_labels,
                lambda label, idx: rx.tooltip(
                    rx.box(
                        width="12px",
                        height="12px",
                        border_radius="50%",
                        bg=rx.cond(
                            TournamentState.step_index >= idx,
                            BRAND_RED,
                            "gray.300",
                        ),
                        opacity=rx.cond(
                            TournamentState.step_index == idx,
                            "1",
                            rx.cond(
                                TournamentState.step_index > idx,
                                "0.8",
                                "0.4",
                            ),
                        ),
                    ),
                    label=label,
                ),
            ),
            justify="center",
            spacing="3",
            width="100%",
            padding_y="2",
        ),
    )
```

Also add `_step_labels` computed var to TournamentState (if not in T-01..T-07):
```python
@rx.var
def _step_labels(self) -> list[str]:
    """Dynamic step labels based on mode."""
    if self.create_mode:
        return [
            "Seleccion", "Estado", "Formulario",
            "Categorias", "Tatamis", "Confirmar",
        ]
    if self.edit_mode:
        return [
            "Seleccion", "Estado", "Editar",
            "Categorias", "Tatamis",
        ]
    return [
        "Seleccion", "Estado",
        "Categorias", "Tatamis",
    ]
```

Import `BRAND_RED` from styles.tokens if not already imported.

**Completion criteria**:
- `_step_indicator()` renders rx.hstack with dots when step_index > 0
- Dots for visited/current step use brand color, future dots gray
- Hidden when step_index == 0
- `_step_labels` returns correct labels based on create_mode/edit_mode

**Estimate**: +40 lines in tournament.py, +20 lines in tournament_state.py (if _step_labels not already added)

---

### T-09: Add _navigation_bar() component

**File**: `kakumi_app/pages/tournament.py`

**What**: Add function rendering prev/next buttons:

```python
def _navigation_bar() -> rx.Component:
    """Render Anterior/Siguiente buttons. Handle context-sensitive labels."""
    state = TournamentState
    return rx.hstack(
        rx.button(
            "← Anterior",
            on_click=state.go_previous,
            disabled=~state.can_go_previous,
            variant="outline",
        ),
        rx.hstack(
            rx.cond(
                (TournamentState.step_index == CONFIRM_STEP)
                & TournamentState.create_mode,
                rx.button(
                    "Comenzar torneo",
                    on_click=state.complete_create_flow,
                    color_scheme="green",
                ),
                rx.button(
                    rx.cond(
                        TournamentState.step_index >= TournamentState.step_count - 1,
                        "Finalizar",
                        "Siguiente →",
                    ),
                    on_click=state.go_next,
                    disabled=~state.can_go_next,
                    color_scheme="red",
                ),
            ),
        ),
        justify="between",
        width="100%",
        padding_top="4",
    )
```

Import step constants from TournamentState (or define locally).
Use `CONFIRM_STEP` constant for comparison.

**Completion criteria**:
- "← Anterior" button visible and enabled when can_go_previous is True
- "← Anterior" disabled/hidden when step_index == 0
- "Siguiente →" button enabled when can_go_next is True
- On confirm step (5) with create_mode, shows "Comenzar torneo" instead
- Button responsive: stack vertically on mobile

**Estimate**: +40 lines

---

### T-10: Add _active_card() dispatch and refactor tournament() layout

**File**: `kakumi_app/pages/tournament.py`

**What**:
- Add `_active_card()` function using `rx.match(TournamentState.step_index, ...)` to render the correct card
- Replace `rx.grid(...)` in `tournament()` body with sequential layout:
  ```python
  def tournament() -> rx.Component:
      body = rx.vstack(
          _workspace_header(),
          _step_indicator(),
          _active_card(),
          _navigation_bar(),
          spacing="4",
          width="100%",
          max_width="800px",  # centered card
          margin_x="auto",
      )
      return registry_page_shell(body=body)
  ```

**Completion criteria**:
- `tournament()` no longer uses `rx.grid()`
- Layout is: header → step_indicator → active_card → navigation_bar
- `_active_card()` dispatches to correct card component via rx.match(step_index)
- Cards 0-6 all have entries in rx.match (even if initially placeholder)
- `max_width="800px"` centers the card
- `registry_page_shell` wrapping preserved

**Estimate**: +30 lines (replace ~10 lines grid with ~30 lines sequential)

---

## Phase 3: Card Components

**Prereq**: Phase 2
**Files**: `kakumi_app/pages/tournament.py`
**Goal**: Build all 7 card components. Reuse existing code where possible.

---

### T-11: Create TournamentSelectorCard (card 0)

**File**: `kakumi_app/pages/tournament.py`

**What**: Refactor existing `_selector_card()` to add create/edit action buttons:

```python
def _selector_card() -> rx.Component:
    """Card 0: Tournament selection list with create/edit actions."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Torneos disponibles", size="5"),
            # Tournament list (reuse existing foreach pattern)
            rx.cond(
                state.tournaments.length() == 0,
                rx.text("No hay torneos cargados todavia."),
                rx.foreach(
                    state.tournaments,
                    lambda tournament: rx.button(
                        tournament["name"],
                        width="100%",
                        variant=rx.cond(
                            state.current_tournament,
                            rx.cond(
                                state.current_tournament["id"] == tournament["id"],
                                "solid",
                                "outline",
                            ),
                            "outline",
                        ),
                        on_click=state.set_current_tournament(tournament["id"]),
                    ),
                ),
            ),
            # Action buttons row
            rx.hstack(
                rx.button(
                    "Crear torneo",
                    on_click=state.start_create_flow,
                    color_scheme="green",
                ),
                rx.button(
                    "Editar torneo",
                    on_click=state.start_edit_flow,
                    variant="outline",
                ),
                spacing="2",
                width="100%",
                justify="center",
            ),
            spacing="3",
            align="stretch",
            width="100%",
        ),
        width="100%",
    )
```

Note: "Siguiente" button is NOT in the card — it lives in `_navigation_bar()`.

**Completion criteria**:
- Tournament list renders as buttons (same pattern as current code)
- Selected tournament shown as "solid" variant, others as "outline"
- "Crear torneo" button calls start_create_flow
- "Editar torneo" button calls start_edit_flow
- Empty state text shown when no tournaments
- No "Siguiente" button inside card (moved to nav bar)

**Estimate**: +55 lines (modifies existing _selector_card)

---

### T-12: Create TournamentStatusCard (card 1)

**File**: `kakumi_app/pages/tournament.py`

**What**: New card merging `_selection_summary()` + lifecycle buttons + QR section:

```python
def _status_card() -> rx.Component:
    """Card 1: Tournament summary, lifecycle controls, and QR."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Estado del torneo", size="5"),
            # Selection summary (reuse _selection_summary() body inline or as call)
            _selection_summary(),
            # Lifecycle controls (reuse conditional from _lifecycle_card)
            rx.cond(
                state.show_lifecycle_controls,
                rx.vstack(
                    rx.divider(),
                    rx.heading("Controles de ciclo", size="4"),
                    _lifecycle_buttons(),  # extract from existing _lifecycle_card
                    spacing="2",
                    width="100%",
                ),
                rx.cond(
                    state.has_selected_tournament,
                    rx.text("No tienes permisos para operar ciclo de torneo."),
                ),
            ),
            # Transition error
            rx.cond(
                state.transition_error,
                rx.callout(state.transition_error, icon="triangle_alert", color="red"),
            ),
            # QR section (moved from _qr_card)
            rx.divider(),
            _qr_section(),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
    )
```

**Helper extraction**:
- Extract `_lifecycle_buttons()` from current `_lifecycle_card()` (the button groups inside rx.cond(state.show_lifecycle_controls, ...))
- Extract `_qr_section()` from current `_qr_card()` (the QR content without card wrapper)

**Cleanup**: Remove old `_lifecycle_card()` and `_qr_card()` functions.

**Completion criteria**:
- Shows tournament summary (name, status, venue, tatami_count)
- Lifecycle buttons visible when show_lifecycle_controls is True
- "No tienes permisos" text shown for viewers
- QR section visible (generate/regenerate/image)
- Transition error callout shown when error exists
- Old _lifecycle_card() and _qr_card() removed
- _lifecycle_buttons() and _qr_section() extracted as reusable helpers

**Estimate**: +120 lines added, -158 lines removed (_lifecycle_card + _qr_card)

---

### T-13: Create TournamentFormCard (card 2)

**File**: `kakumi_app/pages/tournament.py`

**What**: Card wrapper that reuses `_tournament_form()` from `registries.py`:

```python
from kakumi_app.pages.registries import _tournament_form
```

```python
def _form_card() -> rx.Component:
    """Card 2: Tournament create/edit form."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading(
                rx.cond(state.create_mode, "Crear torneo", "Editar torneo"),
                size="5",
            ),
            _tournament_form(),  # from registries.py, binds TournamentCrudState
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

Need to override submit handler: original form calls `TournamentCrudState.save_tournament()` directly via `on_submit`. To bridge, either:
- Option A (recommended): Change `on_submit` in the imported form to call `TournamentState.handle_form_submit()` instead of `TournamentCrudState.save_tournament()`. This requires the form to accept an optional `on_submit` param.
- Option B: Wrap the form inside TournamentFormCard with a new form that intercepts submit.

Recommend Option A: modify `_tournament_form()` signature to accept `on_submit_override: Optional[Any] = None`, defaulting to `TournamentCrudState.save_tournament`. In the card, pass `TournamentState.handle_form_submit`.

**Alternative simpler approach**: Keep `_tournament_form()` as-is. Add a `rx.cond` observer in the card that watches `TournamentCrudState.show_form` and triggers advance on change. This avoids modifying registries.py.

**Decision needed during apply**: Which bridge approach?

**Completion criteria**:
- Card renders _tournament_form() content
- Title is "Crear torneo" when create_mode, "Editar torneo" otherwise
- Form fields bound to TournamentCrudState
- Submit triggers flow advance via bridge

**Estimate**: +35 lines in tournament.py, +5 lines in registries.py (if Option A)

---

### T-14: Create TournamentCategoriesCard wrapper (card 3)

**File**: `kakumi_app/pages/tournament.py`

**What**: Wrapper around existing `_categories_card()` body:

```python
def _categories_card() -> rx.Component:
    """Card 3: Category CRUD (reuses existing component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Categorias", size="5"),
            _existing_categories_content(),  # paste current _categories_card() body
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

Where `_existing_categories_content()` is the `rx.vstack(...)` body inside the current `_categories_card()` function's `rx.card(...)`.

Readonly adapt: wrap "Nueva categoria" button and "Editar"/"Eliminar" action buttons with `rx.cond(~TournamentState.is_readonly_mode, ...)`.

**Completion criteria**:
- All existing category CRUD functionality preserved
- Wrapped inside rx.card with heading
- "Nueva categoria" button hidden when is_readonly_mode
- Editar/Eliminar buttons hidden when is_readonly_mode
- Form fields and table render correctly

**Estimate**: +30 lines (modifies existing _categories_card)

---

### T-15: Create TournamentTatamisCard wrapper (card 4)

**File**: `kakumi_app/pages/tournament.py`

**What**: Same pattern as CategoriesCard — wrap existing _tatami_card() body:

```python
def _tatamis_card() -> rx.Component:
    """Card 4: Tatami CRUD (reuses existing component)."""
    return rx.card(
        rx.vstack(
            rx.heading("Tatamis", size="5"),
            _existing_tatami_content(),  # paste current _tatami_card() body
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

Readonly adapt: same pattern as categories — hide Nuevo/Editar/Eliminar/Activar when `is_readonly_mode`.

**Completion criteria**:
- All existing tatami CRUD functionality preserved
- Wrapped inside rx.card with heading
- Nuevo/Editar/Eliminar/Activar hidden when is_readonly_mode
- Table and badges render correctly

**Estimate**: +30 lines (modifies existing _tatami_card)

---

### T-16: Create RegistrationControlCard (card 5, new)

**File**: `kakumi_app/pages/tournament.py`

**What**: New card for create flow confirmation step:

```python
def _registration_control_card() -> rx.Component:
    """Card 5: Create flow — review and start competition."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Confirmar inicio", size="5"),
            rx.text("El torneo se creo correctamente."),
            rx.text("Revisa categorias y tatamis antes de iniciar."),
            rx.text(
                "Al clickear 'Comenzar torneo' se iniciara la competencia.",
                font_size="sm",
                color_scheme="gray",
            ),
            rx.divider(),
            rx.text(
                f"Torneo: {state.current_tournament['name']}",
                weight="bold",
            ) if state.current_tournament else rx.fragment(),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
    )
```

Note: the "Comenzar torneo" button lives in `_navigation_bar()` (see T-09), not inside the card.

**Completion criteria**:
- Shows confirmation text
- Shows tournament name
- "Comenzar torneo" only shown via nav bar on this step
- Only reachable during create flow

**Estimate**: +30 lines

---

### T-17: Create EditChoiceCard (card 6, new)

**File**: `kakumi_app/pages/tournament.py`

**What**: New card for edit flow — user chooses what to edit:

```python
def _edit_choice_card() -> rx.Component:
    """Card 6: Edit flow — choose what to edit."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("¿Que deseas editar?", size="5"),
            rx.text(
                f"Torneo: {state.current_tournament['name']}"
                if state.current_tournament
                else "Selecciona un torneo"
            ),
            rx.vstack(
                rx.button(
                    "Editar categorias",
                    on_click=state.go_to_step(CATEGORIES_STEP),
                    width="100%",
                ),
                rx.cond(
                    ~state.is_readonly_mode,
                    rx.button(
                        "Editar datos del torneo",
                        on_click=state.go_to_step(FORM_STEP),
                        width="100%",
                        variant="outline",
                    ),
                ),
                spacing="2",
                width="100%",
            ),
            rx.cond(
                state.is_readonly_mode,
                rx.callout(
                    "Solo visualizacion disponible para torneos avanzados.",
                    icon="info",
                ),
            ),
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

**Completion criteria**:
- Shows tournament name
- "Editar categorias" button calls go_to_step(3)
- "Editar datos del torneo" button visible only when NOT readonly
- "Solo visualizacion" callout shown when readonly
- "Anterior" in nav bar returns to status or selector

**Estimate**: +40 lines

---

## Phase 4: Flow Integration

**Prereq**: Phase 1 + Phase 3
**Files**: `kakumi_app/pages/tournament.py` + `kakumi_app/states/tournament_state.py`
**Goal**: Wire all flows end-to-end. Readonly mode gating. RBAC integration.

---

### T-18: Implement create flow end-to-end

**Files**: `kakumi_app/states/tournament_state.py`, `kakumi_app/pages/tournament.py`

**What**: Wire the complete create tournament flow:

1. User clicks "Crear torneo" in Card 0
2. `start_create_flow()` → create_mode=True, go_to_step(2)
3. Card 2 (FormCard) shows empty form → user fills in
4. User clicks "Guardar" → `handle_form_submit()` (bridge) → save via TournamentCrudState
5. On success: `advance_after_form_saved()` → go_to_step(3) (Categories)
6. Card 3 (CategoriesCard) → user adds categories, clicks "Siguiente"
7. go_next() → step=4 (TatamisCard)
8. Card 4 → user adds tatamis, clicks "Siguiente"
9. go_next() → step=5 (ConfirmCard)
10. Nav bar shows "Comenzar torneo" → calls complete_create_flow()
11. complete_create_flow() → calls _execute_transition(EN_CURSO) → go_to_step(1)
12. Card 1 (StatusCard) shows tournament with EN_CURSO status

**Edge cases**:
- Save failure: stay on form, show error
- Transition failure: stay on confirm, show toast error
- User clicks "Anterior" during flow: returns to previous step

**Completion criteria**:
- Full create flow works end-to-end (selector → form → categories → tatamis → confirm → status)
- Save creates tournament in DB with PLANIFICADO status
- Auto-advance after form save to Categories
- Cancel from form returns to selector
- Complete_create_flow transitions to EN_CURSO

**Estimate**: +0 new lines (wires existing T-05 + T-13 + nav bar)

---

### T-19: Implement edit flow end-to-end

**Files**: `kakumi_app/states/tournament_state.py`, `kakumi_app/pages/tournament.py`

**What**: Wire the complete edit tournament flow:

1. User selects tournament, clicks "Editar torneo" in Card 0
2. `start_edit_flow()`:
   - If PLANIFICADO: go_to_step(6) (EditChoiceCard)
   - If INSCRIPCION+: go_to_step(3) (CategoriesCard, readonly)
3. EditChoiceCard: user picks "Editar categorias" or "Editar datos"
4. "Editar categorias" → go_to_step(3) → user edits via existing CRUD
5. "Editar datos" → go_to_step(2) → TournamentCrudState.set_form_values pre-fills
6. User saves → advance_after_form_saved() → go_to_step(1) (StatusCard)
7. "Anterior" from EditChoiceCard: go back to Card 0 or 1

**Edge cases**:
- Tournament status changed between selection and edit → re-check status
- Edit form cancel: return to StatusCard (not selector)
- Edit categories done: go to StatusCard (not further steps)

**Completion criteria**:
- PLANIFICADO tournament: EditChoiceCard shows with both options
- INSCRIPCION+ tournament: direct to CategoriesCard readonly
- Edit form saves and returns to StatusCard
- Edit categories and manual return to StatusCard via "Siguiente"
- Cancel from edit form returns to StatusCard

**Estimate**: +0 new lines (wires existing T-05 + T-17)

---

### T-20: Implement readonly mode in cards

**Files**: `kakumi_app/pages/tournament.py`

**What**: Gate all mutation UI behind `is_readonly_mode` computed var.

**In Cards 0-6**:

**Card 0 (Selector)**: No readonly — selection is always allowed.
**Card 1 (Status)**: Lifecycle buttons unaffected (already gated by show_lifecycle_controls).
**Card 2 (Form)**: Disable form fields when `is_readonly_mode`. Show "Solo lectura" banner.
**Card 3 (Categories)**: 
  - "Nueva categoria" button: `rx.cond(~TournamentState.is_readonly_mode, ...)`
  - Editar/Eliminar buttons in table: `rx.cond(~TournamentState.is_readonly_mode, ...)`
  - Form hidden when readonly (force show_form=False)
**Card 4 (Tatamis)**:
  - "Nuevo tatami": gated
  - Editar/Eliminar/Activar: gated
**Card 5 (Confirm)**: Not affected (only shown in create flow, never readonly)
**Card 6 (Edit)**: "Editar datos" button hidden when readonly

Implementation in CategoriesCard:
```python
# "Nueva categoria" button
rx.cond(
    ~TournamentState.is_readonly_mode,
    rx.button("Nueva categoria", on_click=state.set_form_values),
)
```

**Completion criteria**:
- CategoriesCard: CRUD buttons hidden when tournament is INSCRIPCION+
- TatamisCard: mutation buttons hidden when tournament is INSCRIPCION+
- FormCard: shows readonly banner when tournament is INSCRIPCION+
- EditChoiceCard: hides "Editar datos" when readonly
- Categories/Tatamis form does not open when readonly
- No backend changes — readonly is purely UI gating

**Estimate**: +20 lines (rx.cond wrappers)

---

### T-21: RBAC integration (viewer restrictions)

**Files**: `kakumi_app/pages/tournament.py`

**What**: Use existing `show_lifecycle_controls` rx.var and `AuthService.check_permission` to gate operator-only actions.

**In Card 0**:
- "Crear torneo" button: wrap with `rx.cond(state.show_lifecycle_controls, ...)`
- Viewers see only the tournament list + selection, no create/edit buttons

**In Card 1**:
- Lifecycle buttons already gated by `show_lifecycle_controls`
- QR section: always visible (viewers can see QR but not regenerate — gate regenerate button)

**In Card 2**:
- Form is operator-only — viewers should not reach this card
- If reached via URL/edge case: show "No tienes permisos" text

**In Card 3**:
- Categories CRUD buttons: only shown to operators (via is_readonly_mode which encompasses both tournament status and role)
- Note: `is_readonly_mode` is about tournament status, not role. Need separate `_is_operator` check or rely on existing patterns.

**Decision needed**: In the current code, `is_readonly_mode` gates by tournament status. Viewer restrictions for categories CRUD are handled by `show_lifecycle_controls` (which checks RBAC). Need to decide if Categories/Tatamis card should also check operator role beyond readonly status.

**Recommendation**: Keep it simple — `is_readonly_mode` handles tournament status gating. Viewers are excluded by `show_lifecycle_controls` from reaching operator-only cards via UI navigation. If a viewer navigates directly, they see the readonly view (which is the same as any user viewing an advanced tournament).

**Completion criteria**:
- Card 0: create/edit buttons hidden for viewers
- Card 1: lifecycle buttons hidden for viewers (existing)
- Viewers see readonly view throughout
- No auth check duplication — reuse existing patterns

**Estimate**: +10 lines

---

## Phase 5: Tests

**Prereq**: Phase 4
**Files**: `tests/test_tournament_step_navigation.py`
**Goal**: Test step machine, navigation, flows, and readonly mode.

---

### T-22: Test step machine navigation (go_next, go_previous, guards)

**File**: `tests/test_tournament_step_navigation.py` (new)

**What**: Tests for core step machine behavior:

```python
# ── Step machine core ──
class TestStepMachineCore:
    def test_initial_step_is_zero(self, ...): ...
    def test_go_next_increments_step(self, ...): ...
    def test_go_previous_decrements_step(self, ...): ...
    def test_go_next_blocked_at_max_step(self, ...): ...
    def test_go_previous_blocked_at_step_zero(self, ...): ...
    def test_go_to_step_jumps_directly(self, ...): ...
    def test_go_next_updates_max_reached_step(self, ...): ...

# ── Computed guards ──
class TestStepGuards:
    def test_can_go_next_false_when_no_tournament_at_step_0(self, ...): ...
    def test_can_go_next_true_when_tournament_selected(self, ...): ...
    def test_can_go_next_false_at_max_step(self, ...): ...
    def test_can_go_next_false_for_archivado_status(self, ...): ...
    def test_can_go_previous_false_at_step_0(self, ...): ...
    def test_can_go_previous_true_at_step_1(self, ...): ...

# ── Transition validation ──
class TestTransitionValidation:
    def test_adjacent_transition_allowed(self, ...): ...
    def test_create_shortcut_0_to_2(self, ...): ...
    def test_edit_shortcut_0_to_6(self, ...): ...
    def test_invalid_transition_returns_false(self, ...): ...
    def test_guard_blocks_step_without_tournament(self, ...): ...
```

**Test patterns** (follow existing tests):
- Use `TournamentState()` instantiation
- Set vars directly, call handlers via `.fn()`
- Use `monkeypatch` for state dependencies
- Mark async tests with `@pytest.mark.anyio`
- Use `db_session` fixture from conftest

**Completion criteria**:
- All step machine tests pass
- Edge cases covered (boundary values, invalid transitions)
- Tests follow existing test_file patterns

**Estimate**: +80 lines

---

### T-23: Test create flow

**File**: `tests/test_tournament_step_navigation.py`

**What**: Tests for the complete create tournament flow:

```python
class TestCreateFlow:
    def test_start_create_flow_sets_mode_and_jumps(self, ...): ...
    def test_create_flow_form_advances_to_categories(self, ...): ...
    def test_create_flow_full_path(self, ...): ...
    def test_create_flow_save_failure_stays_on_form(self, ...): ...
    def test_create_flow_complete_starts_competition(self, ...): ...
    def test_create_flow_cancel_returns_to_selector(self, ...): ...
```

**Completion criteria**:
- Full happy path tested
- Failure modes tested
- Auto-advance behavior verified
- Status transition in complete_create_flow verified

**Estimate**: +60 lines

---

### T-24: Test edit flow

**File**: `tests/test_tournament_step_navigation.py`

**What**: Tests for edit flow:

```python
class TestEditFlow:
    def test_start_edit_flow_planificado_shows_choice(self, ...): ...
    def test_start_edit_flow_inscripcion_shows_categories(self, ...): ...
    def test_edit_flow_edit_data_saves_and_returns(self, ...): ...
    def test_edit_flow_edit_categories_returns_to_status(self, ...): ...
    def test_edit_flow_cancel_from_form_returns_to_status(self, ...): ...
    def test_edit_flow_tournament_changed_status(self, ...): ...
```

**Completion criteria**:
- All edit flow paths tested
- Edge case: tournament status changed mid-flow
- Cancel returns to correct card

**Estimate**: +60 lines

---

### T-25: Test readonly mode

**File**: `tests/test_tournament_step_navigation.py`

**What**: Tests for readonly mode behavior:

```python
class TestReadonlyMode:
    def test_is_readonly_mode_planificado_false(self, ...): ...
    def test_is_readonly_mode_inscripcion_true(self, ...): ...
    def test_is_readonly_mode_en_curso_true(self, ...): ...
    def test_is_readonly_mode_archivado_true(self, ...): ...
    def test_is_readonly_mode_no_tournament_false(self, ...): ...
```

**Completion criteria**:
- All status values return correct readonly flag
- No tournament case returns False

**Estimate**: +50 lines

---

## Phase 6: Polish

**Prereq**: Phase 4
**Goal**: Animations, responsiveness, accessibility.

---

### T-26: Add slide transitions between cards

**File**: `kakumi_app/pages/tournament.py`

**What**: Add CSS transition/animation to `_active_card()` container:

```python
def _active_card() -> rx.Component:
    return rx.box(
        rx.match(
            TournamentState.step_index,
            # ... all card cases
        ),
        style={
            "transition": "opacity 0.2s ease, transform 0.2s ease",
        },
        # Use key to trigger React re-mount animation
        key=TournamentState.step_index,
        width="100%",
    )
```

Add keyframe CSS for slide animation (inline or via style prop).

**Simplification**: No complex animation in first iteration. Just add `transition` and `key` prop. Add keyframes in a follow-up if desired.

**Completion criteria**:
- Card container has transition CSS property
- `key` prop bound to step_index for re-mount on step change
- No visual regression on step change

**Estimate**: +5 lines

---

### T-27: Responsive adjustments

**File**: `kakumi_app/pages/tournament.py`

**What**:
- Navigation bar buttons stack vertically on mobile (`direction={"base": "column", "md": "row"}`)
- Step indicator: hide labels on mobile (only show dots)
- Card padding adjusts for small screens
- Action buttons in cards use full width on mobile

```python
# Mobile nav bar
rx.hstack(
    rx.button(..., width={"base": "100%", "md": "auto"}),
    rx.button(..., width={"base": "100%", "md": "auto"}),
    direction={"base": "column", "md": "row"},
    width="100%",
)
```

**Completion criteria**:
- Tournament page renders correctly on mobile (viewport < 768px)
- Navigation buttons full-width on mobile
- Card does not overflow horizontally
- Step indicator dots visible, labels hidden on mobile

**Estimate**: +10 lines

---

### T-28: WCAG compliance (ARIA roles, focus management, keyboard nav)

**File**: `kakumi_app/pages/tournament.py`

**What**:
- Add `role="region"` with `aria-label` to each card
- Add `aria-current="step"` to active step dot
- Use `aria-disabled` instead of `disabled` on buttons that should stay focusable
- Add `aria-live="polite"` to card container for screen reader announcements
- First interactive element in card gets focus when step changes

```python
# Example: aria attributes on card
rx.box(
    role="region",
    aria_label=f"Paso {TournamentState.step_index}: {TournamentState._step_labels[TournamentState.step_index] if TournamentState.step_index < len(TournamentState._step_labels) else ''}",
    aria_live="polite",
    ...
)
```

**Note**: Full focus management in Reflex is limited. Implement basic ARIA attributes; advanced focus management (programmatic focus via refs) may need investigation.

**Completion criteria**:
- All cards have role="region" with descriptive aria-label
- Step indicator dots have aria-current when active
- Navigation buttons use aria-disabled pattern where feasible
- No regression in keyboard navigation

**Estimate**: +20 lines

---

## Dependency Graph

```
T-01 (constants + vars)
  └── T-02 (go_next/go_previous)
  │     └── T-03 (computed guards — needs can_go_next)
  │           └── T-04 (transition validation — needs step_index)
  │                 └── T-05 (flow handlers — needs all above)
  │                       └── T-06 (bridge handler — needs T-05)
  │                             └── T-07 (load_workspace reset — needs T-01)
  │                                   │
  │                                   ▼
  │                            Phase 2: T-08 (step_indicator — needs _step_labels)
  │                            Phase 2: T-09 (navigation_bar — needs can_go_*)
  │                            Phase 2: T-10 (active_card + layout)
  │                                   │
  │                                   ▼
  │                            Phase 3: T-11..T-17 (card components)
  │                                   │
  │                                   ▼
  │                            Phase 4: T-18..T-21 (flow integration)
  │                                   │
  │                                   ├── Phase 5: T-22..T-25 (tests)
  │                                   └── Phase 6: T-26..T-28 (polish)
  │
  └── All phases depend on T-01 through T-07 indirectly
```

**Key dependency rule**: A phase requires ALL previous phases (sequential).

---

## Risk Register

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| TournamentCrudState bridge coupling | Form save success not propagating to step advance | High | T-06 bridge handler. Alternative: rx.cond observer pattern. |
| Reactive loop on step_index change | Infinite re-render | Medium | Guard clauses in go_next/go_previous. No on_mount handlers modify step_index. |
| Substates lack context on tournament switch | Wrong categories/tatamis shown | Low | set_current_tournament already syncs both substates. Ensure it's called before step≥3. |
| _tournament_form() uses registries-only imports | Import error when used in tournament page | Medium | Verify _tournament_form imports are self-contained. Registries uses same state imports. |
| Cards 0 and 3 both bind TournamentState.tournaments | Double loading on mount | Low | load_workspace runs once on page load. Card reads already-loaded data. |
