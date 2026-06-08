# Date Calendar Component — SDD Spec

**Change**: `date-calendar-component`
**Phase**: Spec (complete)
**Date**: 2026-06-07
**Domain coverage**: Karate-Do tournament management (Reflex/Python)

---

## Domain Specs

Two domain specs were produced under `openspec/changes/date-calendar-component/specs/`:

### 1. Tournament Registration
**Path**: `openspec/changes/date-calendar-component/specs/tournament-registration/spec.md`
**Type**: Full spec (no canonical existed)
**Covers**:
- Format helpers: `_iso_to_display`, `_display_to_date`, `_date_to_iso`
- State integration: `set_form_values`, `save_tournament`, `_serialize_tournament`
- Form UI: `rx.select` trigger replacing `rx.input`, DD/MM/AAAA labels
- Table display: `start_date_display` / `end_date_display` columns
- Import-defensive dash normalisation

### 2. Calendar Popover Component
**Path**: `openspec/changes/date-calendar-component/specs/calendar-component/spec.md`
**Type**: Full spec (no canonical existed)
**Covers**:
- Month grid with 7-column layout and Spanish weekday headers
- Prev/next month navigation with year boundary wrap
- Day selection with zero-padded DD/MM/YYYY output
- `rx.cond`-based visibility toggle (positioned overlay)
- Currently selected date highlight
- `value` / `on_change` prop contract
- Zero external dependencies
- Outside-click dismiss behaviour
- Reusable component export

---

## Inferred Domains — Risk Note

The proposal lacked an explicit `Capabilities` section. Domains were inferred from affected areas in §2.1 In Scope:
- `tournament-registration`: All CRUD state changes, form UI, and table display
- `calendar-component`: New reusable Reflex calendar popover

This is an assumption — if the project's openspec convention expects different domain boundaries, the specs should be adjusted before archive.

---

## Verification

- **Canonical overlap**: No other active change (`disconnected-client-warnings`, `visual-styling-overhaul`, etc.) writes to `tournament-registration` or `calendar-component` domains.
- **Legacy shape**: No `openspec/changes/date-calendar-component/spec.md` exists — no legacy-to-domain migration needed.
- **All scenarios are Given/When/Then** format per `openspec/config.yaml` rules.
- **All requirements use RFC 2119** keywords (MUST, SHALL, SHOULD, MAY).
- **Testable**: Every requirement has ≥1 testable scenario.
