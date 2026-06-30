# Design: Tournament Frontend Redesign — Sequential Card Flow

## Overview

Replace 2-column 5-card grid with 7-step sequential card wizard. TournamentState gains step machine. Existing substates (TournamentCategoryState, TournamentTatamiState) unchanged. No backend/model/service changes.

All code changes in `kakumi_app/pages/tournament.py` + `kakumi_app/states/tournament_state.py`.

---

## 1. Component Architecture

### Tree

```
tournament_page()
└── registry_page_shell(body)
    └── rx.vstack
        ├── _workspace_header()
        ├── _step_indicator()            ← progress dots (optional)
        ├── rx.match(TournamentState.step_index)
        │   ├── 0 → TournamentSelectionCard
        │   ├── 1 → TournamentStatusCard
        │   ├── 2 → TournamentFormCard
        │   ├── 3 → TournamentCategoriesCard
        │   ├── 4 → TournamentTatamisCard
        │   ├── 5 → RegistrationControlCard
        │   └── 6 → EditChoiceCard
        └── _navigation_bar()            ← ← Anterior  [Siguiente →]
```

### 1.1 TournamentSelectionCard (step=0)

**Props**: none (reads TournamentState directly)

**State reads**:
- `tournaments: list[dict]` — all tournaments
- `current_tournament: Optional[dict]` — selected
- `has_selected_tournament: bool` (rx.var)

**Handlers called**:
- `set_current_tournament(id)` — on button click
- `start_create_flow()` — click "Crear torneo"
- `start_edit_flow()` — click "Editar torneo"

**Template**:
```python
def _selector_card() -> rx.Component:
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("Torneos disponibles", size="5"),
            _tournament_list(state),
            rx.hstack(
                rx.button("Crear torneo", on_click=state.start_create_flow),
                rx.button("Editar torneo", on_click=state.start_edit_flow),
                spacing="2",
            ),
            spacing="3",
        ),
        width="100%",
    )
```

**States**:
| State | Render |
|-------|--------|
| Loading (torneos == []) | Empty state: "No hay torneos cargados todavía." |
| Tournaments loaded | Lista de botones con selección highlight |
| Tournament selected | Botón solid (current) + outline (rest) |
| Error | rx.callout con transition_error |

### 1.2 TournamentStatusCard (step=1)

**State reads**:
- `current_tournament` — name, status, venue, tatami_count
- `show_lifecycle_controls`, `show_open_registrations_action` etc.
- `has_selected_tournament`, `transition_error`, `validation_warnings`
- `qr_data_url`, `qr_code_text`, `qr_expires_at`

**Handlers called**:
- Lifecycle: `open_registrations`, `close_registrations`, `start_competition`, `finish_competition`, `archive_tournament`, `reopen_registrations`, `cancel_tournament`
- QR: `generate_qr`, `regenerate_qr`

**Template** (reuses `_selection_summary()` from current code + lifecycle buttons + QR):

```python
def _status_card() -> rx.Component:
    state = TournamentState
    return rx.card(
        rx.vstack(
            _selection_summary(),            # reuses existing
            rx.cond(state.show_lifecycle_controls, _lifecycle_buttons(), rx.fragment()),
            rx.cond(state.transition_error, rx.callout(...), rx.fragment()),
            rx.cond(state.validation_warnings, rx.callout(...), rx.fragment()),
            _qr_section(),                    # inline QR (from existing _qr_card())
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

**States**:
| Condition | Behavior |
|-----------|----------|
| No tournament selected | Show "Selecciona un torneo" |
| Tournament loaded, operator role | Show summary + lifecycle buttons |
| Tournament loaded, viewer role | Show summary only (no lifecycle) |
| Transition in progress | Buttons disabled (is_transitioning) |
| Transition error | Show error callout |

### 1.3 TournamentFormCard (step=2)

**State reads (TournamentCrudState)**:
- `name`, `venue`, `start_date`, `end_date`, `tatami_count`, `is_editing`, `error_message`, `show_form`
- Calendar vars: `show_calendar`, `calendar_day_cells`, etc.

**Handlers called (TournamentCrudState)**:
- `set_name`, `set_venue`, `set_start_date`, `set_end_date`, `set_tatami_count`
- `save_tournament`, `cancel_form`
- Calendar handlers: `toggle_calendar`, `calendar_prev_month`, `calendar_next_month`, `select_calendar_day`

**Bridge vars (TournamentState)**:
```python
_form_saved_tournament_id: int = 0   # set by bridge after save success
create_mode: bool = False
```

**How bridge works**:
- TournamentFormCard wraps `_tournament_form()` from registries.py
- TournamentState exposes `handle_form_saved()` which TournamentCrudState.save_tournament calls on success
- Or: TournamentFormCard uses `rx.cond(TournamentCrudState.show_form == False && TournamentCrudState.error_message == "", TournamentState.advance_after_form_saved)`
- **Recommendation**: After `TournamentCrudState.save_tournament()` success, set a shared `_last_saved_tournament_id` on TournamentState, then `go_next()` in create mode or `go_to_step(1)` in edit mode

**Template**:
```python
def _form_card() -> rx.Component:
    # Reuses existing _tournament_form() from registries.py
    # Needs state bridge for flow control
    return rx.card(
        rx.vstack(
            rx.heading(rx.cond(TournamentState.create_mode, "Nuevo Torneo", "Editar Torneo"), size="5"),
            _tournament_form(),            # from registries.py, binds TournamentCrudState
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

**States**:
| Condition | Behavior |
|-----------|----------|
| create_mode=True | Heading "Nuevo Torneo", save creates new tournament |
| is_editing=True | Heading "Editar Torneo", save updates existing |
| Validation error | error_message callout shown |
| Save success (create) | Auto-advance to step 3 (Categories) |
| Save success (edit) | Auto-return to step 1 (Status) |
| Save failure | Stay on step, show toast.error |

### 1.4 TournamentCategoriesCard (step=3)

**Reuses existing `_categories_card()` from current code**. Minimal change: wrap in container that passes `TournamentCategoryState.readonly_mode`.

**Template**:
```python
def _categories_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            _existing_categories_content(),   # paste current _categories_card() body
            spacing="3",
            width="100%",
        ),
        width="100%",
    )
```

**States**: unchanged from current.

### 1.5 TournamentTatamisCard (step=4)

**Reuses existing `_tatami_card()` from current code**. Same pattern as CategoriesCard.

### 1.6 RegistrationControlCard (step=5)

**New component**. Shown only during create flow.

**State reads**:
- `current_tournament` — verify tournament exists and is in BORRADOR status
- `created_tournament_id` — tournament created earlier in form step

**Handlers called**:
- `complete_create_flow()` — calls `_execute_transition(EN_CURSO)`, then `go_to_step(1)`

**Template**:
```python
def _registration_control_card() -> rx.Component:
    return rx.card(
        rx.vstack(
            rx.heading("Confirmar inicio", size="5"),
            rx.text("El torneo se creó correctamente. Revisá categorías y tatamis."),
            rx.text("Al clickear 'Comenzar torneo' se iniciará la competencia."),
            rx.button(
                "Comenzar torneo",
                on_click=TournamentState.complete_create_flow,
                color_scheme="green",
            ),
            spacing="3",
        ),
        width="100%",
    )
```

### 1.7 EditChoiceCard (step=6)

**New component**. Reached from selector via `start_edit_flow()`.

**State reads**:
- `current_tournament` — status check for permissions
- `is_readonly_mode` (rx.var)

**Handlers called**:
- `go_to_step(3)` — "Editar categorías"
- `go_to_step(2)` — "Editar datos del torneo" (only for BORRADOR)
- `go_previous()` — back to selector

**Template**:
```python
def _edit_choice_card() -> rx.Component:
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("¿Qué querés editar?", size="5"),
            rx.text(f"Torneo: {state.current_tournament['name']}"),
            rx.button("Editar categorías", on_click=state.go_to_step(3)),
            rx.cond(
                state._current_status() == TournamentStatus.PLANIFICADO,
                rx.button("Editar datos del torneo", on_click=state.go_to_step(2)),
            ),
            rx.cond(
                state.is_readonly_mode,
                rx.text("Solo visualización disponible para torneos avanzados."),
            ),
            spacing="3",
        ),
        width="100%",
    )
```

### _step_indicator()

Optional breadcrumb/progress-dots component:

```python
def _step_indicator() -> rx.Component:
    steps = ["Selección", "Estado", "Formulario", "Categorías", "Tatamis", "Confirmar", "Editar"]
    return rx.hstack(
        rx.foreach(
            steps,                              # simplified: actual impl needs index tracking
            lambda step, i: rx.cond(
                TournamentState.step_index == i,
                rx.badge(step, color_scheme="red"),
                rx.text(step, color_scheme="gray"),
            ),
        ),
        spacing="2",
    )
```

Actually, step_indicator labels should be computed dynamically based on `create_mode` / `edit_mode`. Simplified approach:

```python
def _step_indicator() -> rx.Component:
    return rx.flex(
        rx.foreach(
            TournamentState._step_labels,  # list[str] computed from mode
            lambda label, idx: rx.badge(
                label,
                variant=rx.cond(TournamentState.step_index == idx, "solid", "soft"),
                color_scheme=rx.cond(TournamentState.step_index == idx, "red", "gray"),
            ),
        ),
        spacing="3",
        justify="center",
        width="100%",
        wrap="wrap",
    )
```

### _navigation_bar()

```python
def _navigation_bar() -> rx.Component:
    state = TournamentState
    return rx.hstack(
        rx.button(
            "← Anterior",
            on_click=state.go_previous,
            disabled=~state.can_go_previous,
            variant="outline",
        ),
        rx.button(
            "Siguiente →",
            on_click=state.go_next,
            disabled=~state.can_go_next,
            variant="solid",
            color_scheme="red",
        ),
        justify="between",
        width="100%",
    )
```

---

## 2. Step Machine Design

### Core vars

```python
# TournamentState additions
step_index: int = 0
step_count: int = 7                  # total card slots
create_mode: bool = False            # True during create flow
edit_mode: bool = False               # True during edit flow
_form_saved_tournament_id: int = 0   # bridge from TournamentCrudState
```

### Step mapping (constants)

```python
# Step indices — used in rx.match() and transition validation
SELECTION_STEP = 0
STATUS_STEP = 1
FORM_STEP = 2
CATEGORIES_STEP = 3
TATAMIS_STEP = 4
CONFIRM_STEP = 5   # RegistrationControlCard
EDIT_CHOICE_STEP = 6
```

### Navigation handlers

```python
@rx.event
def go_next(self) -> None:
    """Advance one step. Validates preconditions."""
    if not self._validate_step_transition(self.step_index, self.step_index + 1):
        return
    self.step_index += 1

@rx.event
def go_previous(self) -> None:
    """Go back one step."""
    if not self._validate_step_transition(self.step_index, self.step_index - 1):
        return
    self.step_index -= 1

@rx.event
def go_to_step(self, target_step: int) -> None:
    """Non-sequential jump (create/edit shortcuts). Validated via transition map."""
    if not self._validate_step_transition(self.step_index, target_step):
        return
    self.step_index = target_step
```

### Computed guards

```python
@rx.var
def can_go_next(self) -> bool:
    """Next enabled when step_index < step_count - 1 AND preconditions met."""
    if self.step_index >= self.step_count - 1:
        return False
    return self._validate_step_transition(self.step_index, self.step_index + 1)

@rx.var
def can_go_previous(self) -> bool:
    """Previous enabled when step_index > 0."""
    return self.step_index > 0

@rx.var
def is_readonly_mode(self) -> bool:
    """Cards render readonly when tournament is in advanced state."""
    if not self.current_tournament:
        return False
    status = self.current_tournament.get("status", "")
    advanced = {"INSCRIPCION", "VERIFICACION", "EN_CURSO", "FINALIZADO", "ARCHIVADO"}
    return status in advanced
```

### Transition map

```python
def _validate_step_transition(self, from_step: int, to_step: int) -> bool:
    """Validates step transition. Returns True if allowed.

    Transition Map:
        Normal sequential: step_n ↔ step_n±1 (always allowed)
        Create shortcut:   0 → 2                  (start_create_flow)
        Create flow:       2 → 3 → 4 → 5 → 1      (after save, post-confirm)
        Edit shortcut:     0 → 6                  (start_edit_flow)
        Edit → form:       6 → 2                  (edit tournament data)
        Edit → categories: 6 → 3                  (edit categories)
        Form saved (edit): 2 → 1                  (return to status)
        Categories edited: 3 → 1                  (return to status)
        Cancel form:       2 → 1 | 2 → 0          (cancel returns)
        Cancel edit:       6 → 1 | 6 → 0          (cancel returns)
        Confirm complete:  5 → 1                  (create flow done)
    """
    # Guard: tournament selected for step >= 1
    if to_step >= 1 and not self.has_selected_tournament and to_step not in (0, 6):
        return False

    # Simple +/- 1: always allowed within [0, step_count-1]
    if abs(to_step - from_step) == 1:
        return 0 <= to_step < self.step_count

    # Special transitions
    special_transitions = {
        (0, 2): self.create_mode,           # create flow entry
        (0, 6): self.edit_mode,              # edit flow entry
        (2, 0): not self.create_mode,        # form cancel, normal back
        (2, 1): not self.create_mode,        # form saved (edit) → status
        (3, 1): self.edit_mode,              # categories done → status
        (3, 2): False,                       # no backward from create categories to form
        (5, 1): True,                        # confirm done → status
        (2, 3): self.create_mode,            # form saved → categories
        (3, 4): self.create_mode,            # categories → tatamis
        (4, 5): self.create_mode,            # tatamis → confirm
    }

    return special_transitions.get((from_step, to_step), False)
```

### Reset on load

```python
# Modified load_workspace
@rx.event
async def load_workspace(self) -> None:
    self.step_index = 0
    self.create_mode = False
    self.edit_mode = False
    self._form_saved_tournament_id = 0
    # ... rest of existing load_workspace logic

# Also add to set_current_tournament when tournament changes
@rx.event
async def set_current_tournament(self, tournament_id: int) -> None:
    if tournament_id != self._get_tournament_id():
        self.step_index = 1   # auto-advance to status card on tournament select
    # ... rest of existing set_current_tournament logic
```

Wait — constraint says "Siempre Card 1 al entrar a /tournament". So `step_index` resets to 0 on `load_workspace`. But when user clicks a tournament on Card 0, the "Siguiente" button gets enabled. The user then clicks "Siguiente" to go to Card 1. So `set_current_tournament` should NOT auto-advance — it just enables `can_go_next`.

Let me correct this:

```python
@rx.event
async def load_workspace(self) -> None:
    """Modified on_load: reset step machine, then load workspace."""
    self.step_index = 0
    self.create_mode = False
    self.edit_mode = False
    self._form_saved_tournament_id = 0
    # ... existing load_workspace body
```

---

## 3. State Changes

### TournamentState — new vars

| Var | Type | Default | Description |
|-----|------|---------|-------------|
| `step_index` | `int` | `0` | Current visible card index |
| `step_count` | `int` | `7` | Total card slots |
| `create_mode` | `bool` | `False` | True during create flow |
| `edit_mode` | `bool` | `False` | True during edit flow |
| `_form_saved_tournament_id` | `int` | `0` | Bridge from TournamentCrudState after save success |

### TournamentState — new rx.var

| Var | Return | Logic |
|-----|--------|-------|
| `can_go_next` | `bool` | `self.step_index < self.step_count - 1 AND _validate_step_transition(step_index, step_index + 1)` |
| `can_go_previous` | `bool` | `self.step_index > 0` |
| `is_readonly_mode` | `bool` | tournament status in {INSCRIPCION, VERIFICACION, EN_CURSO, FINALIZADO, ARCHIVADO} |
| `_step_labels` | `list[str]` | Dynamic labels based on create_mode/edit_mode |

### TournamentState — new handlers

| Handler | Type | Logic |
|---------|------|-------|
| `go_next()` | `@rx.event` | Validate + increment step_index |
| `go_previous()` | `@rx.event` | Decrement step_index |
| `go_to_step(step: int)` | `@rx.event` | Non-sequential validated jump |
| `start_create_flow()` | `@rx.event` | Set `create_mode=True`, `go_to_step(2)` |
| `start_edit_flow()` | `@rx.event` | Set `edit_mode=True`, `go_to_step(6)` or `go_to_step(3)` depending on status |
| `complete_create_flow()` | `@rx.event` | Call `_execute_transition(EN_CURSO)`, then `go_to_step(1)` |
| `advance_after_form_saved()` | `@rx.event` | Bridge from TournamentCrudState: if create_mode → `go_to_step(3)`, else `go_to_step(1)` |

### Unchanged states

- **TournamentCategoryState** — no structural changes. `_current_tournament_status` already guards CRUD. `set_form_values` already rejects if status not in [PLANIFICADO, INSCRIPCION, VERIFICACION].
- **TournamentTatamiState** — no changes. Same guard pattern.
- **TournamentCrudState** — no changes. Used via bridge pattern.

### Substates readonly mode

Neither substate needs new vars. The existing `_current_tournament_status` guard in both substates already prevents editing when tournament is in advanced state. The "readonly" UI behavior (disabled fields) is handled by `rx.cond(TournamentState.is_readonly_mode, ...)` in the rendering, which disables form buttons without touching state.

---

## 4. Data Flow Between Steps

### 4.1 Selection → Status

```
User clicks tournament in Card 0
→ TournamentState.set_current_tournament(id)
  → sync_auth_context()                // lazy — already done in load_workspace
  → refresh_current_tournament_snapshot(id)
  → TournamentCategoryState.set_tournament_context(id)
  → TournamentTatamiState.set_tournament_context(id)
  → refresh_current_tournament_snapshot(id)
→ can_go_next becomes True (tournament selected)
→ User clicks "Siguiente"
→ go_next() → step_index = 1
→ Card 1 renders with current_tournament data
```

### 4.2 Crear flow

```
User clicks "Crear torneo" in Card 0
→ start_create_flow()
  → create_mode = True
  → go_to_step(2)
→ Card 2 renders with TournamentCrudState form

User fills form, clicks "Guardar"
→ TournamentCrudState.save_tournament()
  → on success: TournamentState._form_saved_tournament_id = new_tournament_id
  → TournamentState.advance_after_form_saved()
    → go_to_step(3)     // Categories

User adds categories
→ TournamentCategoryState.save_category()   // existing, no changes
→ User clicks "Siguiente"
→ go_next() → step_index = 4   // Tatamis

User configures tatamis
→ TournamentTatamiState.save_tatami()   // existing, no changes
→ User clicks "Siguiente"
→ go_next() → step_index = 5   // Confirm

User clicks "Comenzar torneo"
→ complete_create_flow()
  → _execute_transition(EN_CURSO)
  → go_to_step(1)   // Status card with updated status
```

### 4.3 Edit flow (BORRADOR)

```
User selects tournament, clicks "Editar torneo"
→ start_edit_flow()
  → edit_mode = True
  → go_to_step(6)   // EditChoiceCard

User clicks "Editar categorías"
→ go_to_step(3)   // Categories, edit_mode=True
  → User edits categories via existing TournamentCategoryState handlers
  → User clicks "Siguiente"
  → go_to_step(1)   // Status (valid transition: 3→1 when edit_mode)

OR

User clicks "Editar datos del torneo"
→ go_to_step(2)   // Form, edit_mode=False (is_editing on TournamentCrudState)
  → TournamentCrudState.set_form_values(tournament) prefills
  → User edits, saves
  → TournamentState.advance_after_form_saved()
    → go_to_step(1)   // Status
```

### 4.4 View flow (EN_CURSO+)

```
0 → 1 (can see status, lifecycle controls disabled for non-operators)
  CategoriesCard and TatamisCard are reachable via sequential navigation
  but render in readonly mode (form buttons hidden, table only)
```

### Flow diagram

```
                    ┌─────────────────────────────────────┐
                    │           ┌─── 2 (Form)            │
                    │           │   │ save success        │
                    │           │   ▼                    │
                    │           └─── 3 (Categories) ──┐  │
                    │           └─── 4 (Tatamis) ──┐  │  │
                    │           └─── 5 (Confirm) ──┐│  │  │
                    │                              ▼▼  ▼  │
                    │  6 (EditChoice) ─→ 2 or 3 ──→ 1    │
                    │                            (Status) │
                    │  ┌───────────────────────────▲      │
                    ▼  ▼                                  │
0 (Selection) ────→ 1 (Status) ──→ 3 ──→ 4 ──→ ... ─────┘
     ↑                                        │
     └────────────────────────────────────────┘
           (back always returns to 0)

Key:
──→ = sequential (go_next/go_previous)
──→ = non-sequential jump (go_to_step)
```

---

## 5. Routing

### No changes

- Route `/tournament` unchanged
- No sub-routes added
- `on_load` handler modified: `TournamentState.load_workspace()` adds `step_index = 0` reset at start

### Modified `on_load` behavior

```python
# In kakumi_app.py — existing add_page
app.add_page(
    tournament,
    route="/tournament",
    on_load=TournamentState.load_workspace,  # modified to reset step_index
)
```

The `load_workspace` handler adds these lines at top:
```python
self.step_index = 0
self.create_mode = False
self.edit_mode = False
self._form_saved_tournament_id = 0
```

---

## 6. UI/UX Design Decisions

### 6.1 Step transitions

**Decision**: Use Reflex `rx.motion.div` wrapper or simple CSS transitions via `animation` prop on the active card container.

```python
def _active_card() -> rx.Component:
    return rx.box(
        rx.match(
            TournamentState.step_index,
            0, _selector_card(),
            1, _status_card(),
            2, _form_card(),
            3, _categories_card(),
            4, _tatamis_card(),
            5, _registration_control_card(),
            6, _edit_choice_card(),
            _selector_card(),
        ),
        transition="opacity 0.2s ease, transform 0.2s ease",
        style={
            "animation": rx.cond(
                TournamentState.step_index > 0,
                "slideInRight 0.25s ease-out",
                "slideInLeft 0.25s ease-out",
            ),
        },
        width="100%",
    )
```

**Animation**: `fade + slide` (slide left on forward, right on back). Keyframes defined in CSS module or inline via Reflex style. This avoids performance issues of complex animations in Reflex.

**Alternative**: Start simple — no animation on first iteration. Add fade transition later as optimization.

### 6.2 Navigation bar behavior

- "← Anterior" hidden on step 0 (or disabled)
- "Siguiente →" enabled only when `can_go_next` = True
- Button labels change per step context:
  - Step 0: "Siguiente →" (when tournament selected)
  - Step 5 (create flow): "Comenzar torneo" replaces next (calls `complete_create_flow`)
  - Step 1: "Siguiente →" if more steps available
- "Siguiente" on step 5 triggers `complete_create_flow` not `go_next`
- Both buttons rendered always, disabled via `disabled=~state.can_go_next`

### 6.3 Breadcrumb / Step indicator

**Decision**: Include minimal step indicator as 7 dots (●) with active step highlighted. Hidden on step 0. Show only on steps 1-6.

```python
def _step_indicator() -> rx.Component:
    return rx.cond(
        TournamentState.step_index > 0,
        rx.hstack(
            rx.foreach(
                [True, False, False, False, False, False, False],  # simplified
                lambda is_visited, idx: rx.badge(
                    "●",
                    color_scheme=rx.cond(
                        TournamentState.step_index >= idx, "red", "gray"
                    ),
                ),
            ),
            justify="center",
            spacing="1",
        ),
    )
```

**Rationale**: Dots show progression without committing to step labels (which change between create/edit modes). Labels would add complexity.

### 6.4 Responsive

- Single card is naturally mobile-friendly
- `max_width="800px"` on container keeps cards readable
- Navigation buttons stack vertically on narrow screens
- No layout changes needed inside cards — existing content adapts

### 6.5 Card container consistency

All cards share:
- `rx.card(width="100%")`
- Internal `rx.vstack(spacing="3", align="start")` layout
- Heading with `size="5"`
- Consistent padding via card defaults

### 6.6 i18n

Existing pattern: Spanish hardcoded strings. Design preserves this. Future i18n layer can wrap strings without structural changes.

### 6.7 QR card placement

**Decision**: Integrate QR generation into StatusCard (step 1) as collapsible section. This eliminates a dedicated step and keeps QR accessible from the tournament overview card.

```python
def _qr_section() -> rx.Component:
    state = TournamentState
    return rx.vstack(
        rx.cond(
            state.qr_data_url != "",
            rx.image(...),
            rx.button("Generar QR", on_click=state.generate_qr, ...),
        ),
        spacing="2",
        width="100%",
    )
```

---

## 7. Permissions Matrix: Visibility by Role × Step

| Step | Card | Operator | Viewer | No auth |
|------|------|----------|--------|---------|
| **0** | TournamentSelectionCard | Full: select, create, edit, navigate next | Readonly list + select. No create/edit buttons. | Redirect to login |
| **1** | TournamentStatusCard | Full: lifecycle transitions, QR, bracket link, navigation | View tournament summary. No lifecycle buttons. QR visible if generated. Bracket link active. | Redirect to login |
| **2** | TournamentFormCard | Full: create/edit tournament. Save + cancel. | Not shown. | Redirect to login |
| **3** | TournamentCategoriesCard | Full CRUD. Fields disabled when tournament in VERIFICACION+/EN_CURSO+. | View-only: table rendered, form buttons hidden, fields disabled. | Redirect to login |
| **4** | TournamentTatamisCard | Full CRUD. Disabled when tournament in EN_CURSO+. | View-only: table only, no add/edit/delete buttons. | Redirect to login |
| **5** | RegistrationControlCard | Full: confirm and start competition. Only EN_CURSO+ reachable. | Not shown. | Redirect to login |
| **6** | EditChoiceCard | Full: choose edit path. Action buttons conditional on status. | Not shown (redirect to Card 1 if navigated). | Redirect to login |

**Implementation note**: The current `sync_auth_context()` + `show_lifecycle_controls` pattern already handles Operator vs Viewer differentiation. The card rendering adds:

- `rx.cond(state.show_lifecycle_controls, ...)` for operator-specific buttons
- Viewers don't get create/edit buttons on Card 0
- No-auth redirect already handled by `AuthState.check_auth_redirect` via existing middleware pattern

---

## 8. Technical Risks

### R1: TournamentCrudState bridge coupling

**Risk**: `_tournament_form()` from registries.py uses `TournamentCrudState`. The step machine lives in `TournamentState`. Two separate state classes need coordination after save.

**Severity**: High. Without bridging, save success cannot trigger step advance.

**Mitigation**: 
- TournamentState observes `_form_saved_tournament_id` var. TournamentCrudState sets TournamentState's var after successful save.
- At render time, use `rx.cond(TournamentCrudState.show_form == False && TournamentState.create_mode == True, TournamentState.advance_after_form_saved())` as event chain.
- **Alternative**: Add a thin wrapper `_create_tournament_handler` in TournamentState that calls `TournamentCrudState.save_tournament()` then handles step advance.

**Recommendation**: Option 2 (bridge via `on_submit` wrapper):

```python
@rx.event
async def handle_form_submit(self) -> None:
    """Bridge: delegates to TournamentCrudState.save_tournament(), advances step on success."""
    crud = await self.get_state(TournamentCrudState)
    result = await crud.save_tournament()

    if crud.show_form == False and crud.error_message == "":
        self._form_saved_tournament_id = crud.current_tournament.get("id", 0) if crud.current_tournament else 0
        await self.advance_after_form_saved()
```

### R2: Reactive loop when go_next modifies step_index

**Risk**: Changing `step_index` triggers re-render. If the newly rendered card's `on_mount` or `rx.var` evaluation calls a handler that changes `step_index` again, infinite loop.

**Severity**: Medium.

**Mitigation**:
- No card uses `on_mount` that modifies `step_index`
- `rx.var` reads for `can_go_next`/`can_go_previous` are pure — no side effects
- Guard clause in `go_next`/`go_previous`: if `from_step == to_step`, skip

### R3: Substates lack context when tournament switches

**Risk**: User selects Tournament A → view Card 3 (categories loaded for A). User goes back → selects Tournament B → goes to Card 3. TournamentCategoryState still has A's categories until `set_tournament_context(B.id)` completes.

**Severity**: Low. Current code already handles this: `set_current_tournament(id)` calls both substates.

**Mitigation**: Ensure `set_current_tournament` always fires before any step navigation that depends on context. Enforce via `_validate_step_transition`: step ≥ 3 requires `has_selected_tournament`.

### R4: Race condition — save_tournament succeeds but step doesn't advance

**Risk**: Async timing between `TournamentCrudState.save_tournament()` completing and `TournamentState` detecting success.

**Severity**: Medium. User would be stuck on form card with no feedback.

**Mitigation**:
- `handle_form_submit` (bridge wrapper) is sequential: `await crud.save_tournament()` → check result → advance step
- If save fails, `show_form` stays `True` and `error_message` is set — step stays put
- Toast success/error already handled by `save_tournament`

### R5: Edit flow step validation complexity

**Risk**: Transition map for edit flow (6→2, 6→3, 2→1, 3→1, 2→0) creates many edge cases. `go_previous()` from step 2 (form) during edit mode should go to 1 (status), not 0 (selector).

**Severity**: Medium.

**Mitigation**:
- `_validate_step_transition` explicitly enumerates all non-sequential transitions
- Mode flags (`create_mode`, `edit_mode`) gate special transitions
- Test each flow path exhaustively

### R6: Animation flash on step change

**Risk**: `rx.match()` replaces entire card DOM. Without transition, step change is abrupt.

**Severity**: Low.

**Mitigation**: CSS transition on card container. `key` prop on outer rx.box keyed to `step_index` so React handles mount/unmount smoothly.

---

## Affected Files

| Action | File | Impact |
|--------|------|--------|
| **EDIT** | `kakumi_app/pages/tournament.py` | Major. Replace grid layout with sequential cards. Add 2 new card components (EditChoiceCard, RegistrationControlCard) + step_indicator + navigation_bar. Wrap existing cards (CategoriesCard, TatamisCard) unchanged. |
| **EDIT** | `kakumi_app/states/tournament_state.py` | Major. Add step machine vars + handlers. Add bridge to TournamentCrudState. Modify `load_workspace` to reset `step_index`. |
| **EDIT** | `kakumi_app/kakumi_app.py` | Minor. Update `on_load` routing if TournamentState handler signature changes (likely no change — `load_workspace` remains same public signature). |

---

*Artifact: design*
*Change: tournament-frontend-redesign*
*Branch: chore/tournament-frontend-redesign*
*Generated: 2026-06-30*
