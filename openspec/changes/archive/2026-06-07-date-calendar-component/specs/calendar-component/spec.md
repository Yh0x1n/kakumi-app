# Calendar Popover Component Specification

## Purpose

Define a reusable Reflex component that renders a mini month-grid calendar popover for date selection. The component SHALL provide month navigation (prev/next), highlight the currently selected date, and invoke an `on_change` callback with the chosen date in DD/MM/YYYY format. It SHALL be triggerable from an `rx.select` or `rx.button` and SHALL use only built-in Reflex components with zero external dependencies.

## Requirements

### Requirement: Calendar Renders Month Grid

The calendar popover SHALL render a month grid with day cells arranged in a 7-column layout (Sunday through Saturday), with each column header showing abbreviated weekday names (`Do`, `Lu`, `Ma`, `Mi`, `Ju`, `Vi`, `Sá` for Spanish locale).

Day cells SHALL be `rx.button` elements bound to an `rx.foreach` over the day numbers for the visible month. Empty leading/trailing cells SHALL be rendered for days outside the current month to preserve grid alignment.

#### Scenario: Month grid shows correct day layout

- GIVEN the component is rendered with visible month = June 2026
- WHEN the calendar popover is open
- THEN the grid MUST display 7 columns (Sun–Sat)
- AND column headers MUST display abbreviated Spanish weekday names
- AND day cells starting from the correct weekday offset MUST be rendered for 1 through 30 (June has 30 days)

#### Scenario: Grid uses rx.foreach for day cells

- GIVEN the component renders day cells
- THEN day cell content MUST be generated via `rx.foreach`
- AND each cell MUST be an `rx.button` with an `on_click` handler

### Requirement: Month Navigation Buttons

The calendar popover SHALL render prev-month and next-month navigation buttons. The prev-month button SHALL decrement the displayed month by one; the next-month button SHALL increment it by one. Year boundaries SHALL wrap correctly (e.g., January prev goes to December of previous year).

#### Scenario: Previous month navigation

- GIVEN the calendar is showing June 2026
- WHEN the user clicks the prev-month button
- THEN the displayed month SHALL change to May 2026

#### Scenario: Next month navigation

- GIVEN the calendar is showing June 2026
- WHEN the user clicks the next-month button
- THEN the displayed month SHALL change to July 2026

#### Scenario: Year boundary wrap — prev from January

- GIVEN the calendar is showing January 2027
- WHEN the user clicks the prev-month button
- THEN the displayed month SHALL change to December 2026
- AND the displayed year SHALL change to 2026

#### Scenario: Year boundary wrap — next from December

- GIVEN the calendar is showing December 2026
- WHEN the user clicks the next-month button
- THEN the displayed month SHALL change to January 2027
- AND the displayed year SHALL change to 2027

### Requirement: Day Selection Sets Date

Clicking a day cell SHALL invoke the `on_change` callback with the selected date formatted as DD/MM/YYYY string. After selection, the popover SHALL close (visibility toggled off).

#### Scenario: Day click selects date

- GIVEN the calendar is showing June 2026
- AND the calendar is open (visible)
- WHEN the user clicks day cell "7"
- THEN `on_change` MUST be called with `"07/06/2026"`
- AND the popover SHALL close (visibility becomes hidden)

#### Scenario: Double-digit day formatting

- GIVEN the calendar is showing June 2026
- WHEN the user clicks day cell "15"
- THEN `on_change` MUST be called with `"15/06/2026"`

#### Scenario: Single-digit day zero-padding

- GIVEN the calendar is showing March 2026
- WHEN the user clicks day cell "3"
- THEN `on_change` MUST be called with `"03/03/2026"`

### Requirement: Popover Visibility Toggled via rx.cond

The calendar popover SHALL use `rx.cond` to toggle its visibility. When hidden, the popover SHALL NOT render in the DOM (removes layout impact).

The popover SHALL be implemented as a positioned `rx.box` overlay relative to its trigger element. Positioning SHALL use Reflex style props (e.g., `position="absolute"`, `z_index`).

If Reflex 0.8.28.post1 provides `rx.popover` with correct focus-trapping and dismiss-on-click-outside behaviour, `rx.popover` MAY be used instead of `rx.cond`.

#### Scenario: Hidden calendar not in DOM

- GIVEN the popover is closed (`show_calendar = False`)
- WHEN the parent component renders
- THEN the calendar grid content MUST NOT appear in the rendered output

#### Scenario: Visible calendar renders overlay

- GIVEN the popover is open (`show_calendar = True`)
- WHEN the parent component renders
- THEN the calendar grid MUST be visible as an overlay positioned near the trigger

### Requirement: Currently Selected Date Highlight

The calendar popover SHALL highlight the currently selected date cell if it falls within the visible month. The highlight SHALL use a distinct visual style (e.g., different background colour).

#### Scenario: Selected date highlighted in same month

- GIVEN the current value is `"07/06/2026"` and the calendar is showing June 2026
- WHEN the popover renders
- THEN day cell "7" MUST have a highlighted style distinct from other day cells

#### Scenario: No highlight when selected date outside visible month

- GIVEN the current value is `"07/06/2026"` and the calendar is showing January 2026
- WHEN the popover renders
- THEN no day cell SHALL be highlighted

### Requirement: Popover Accepts value and on_change Props

The component function `date_calendar_popover(value: str, on_change: callable)` SHALL accept:

- `value`: A DD/MM/YYYY string representing the currently selected date (or empty string when no date selected)
- `on_change`: A callback function that receives the selected DD/MM/YYYY string

#### Scenario: Empty value renders no selection

- GIVEN `value = ""` (no date selected yet)
- WHEN the calendar popover renders
- THEN no day cell SHALL be highlighted

### Requirement: Zero External Dependencies

The component SHALL use only built-in Reflex 0.8.28.post1 components (`rx.grid`, `rx.button`, `rx.cond`, `rx.box`, `rx.text`, `rx.hstack`, `rx.vstack`, `rx.foreach`, `rx.match` or equivalent). Zero new Python or JavaScript packages SHALL be added.

#### Scenario: No new imports from external packages

- GIVEN the file `kakumi_app/components/date_calendar.py`
- WHEN all import statements are inspected
- THEN all imports MUST resolve to Python standard library modules or Reflex package (`reflex` / `rx`)
- AND no new entries SHALL be added to `requirements.txt` or `pyproject.toml`

### Requirement: Popover Dismisses on Outside Click

Clicking outside the calendar popover SHALL close it (set visibility to False). If `rx.popover` is used, this behaviour is built-in. If the `rx.cond` overlay approach is used, a click-outside handler SHALL be implemented.

#### Scenario: Outside click closes popover

- GIVEN the calendar popover is open
- WHEN the user clicks outside the popover bounds
- THEN the popover SHALL close
- AND `show_calendar` SHALL be set to `False`

### Requirement: Component Is Reusable

The component SHALL be exported as a named function `date_calendar_popover` from `kakumi_app/components/date_calendar.py`. It SHALL be importable and usable in any page or component that needs date selection.

#### Scenario: Importable from component module

- GIVEN a Refle page that needs date selection
- WHEN `from kakumi_app.components.date_calendar import date_calendar_popover` is executed
- THEN the import SHALL succeed
- AND calling `date_calendar_popover(value="07/06/2026", on_change=handler)` SHALL return a valid Reflex component
