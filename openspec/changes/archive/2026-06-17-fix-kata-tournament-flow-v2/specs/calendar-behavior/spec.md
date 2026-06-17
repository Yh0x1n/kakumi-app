# Delta: Calendar Behavior — Prevent Unintended Form Submit

## Purpose

Fix the calendar date picker component so its interactive elements (day buttons, navigation arrows, trigger button) do NOT trigger `type="submit"` behavior when used inside an `rx.form()` context. Only the explicit "Save" submit button in the hosting form SHALL trigger submission.

## MODIFIED Requirements

### Requirement: Calendar Buttons Type Attribute

Every `rx.button` inside `date_calendar_popover()` MUST have `type="button"` to prevent default submit behavior in an `rx.form()` context. This applies to:
1. Day cell buttons (`_render_day_cell`)
2. Month navigation buttons (`‹` and `›` in `nav_header`)
3. The trigger button (styled input-like button in the closed state)
(Previously: buttons had no `type` attribute, defaulting to `type="submit"` when inside a form)

#### Scenario: Day click does not submit form

- GIVEN a form containing `date_calendar_popover` as a child component
- WHEN the operator clicks a day cell in the calendar overlay
- THEN the day MUST be selected
- AND the form MUST NOT be submitted

#### Scenario: Month navigation does not submit form

- GIVEN the calendar overlay is visible
- WHEN the operator clicks the `‹` or `›` navigation button
- THEN the displayed month MUST change
- AND the form MUST NOT be submitted

#### Scenario: Calendar trigger does not submit form

- GIVEN the calendar is closed
- WHEN the operator clicks the trigger button to open the overlay
- THEN the calendar overlay MUST open
- AND the form MUST NOT be submitted

#### Scenario: Save button still submits form

- GIVEN the form is open with calendar and a "Guardar" button
- WHEN the operator clicks the "Guardar" button
- THEN the form MUST submit normally
- AND the calendar buttons MUST NOT interfere

## REMOVED Requirements

(This section intentionally blank — no requirements removed.)
