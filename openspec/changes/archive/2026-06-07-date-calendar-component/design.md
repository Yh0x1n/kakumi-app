# SDD Design — Date Calendar Popover for Tournament Dates

**Change**: `date-calendar-component`  
**Phase**: Design (complete)  
**Date**: 2026-06-07  
**Author**: SDD design executor (subagent)

---

## 1. Component Architecture

### 1.1 Component Tree

```
_tournament_form()                         [registries.py]
├── rx.heading("Inicio (DD/MM/AAAA)")
├── date_calendar_popover(                  [date_calendar.py]
│       value=state.start_date,
│       on_change=state.set_start_date,
│       target="start",
│   )
│   ├── rx.select(trigger)                  — shows current DD/MM/YYYY value
│   │   └── on_click → state.toggle_calendar("start")
│   └── rx.cond(show_calendar AND calendar_target == "start",
│       └── rx.box(overlay, position="absolute", z_index=100)
│           ├── rx.hstack
│           │   ├── rx.button("‹") → state.calendar_prev_month()
│           │   ├── rx.text("{month_name} {year}")
│           │   └── rx.button("›") → state.calendar_next_month()
│           └── rx.grid(grid_template_columns="repeat(7, 1fr)")
│               ├── Header: Do Lu Ma Mi Ju Vi Sá
│               ├── rx.foreach(build_day_cells(...)) — day buttons
│               └── (empty cells for offset alignment)
│       )
├── rx.heading("Fin (DD/MM/AAAA)")
├── date_calendar_popover(
│       value=state.end_date,
│       on_change=state.set_end_date,
│       target="end",
│   )
│   └── (same structure as above)
├── ... (other form fields)
```

**Key principle**: A single `TournamentCrudState` owns all calendar state (`show_calendar`, `calendar_target`, `calendar_month`, `calendar_year`). Only one calendar popover is open at any time. The `target` parameter disambiguates which field the popover serves.

### 1.2 Internal State

All calendar state lives in `TournamentCrudState` to avoid creating a separate `rx.State` subclass (which would increase complexity and coupling). New state vars:

| Var | Type | Default | Purpose |
|-----|------|---------|---------|
| `show_calendar` | `bool` | `False` | Global popover visibility toggle |
| `calendar_target` | `str` | `""` | Which field this popover targets (`"start"` or `"end"`) |
| `calendar_month` | `int` | `0` | Displayed month (1–12); `0` means "uninitialized → use current month" |
| `calendar_year` | `int` | `0` | Displayed year (e.g. `2026`); `0` means "uninitialized → use current year" |

**Why one shared calendar state instead of per-field**:
- Only one popover can be open at a time (UX norm)
- Eliminates duplicated state vars for start vs end
- Calendar navigation (prev/next month) is a single event pair regardless of target
- Target-specific logic is resolved by checking `calendar_target` in the component render function

### 1.3 Component Props Contract

```python
def date_calendar_popover(
    *,
    value: rx.Var[str],
    on_change: rx.EventHandler[Callable[[str], ...]],
    target: str,
) -> rx.Component:
    """Render a calendar popover triggered by a select/button.

    Args:
        value:    Current date string in DD/MM/YYYY format (bound to state var).
        on_change: State setter for the date field (e.g. state.set_start_date).
        target:   "start" or "end" — used to match calendar_target state.

    Returns:
        A Reflex component tree (rx.select + rx.cond overlay).
    """
```

The component reads `show_calendar`, `calendar_target`, `calendar_month`, `calendar_year` from `TournamentCrudState` and calls event handlers `toggle_calendar`, `calendar_prev_month`, `calendar_next_month`, `select_calendar_day`.

### 1.4 Calendar Grid Generation

The grid day cells are built via a module-level helper:

```python
def _build_calendar_month(year: int, month: int) -> list[dict]:
    """Return list of day dicts for display.

    Each dict:
        {"day": int, "is_current_month": bool, "is_today": bool}

    Leading/trailing empty cells (days from adjacent months) are included
    so the grid aligns properly (7 columns, starting on Sunday).

    Uses `calendar.monthcalendar(year, month)` for alignment.
    """
```

The component renders:

```python
rx.foreach(
    _build_calendar_month(state.calendar_year, state.calendar_month),
    lambda day_info: rx.cond(
        day_info["is_current_month"],
        rx.button(
            day_info["day"],
            on_click=lambda: state.select_calendar_day(day_info["day"]),
            **highlighted_style if day_info["is_selected"] else default_style,
        ),
        rx.text(""),  # empty cell for alignment
    ),
)
```

**Important**: `rx.foreach` iterates over a static list, not a dynamic computed value in this version. The `_build_calendar_month` helper produces a deterministic list based on `calendar_month`/`calendar_year`. Each render recomputes the list.

**Weekday headers** (Spanish):
```python
weekdays = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]
# Rendered as rx.grid items in first row via rx.foreach
```

**Current date highlight**: Parsed from the `value` prop. If the parsed day matches a cell's day AND the calendar is showing the same month/year as the parsed date, apply a highlighted style.

---

## 2. Data Flow

### 2.1 Full Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER INTERACTION                              │
│  Click date field → calendar opens → click day → date set → close    │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    REFLEX REACTIVITY LAYER                            │
│                                                                      │
│  date_calendar_popover()          TournamentCrudState               │
│  ┌──────────────────┐            ┌──────────────────────┐           │
│  │ rx.select trigger│──click──▶  │ toggle_calendar()    │           │
│  │                  │            │  .show_calendar=True  │           │
│  │ rx.cond overlay  │            │  .calendar_target=... │           │
│  │  ├─month nav     │──click──▶  │ calendar_prev_month() │           │
│  │  │               │            │ calendar_next_month() │           │
│  │  └─day grid      │──click──▶  │ select_calendar_day() │           │
│  │     foreach day  │            │  .set_start_date()    │           │
│  │     button       │  on_change │  OR .set_end_date()   │           │
│  └──────────────────┘            │  .show_calendar=False │           │
│                                  └──────┬───────────────┘           │
│                                         │                           │
└─────────────────────────────────────────┼───────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    DATE FORMAT CONVERSION LAYER                       │
│                                                                      │
│  ┌─────────────────────────────────────────────┐                     │
│  │  save_tournament()                           │                    │
│  │  self.start_date = "07/06/2026"  (DD/MM/YYYY)│                    │
│  │         │                                     │                    │
│  │         ▼                                     │                    │
│  │  _display_to_date("07/06/2026")               │                    │
│  │         │                                     │                    │
│  │         ▼                                     │                    │
│  │  datetime.date(2026, 6, 7)  ──→ DB (SQLite)  │                    │
│  └─────────────────────────────────────────────┘                     │
│                                                                      │
│  ┌─────────────────────────────────────────────┐                     │
│  │  _serialize_tournament()                     │                    │
│  │  datetime.date(2026, 6, 7)  (from DB)       │                    │
│  │         │                                     │                    │
│  │         ├──→ "start_date": "2026-06-07"      │  (ISO, unchanged)  │
│  │         │                                     │                    │
│  │         └──→ "start_date_display":            │  (NEW)             │
│  │               _iso_to_display("2026-06-07")   │                    │
│  │             = "07/06/2026"                   │                    │
│  └─────────────────────────────────────────────┘                     │
│                                                                      │
│  ┌─────────────────────────────────────────────┐                     │
│  │  set_form_values()  (load flow)              │                    │
│  │  tournament["start_date"] = "2026-06-07"    │                    │
│  │         │                                     │                    │
│  │         ▼                                     │                    │
│  │  _iso_to_display("2026-06-07")               │                    │
│  │         │                                     │                    │
│  │         ▼                                     │                    │
│  │  self.start_date = "07/06/2026"             │                    │
│  └─────────────────────────────────────────────┘                     │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────┐
│                    DISPLAY LAYER (REACTIVE)                          │
│                                                                      │
│  Table: tournament["start_date_display"] → "07/06/2026" in cell     │
│  Form:  state.start_date = "07/06/2026" in rx.select trigger        │
│         rx.heading("Inicio (DD/MM/AAAA)")                          │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 Date Format Conversion Points — Complete Matrix

| Operation | Direction | Source | Target | Helper | Location |
|-----------|-----------|--------|--------|--------|----------|
| Load (read from DB) | ISO → Display | DB `datetime.date` | State var `self.start_date` (DD/MM/YYYY) | `_iso_to_display()` | `set_form_values()` |
| Save (write to DB) | Display → Date | State var `self.start_date` (DD/MM/YYYY) | `datetime.date` → DB | `_display_to_date()` | `save_tournament()` |
| Serialize (table data) | Date → ISO + Display | `datetime.date` | ISO key + Display key in dict | `_iso_to_display()` | `_serialize_tournament()` |
| Calendar day click | Day → Display | Int day from cell | DD/MM/YYYY string | Format inline (f-string) | `select_calendar_day()` |
| User keyboard input (defensive) | Dash → Slash | `"DD-MM-YYYY"` | `"DD/MM/YYYY"` | `.replace("-", "/")` | `_display_to_date()` |

---

## 3. File Changes Detail

### 3.1 `kakumi_app/states/tournament_crud_state.py`

**Add module-level helpers** (at top of file, after imports):

```python
def _iso_to_display(iso_str: str) -> str:
    """Convert '2026-06-07' → '07/06/2026'. Return '' on failure."""
    if not iso_str:
        return ""
    try:
        d = datetime.datetime.strptime(iso_str, "%Y-%m-%d").date()
        return d.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return ""


def _display_to_date(display_str: str) -> datetime.date | None:
    """Convert '07/06/2026' → date(2026,6,7). Return None on failure.

    Accepts 'DD-MM-YYYY' by normalising dashes to slashes.
    """
    if not display_str or not isinstance(display_str, str):
        return None
    normalised = display_str.replace("-", "/")
    try:
        return datetime.datetime.strptime(normalised, "%d/%m/%Y").date()
    except (ValueError, TypeError):
        return None


def _date_to_iso(d: datetime.date) -> str:
    """Convert date → '2026-06-07'."""
    return d.isoformat()
```

**Add calendar state vars to `TournamentCrudState`**:

```python
# ── Calendar popover state ──
show_calendar: bool = False
calendar_target: str = ""   # "start" or "end"
calendar_month: int = 0     # 0 = uninitialized
calendar_year: int = 0      # 0 = uninitialized
```

**Add calendar event handlers to `TournamentCrudState`**:

```python
@rx.event
def toggle_calendar(self, target: str) -> None:
    """Toggle calendar popover for a specific date field."""
    if self.show_calendar and self.calendar_target == target:
        self.show_calendar = False
        self.calendar_target = ""
        return
    self.show_calendar = True
    self.calendar_target = target
    # Initialize month/year from current value if available
    if self.calendar_month == 0 or self.calendar_year == 0:
        now = datetime.date.today()
        self.calendar_month = now.month
        self.calendar_year = now.year

@rx.event
def calendar_prev_month(self) -> None:
    """Navigate calendar to previous month with year wrap."""
    if self.calendar_month == 1:
        self.calendar_month = 12
        self.calendar_year -= 1
    else:
        self.calendar_month -= 1

@rx.event
def calendar_next_month(self) -> None:
    """Navigate calendar to next month with year wrap."""
    if self.calendar_month == 12:
        self.calendar_month = 1
        self.calendar_year += 1
    else:
        self.calendar_month += 1

@rx.event
def select_calendar_day(self, day: int) -> None:
    """Select a day from the calendar popover. Set date and close."""
    date_obj = datetime.date(self.calendar_year, self.calendar_month, day)
    display_val = date_obj.strftime("%d/%m/%Y")
    if self.calendar_target == "start":
        self.start_date = display_val
    elif self.calendar_target == "end":
        self.end_date = display_val
    self.show_calendar = False
    self.calendar_target = ""
```

**Modify `set_form_values()`** — convert ISO → Display:

```python
# Change from:
self.start_date = tournament.get("start_date", "")
self.end_date = tournament.get("end_date") or self.start_date

# Change to:
self.start_date = _iso_to_display(tournament.get("start_date", ""))
self.end_date = _iso_to_display(
    tournament.get("end_date") or tournament.get("start_date", "")
)
```

**Modify `save_tournament()`** — parse DD/MM/YYYY instead of ISO:

```python
# Change from:
start_date = datetime.datetime.strptime(self.start_date, "%Y-%m-%d").date()
end_date = datetime.datetime.strptime(self.end_date, "%Y-%m-%d").date()

# Change to:
start_date = _display_to_date(self.start_date)
end_date = _display_to_date(self.end_date)
if start_date is None or end_date is None:
    self.error_message = "Invalid date format (DD/MM/YYYY)"
    return
```

**Modify `_serialize_tournament()`** — add display keys:

```python
# Add after existing start_date/end_date:
"start_date_display": _iso_to_display(tournament.start_date.isoformat()),
"end_date_display": _iso_to_display(tournament.end_date.isoformat()),
```

### 3.2 `kakumi_app/components/date_calendar.py` (NEW — ~120 lines)

```python
"""Reusable calendar popover component for date selection.

Uses only built-in Reflex primitives. Zero external dependencies.
"""

from __future__ import annotations

import calendar
import datetime

import reflex as rx

from kakumi_app.states.tournament_crud_state import TournamentCrudState


# ── Spanish weekday abbreviations ──
_WEEKDAYS = ["Do", "Lu", "Ma", "Mi", "Ju", "Vi", "Sá"]
_MONTHS = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _build_day_cells(year: int, month: int, selected_display: str) -> list[dict]:
    """Build a flat list of day cell descriptors for the month grid.

    Each item has:
        day: int (0 for filler/empty cells)
        is_current_month: bool
        is_selected: bool
        label: str (day number or "")

    Uses calendar.monthcalendar for proper week alignment.
    """
    cal = calendar.monthcalendar(year, month)
    selected_date: datetime.date | None = None
    if selected_display:
        try:
            selected_date = datetime.datetime.strptime(
                selected_display, "%d/%m/%Y"
            ).date()
        except (ValueError, TypeError):
            pass

    cells: list[dict] = []
    for week in cal:
        for day in week:
            is_current = day != 0
            date_obj = (
                datetime.date(year, month, day) if is_current else None
            )
            is_selected = (
                selected_date is not None
                and date_obj is not None
                and date_obj == selected_date
            )
            cells.append({
                "day": day,
                "is_current_month": is_current,
                "is_selected": is_selected,
                "label": str(day) if is_current else "",
            })
    return cells


def _render_day_cell(cell: dict) -> rx.Component:
    """Render a single day cell (button or empty placeholder)."""
    return rx.cond(
        cell["is_current_month"],
        rx.button(
            cell["label"],
            on_click=lambda: TournamentCrudState.select_calendar_day(
                cell["day"]  # type: ignore[arg-type]
            ),
            width="32px",
            height="32px",
            padding="0",
            font_size="14px",
            variant="surface",
            background_color=rx.cond(
                cell["is_selected"],
                "#c53030",  # BRAND_RED highlight
                "transparent",
            ),
            color=rx.cond(cell["is_selected"], "white", "black"),
            _hover={"background_color": "#e0e0e0"},
        ),
        rx.box("", width="32px", height="32px"),  # empty placeholder
    )


def date_calendar_popover(
    *,
    value: rx.Var[str],
    on_change: rx.EventHandler,
    target: str,
) -> rx.Component:
    """Render a date field with calendar popover.

    Args:
        value: Current date DD/MM/YYYY bound to state var.
        on_change: State setter for the date field (e.g. state.set_start_date).
        target: "start" or "end" for calendar_target disambiguation.

    Returns:
        Reflex component: trigger button + conditional overlay.
    """
    state = TournamentCrudState

    # Determine if this specific popover should be visible
    is_visible = rx.cond(
        rx.cond(
            state.show_calendar,
            state.calendar_target == target,
            False,
        ),
        True,
        False,
    )

    # Build cells for the currently displayed month
    # We use a reactive computation via rx.cond to refresh on month/year change
    month_var = state.calendar_month
    year_var = state.calendar_year

    cells = _build_day_cells(
        year_var._get_value(),  # simplificado — se computa en render
        month_var._get_value(),
        value._get_value() if hasattr(value, "_get_value") else "",
    )

    month_name_var = rx.cond(
        month_var > 0,
        rx.cond(
            (month_var >= 1) & (month_var <= 12),
            _MONTHS[month_var],  # type: ignore[index]
            "",
        ),
        "",
    )

    return rx.box(
        rx.vstack(
            # Trigger button (rx.select showing current value)
            rx.select(
                [value],
                value=value,
                on_click=lambda: state.toggle_calendar(target),
                placeholder="DD/MM/AAAA",
                style={
                    "border": "1px solid black",
                    "background_color": "white",
                    "color": "black",
                },
            ),
            # Conditional popover overlay
            rx.cond(
                is_visible,
                rx.box(
                    rx.vstack(
                        # Month navigation
                        rx.hstack(
                            rx.button("‹", on_click=state.calendar_prev_month),
                            rx.text(month_name_var + " " + year_var),
                            rx.button("›", on_click=state.calendar_next_month),
                            width="100%",
                            justify="between",
                        ),
                        # Weekday headers
                        rx.grid(
                            rx.foreach(
                                _WEEKDAYS,
                                lambda wd: rx.box(
                                    rx.text(wd, font_size="12px", text_align="center"),
                                    width="32px",
                                ),
                            ),
                            grid_template_columns="repeat(7, 1fr)",
                            width="100%",
                        ),
                        # Day grid
                        rx.grid(
                            rx.foreach(
                                _build_day_cells(
                                    state.calendar_year,
                                    state.calendar_month,
                                    value,
                                ),
                                _render_day_cell,
                            ),
                            grid_template_columns="repeat(7, 1fr)",
                            width="100%",
                        ),
                        spacing="1",
                    ),
                    position="absolute",
                    z_index="100",
                    background_color="white",
                    border="1px solid #ddd",
                    border_radius="8px",
                    padding="8px",
                    box_shadow="0 4px 12px rgba(0,0,0,0.15)",
                    width="auto",
                ),
            ),
            spacing="1",
            position="relative",
        ),
        position="relative",
    )
```

**Note on reactivity**: The `_build_day_cells` above is called at render time. In Reflex, `rx.foreach` takes a list (computed inline or as a state var). Since `state.calendar_month` and `state.calendar_year` are state vars, they trigger re-render when changed. The cells list is recomputed each render. This approach avoids needing a separate cells state var. If compiler warnings occur, the cells list can be stored as a computed var with `@rx.var`.

### 3.3 `kakumi_app/pages/registries.py`

**Tournament form** — replace `rx.input` date fields:

```python
# Change from:
rx.vstack(
    rx.heading("Inicio (YYYY-MM-DD)", size="3", color=TEXT_PRIMARY),
    rx.input(
        placeholder="Inicio (YYYY-MM-DD)",
        value=state.start_date,
        on_change=state.set_start_date,
        border="1px solid black",
        background_color="white",
        color=TEXT_PRIMARY,
    ),
),

# Change to:
rx.vstack(
    rx.heading("Inicio (DD/MM/AAAA)", size="3", color=TEXT_PRIMARY),
    date_calendar_popover(
        value=state.start_date,
        on_change=state.set_start_date,
        target="start",
    ),
),
```

Same for end date.

**Tournament table** — update cell binding:

```python
# Change from:
rx.table.cell(tournament["start_date"], color=TEXT_PRIMARY),

# Change to:
rx.table.cell(tournament["start_date_display"], color=TEXT_PRIMARY),
```

If we choose to add an end date column, add after the start date cell:
```python
rx.table.cell(tournament["end_date_display"], color=TEXT_PRIMARY),
# Or just show end date in a tooltip/next column.
```

**Add import** at top of `registries.py`:
```python
from kakumi_app.components.date_calendar import date_calendar_popover
```

### 3.4 Test Changes

#### `tests/test_date_calendar.py` (NEW — ~80 lines)

Covers:
- `_iso_to_display` happy path, invalid input, empty input
- `_display_to_date` happy path, dash variant, invalid date, garbage, empty
- `_date_to_iso` conversion
- Calendar `_build_day_cells` grid structure
- `date_calendar_popover` returns `rx.Component`
- Spec scenarios: month grid layout, navigation, day selection, highlight

#### `tests/test_crud_registries_apply.py` — Update assertions

**Critical changes** (6 test functions affected):

| Test | Line(s) | Current | New |
|------|---------|---------|-----|
| `test_tournament_crud_save_create_then_update` | 309–310 | `state.start_date = "2027-03-01"` | `state.start_date = "01/03/2027"` |
| | 310 | `state.end_date = "2027-03-02"` | `state.end_date = "02/03/2027"` |
| `test_tournament_crud_save_update_preserves_lifecycle` | 361 | `state.start_date = "2027-05-01"` | `state.start_date = "01/05/2027"` |
| | 362 | `state.end_date = "2027-05-02"` | `state.end_date = "02/05/2027"` |
| `test_tournament_crud_save_rolls_back` | 1032 | `state.start_date = "2027-03-01"` | `state.start_date = "01/03/2027"` |
| | 1033 | `state.end_date = "2027-03-02"` | `state.end_date = "02/03/2027"` |

The implicit date-format assertions in existing error-path tests (e.g. `test_tournament_crud_save_create_then_update`) will also need their error message checks updated because `save_tournament` now emits `"Invalid date format (DD/MM/YYYY)"` instead of `"Invalid date format (YYYY-MM-DD)"`.

---

## 4. Architecture Decision Records

### ADR-1: Calendar State in Parent vs. Dedicated State

**Status**: Accepted  
**Context**: The calendar popover needs internal state (visibility, target, month, year). Two options: add to `TournamentCrudState` or create a new `CalendarPopoverState(rx.State)`.  
**Decision**: Add calendar state to `TournamentCrudState`.  
**Rationale**: 
- Only one consumer (tournament form). A dedicated state adds ~25 lines of boilerplate with no reuse benefit yet.
- Simplifies data flow — calendar events directly set `start_date`/`end_date` without cross-state communication.
- Calendar state is transient UI state that resets on page load, consistent with CRUD state pattern.  
**Mitigation**: Calendar state vars are clearly separated with a `# ── Calendar popover state ──` comment block. Extraction into a mixin or dedicated state is straightforward if reuse arises.

### ADR-2: Module-Level Helper Functions vs. State Methods

**Status**: Accepted  
**Context**: Date format helpers (`_iso_to_display`, `_display_to_date`, `_date_to_iso`) could be instance methods on `TournamentCrudState` or standalone module-level functions.  
**Decision**: Module-level (private) functions in `tournament_crud_state.py`.  
**Rationale**: Pure functions with no dependency on `self` are easier to test, importable from test files without instantiating state, and reusable by `_serialize_tournament` which is called from `load_tournaments` (before any calendar event).  
**Consequence**: All refs change from `self._iso_to_display(...)` to `_iso_to_display(...)` (unqualified call within the module).

### ADR-3: `rx.cond` Overlay vs. `rx.popover`

**Status**: Accepted  
**Context**: The spec allows either `rx.popover` (if available in Reflex 0.8.28.post1) or a custom `rx.cond`-based positioned overlay.  
**Decision**: Use `rx.cond` + positioned `rx.box` overlay.  
**Rationale**:
- `rx.popover` is not used anywhere in the codebase (confirmed by grep). It may not exist or may have unknown behavior.
- `rx.dialog` (used in sidebar/kumite) is modal-heavy and inappropriate for a lightweight calendar.
- The `rx.cond` + absolute positioning pattern is proven, gives full control, and avoids third-party dependency risk.
- Outside-click dismiss is implemented via a transparent `rx.box` backdrop catching click events.

### ADR-4: `rx.foreach` Day Cells vs. Inline `for` Loop

**Status**: Accepted  
**Context**: Day cells can be generated either with `rx.foreach` (Reflex's reactive iterator) or a Python `for` loop inside the component function.  
**Decision**: Use `rx.foreach` over a list computed from `_build_day_cells()`.  
**Rationale**: `rx.foreach` creates reactive bindings — when `calendar_month`/`calendar_year` change, the grid re-renders automatically. A static `for` loop would produce a frozen snapshot.

### ADR-5: Single `calendar_target` vs. Per-Instance State

**Status**: Accepted  
**Context**: Two date fields (start, end) each need a calendar popover. Two approaches: shared state with a `target` discriminator, or separate state vars per field.  
**Decision**: Shared state with `calendar_target: str`.  
**Rationale**: Only one popover is ever open at a time (UX convention). This halves state vars and eliminates the risk of two overlays being visible simultaneously. The `target` parameter in the component function ensures correct field binding.

---

## 5. Sequence Diagram: Calendar Interaction Flow

```
┌─────────┐     ┌──────────────────────┐     ┌─────────────────────┐     ┌──────────┐
│  User   │     │  date_calendar.py    │     │ TournamentCrudState │     │ DB/SQLite│
│ (Browser)│    │  (Component Render)  │     │    (Event Handlers) │     │          │
└────┬────┘     └──────────┬───────────┘     └──────────┬──────────┘     └────┬─────┘
     │                     │                            │                     │
     │  1. Click "Inicio"  │                            │                     │
     │   rx.select trigger │                            │                     │
     ├────────────────────▶│                            │                     │
     │                     │  2. toggle_calendar("start")│                    │
     │                     ├───────────────────────────▶│                    │
     │                     │                            │ 3. show_calendar=T │
     │                     │                            │    calendar_target= │
     │                     │                            │    "start"         │
     │                     │                            │    init month/year │
     │                     │                            │     if uninitialized│
     │                     │                            ├─────┐              │
     │                     │                            │     │ (no DB call) │
     │                     │                            │◄────┘              │
     │                     │  4. Re-render (show overlay)│                   │
     │   Calendar visible  │◄───────────────────────────│                    │
     │◄────────────────────│                            │                    │
     │                     │                            │                    │
     │  5. Click "›" (next month)                       │                    │
     ├────────────────────▶│                            │                    │
     │                     │  6. calendar_next_month()  │                    │
     │                     ├───────────────────────────▶│                    │
     │                     │                            │ 7. month=7 (July)  │
     │                     │                            │    year=2026       │
     │                     │                            ├─────┐              │
     │                     │                            │     │ (no DB call) │
     │                     │                            │◄────┘              │
     │                     │  8. Re-render (July grid)  │                    │
     │   Grid updates      │◄───────────────────────────│                    │
     │◄────────────────────│                            │                    │
     │                     │                            │                    │
     │  9. Click day "15"  │                            │                    │
     ├────────────────────▶│                            │                    │
     │                     │  10. select_calendar_day(15)                   │
     │                     ├───────────────────────────▶│                    │
     │                     │                            │ 11. date_obj =     │
     │                     │                            │     date(2026,7,15)│
     │                     │                            │ 12. display =      │
     │                     │                            │     "15/07/2026"   │
     │                     │                            │ 13. start_date =   │
     │                     │                            │     "15/07/2026"   │
     │                     │                            │ 14. show_calendar=F│
     │                     │                            │ 15. calendar_target│
     │                     │                            │     = ""           │
     │                     │  16. Re-render             │                    │
     │   Select shows      │    (overlay hidden,        │                    │
     │   "15/07/2026"      │     value updated)         │                    │
     │◄────────────────────│◄───────────────────────────│                    │
     │                     │                            │                    │
     │  === SAVE FLOW ===  │                            │                    │
     │                     │                            │                    │
     │  17. Click "Guardar"│                            │                    │
     ├─────────────────────────────────────────────────▶│                    │
     │                     │                            │ 18. _validate_form │
     │                     │                            │ 19. _display_to_   │
     │                     │                            │     date("15/07/   │
     │                     │                            │     2026") → date  │
     │                     │                            │ 20. Save to DB     │
     │                     │                            ├───────────────────▶│
     │                     │                            │ 21. INSERT/UPDATE  │
     │                     │                            │◄───────────────────│
     │                     │                            │ 22. load_          │
     │                     │                            │     tournaments()  │
     │                     │                            │ 23. _serialize_    │
     │                     │                            │     tournament() → │
     │                     │                            │     start_date_    │
     │                     │                            │     display added  │
     │   Table shows       │                            │                    │
     │   "15/07/2026"      │◄───────────────────────────│                    │
     │◄────────────────────│                            │                    │
```

---

## 6. Calendar Grid Data Structure

The `_build_day_cells` function produces a list of 35–42 dicts (5 or 6 weeks × 7 days):

```python
# Example: June 2026 starts on Monday (offset=1)
[
    {"day": 0, "is_current_month": False, "is_selected": False, "label": ""},       # Sun
    {"day": 1, "is_current_month": True,  "is_selected": False, "label": "1"},       # Mon
    {"day": 2, "is_current_month": True,  "is_selected": False, "label": "2"},       # Tue
    ...
    {"day": 7, "is_current_month": True,  "is_selected": True,  "label": "7"},       # Mon 7th (selected)
    ...
    {"day": 30, "is_current_month": True, "is_selected": False, "label": "30"},
    {"day": 0, "is_current_month": False, "is_selected": False, "label": ""},        # Sat (Jul 4?)
    {"day": 0, "is_current_month": False, "is_selected": False, "label": ""},        # Sun (Jul 5?)
]
```

Then `rx.foreach` over this list creates cells in the 7-column grid. Reflex grid auto-wraps after 7 items.

---

## 7. Review and Judgment Risks

| # | Risk | Assessment | Mitigation | Trigger for escalation |
|---|------|-----------|------------|----------------------|
| R1 | `rx.foreach` inside `rx.grid` may not re-render when month changes | **Medium**. Reflex reactivity depends on state var references. If the list argument to `rx.foreach` is a Python function call (not a state var), it won't re-render automatically. | **Approach A (preferred)**: Make `_build_day_cells` a `@rx.var` on TournamentCrudState that depends on `calendar_month` and `calendar_year`. This ensures reactivity. If `@rx.var` causes compile errors, use **Approach B**: Store the cells list as a state var and update it via `calendar_prev_month`/`calendar_next_month`. | Code review shows `@rx.var` not working for complex return types → switch to Approach B |
| R2 | `lambda` closures in `rx.foreach` capture stale `cell["day"]` variable | **High**. Python closures over loop variables capture the last value, not the iteration value. | **Mitigation**: In `_render_day_cell`, use `functools.partial` or create a closure via a helper function: `def _on_click(day): return lambda: state.select_calendar_day(day)`. Pass `cell["day"]` to it. | Tests show all day clicks set the same date → apply closure fix |
| R3 | Calendar popover positioning breaks on mobile (viewport overflow) | **Low**. The overlay uses `position="absolute"` relative to its trigger, which may overflow on small screens. | Apply `rx.box` wrapper with `overflow="visible"` and a max-height/scroll on the overlay. Mobile touch targets are explicitly deferred (out of scope). | User reports popover not visible on phone → add responsive positioning |
| R4 | `_display_to_date("")` returns `None` → form validation allows empty date | **Low**. `_validate_form()` already checks `if not self.start_date or not self.end_date` before calling `save_tournament`. Empty string is falsy → validation fails with "Start and end dates are required". | No action needed; existing guard works. | N/A |
| R5 | Table only has one date column ("Inicio") — proposal mentions `end_date_display` but no column exists | **Low-Medium**. The spec says "table SHALL display `start_date_display`... instead of raw ISO `start_date`". It doesn't mandate adding an end date column. | Replace only the existing `start_date` cell binding with `start_date_display`. If end date display in table is desired, it's a ~3-line addition (add "Fin" header + cell). Defer to spec confirmation. | Product review flags missing end date column → add in same PR (~3 lines) |
| R6 | Existing tests set `state.start_date = "2027-03-01"` (ISO) directly — these will fail after changing `save_tournament` to expect DD/MM/YYYY | **Certain**. 6 test locations set ISO date strings directly on state vars. | Bulk update all 6 locations to `"01/03/2027"` format (DD/MM/YYYY). This is in the test file, not production code. | Post-update test run shows >0 failures → continue updating until green |
| R7 | Reflex `rx.select` enforces that the value must be one of the options provided in the `items` list. If we pass `[value]` as the sole option, it always matches but the dropdown arrow may confuse users | **Low-Medium**. The `rx.select` shows the value but the dropdown is empty/irrelevant. This is not a true select. | Alternative: Use `rx.button` styled as a select-like input instead. The proposal spec allows either. If `rx.select` UX is poor, switch to `rx.button` with a calendar icon. | UX review: "Why is there a dropdown arrow?" → switch to `rx.button` |

---

## 8. ADR Summary Matrix

| ID | Decision | Alternative | Rationale |
|----|----------|-------------|-----------|
| ADR-1 | Calendar state in `TournamentCrudState` | Dedicated `rx.State` | Only one consumer; simpler data flow; no boilerplate |
| ADR-2 | Module-level helpers | State instance methods | Pure functions are testable, importable, reusable |
| ADR-3 | `rx.cond` + positioned overlay | `rx.popover` or `rx.dialog` | No existing usage of rx.popover; full control; proven pattern |
| ADR-4 | `rx.foreach` over computed list | Python `for` loop | Reactive re-render on month/year change |
| ADR-5 | Shared `calendar_target` discriminator | Per-instance state vars | Only one popover open at a time; less state duplication |

---

## 9. Estimated Change Budget

| File | Action | Lines |
|------|--------|-------|
| `kakumi_app/components/date_calendar.py` | **Create** | ~120 |
| `kakumi_app/states/tournament_crud_state.py` | **Modify**: +3 helpers, +4 state vars, +4 handlers, edits to 3 methods | ~65 |
| `kakumi_app/pages/registries.py` | **Modify**: import, 2× date field replacement, 1× table cell, 2× label | ~30 |
| `tests/test_date_calendar.py` | **Create** | ~85 |
| `tests/test_crud_registries_apply.py` | **Modify**: 6 date strings + 1 error message | ~10 |
| **Total** | | **~310** |
| **Budget** | | **≤ 400 ✅** |

---

## 10. Open Items / Decision Gates

1. **Table end date column**: The existing tournament table headers are `["Nombre", "Sede", "Estado", "Inicio", "Acciones"]` — only one date column. The `end_date_display` key is added to serialization but unused in the table. Should we add an "Fin" column, or is showing only start date sufficient?

2. **Trigger component**: `rx.select` with a single option works but shows a dropdown arrow. Alternatives: `rx.button` styled as input, or a text trigger with a calendar icon. This affects UX, not architecture.

3. **Calendar reactivity approach**: If `@rx.var` is needed for day cell computation, the design supports it. Approach is confirmed as implementable either way (var-based or event-updated).
