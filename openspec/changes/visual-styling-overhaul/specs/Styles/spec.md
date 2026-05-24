# Styles Specification — visual-styling-overhaul

## Purpose

Define a consolidated, token-driven visual styling system for the Kakumi Tournament Manager application. All color values MUST resolve through a single source of truth (`kakumi_app/styles/tokens.py`). Hardcoded literal color strings in component and page files are replaced with named tokens to ensure consistency, maintainability, and auditability.

---

## Requirements

### Requirement: Token Consolidation — CARD_BG, HEADER_BG, MUTED_TEXT migrated to tokens.py

The system MUST define the constants `CARD_BG`, `HEADER_BG`, and `MUTED_TEXT` inside `kakumi_app/styles/tokens.py`.

- `CARD_BG` MUST have value `"#ffffff"`.
- `HEADER_BG` MUST have value `"#f2f2f2"`.
- `MUTED_TEXT` MUST have value `"#534342"`.

The file `kakumi_app/components/registry_crud.py` MUST remove the inline definitions of `CARD_BG`, `HEADER_BG`, and `MUTED_TEXT` and instead import them via:

```python
from kakumi_app.styles.tokens import CARD_BG, HEADER_BG, MUTED_TEXT
```

All existing import statements in other modules that reference `MUTED_TEXT` from `registry_crud` (e.g., `pages/registries.py`) MUST be updated to import from `kakumi_app.styles.tokens` instead.

#### Scenario: CARD_BG, HEADER_BG, MUTED_TEXT exist in tokens.py

- GIVEN the file `kakumi_app/styles/tokens.py`
- WHEN the file is read
- THEN it MUST contain `CARD_BG = "#ffffff"`, `HEADER_BG = "#f2f2f2"`, and `MUTED_TEXT = "#534342"`

#### Scenario: registry_crud.py imports from tokens.py instead of defining locally

- GIVEN the file `kakumi_app/components/registry_crud.py`
- WHEN the file is scanned for `CARD_BG`, `HEADER_BG`, and `MUTED_TEXT`
- THEN these constants MUST NOT be defined as top-level assignments (no `= "#..."` lines)
- AND they MUST be imported via `from kakumi_app.styles.tokens import ...`

#### Scenario: All references to MUTED_TEXT resolve through tokens.py

- GIVEN all files that reference `MUTED_TEXT`
- WHEN the import chain is traced
- THEN every `MUTED_TEXT` usage MUST ultimately resolve to `kakumi_app.styles.tokens.MUTED_TEXT`, not to a local or transitive definition in `registry_crud`

---

### Requirement: New Text Tokens — TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY

The system MUST define three new text-color tokens in `kakumi_app/styles/tokens.py`:

- `TEXT_PRIMARY = "#000000"` — replaces all inline `color="black"` usages.
- `TEXT_SECONDARY = "#000000"` — semantic secondary token; same hex value as `TEXT_PRIMARY` to preserve current appearance while enabling future differentiation.
- `TEXT_TERTIARY = "#808080"` — replaces all inline `color="gray"` usages.

All three tokens MUST be importable by any module in the application.

#### Scenario: New tokens defined in tokens.py

- GIVEN the file `kakumi_app/styles/tokens.py`
- WHEN the file is read
- THEN it MUST contain `TEXT_PRIMARY = "#000000"`, `TEXT_SECONDARY = "#000000"`, and `TEXT_TERTIARY = "#808080"`

#### Scenario: New tokens are importable

- GIVEN a Python interpreter with `kakumi_app` on the path
- WHEN `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY` is executed
- THEN it MUST succeed without `ImportError`

---

### Requirement: BG_PAGE Token Application — Replace background_color="white"

The system MUST replace every occurrence of `background_color="white"` (or equivalently `background_color="#ffffff"`) in page-level containers with the existing token `BG_PAGE` (value `"#f5f5f5"`), as defined in `kakumi_app/styles/tokens.py`.

This applies to the following files and locations:

| File | Lines affected |
|---|---|
| `kakumi_app/kakumi_app.py` | `background_color="white"` in the `index()` function body |
| `kakumi_app/pages/exhibition.py` | `background_color="white"` in `exhibition()` (both the inner `rx.vstack` and outer `rx.box`) |
| `kakumi_app/pages/admin/users_page.py` | `background_color="white"` in `users_table()` or equivalent container |
| `kakumi_app/pages/admin/teams_page.py` | `background_color="white"` in `teams_table()` or equivalent container |
| `kakumi_app/pages/admin/export_page.py` | `background_color="white"` in the export page component |
| `kakumi_app/components/protected_layout.py` | `background_color="white"` in the authenticated layout branch |
| `kakumi_app/pages/viewer.py` | Each `background_color="white"` occurrence |
| `kakumi_app/pages/results.py` | `background_color="white"` in `_empty_state()` or equivalent container |
| `kakumi_app/pages/registries.py` | All `background_color="white"` occurrences in form fields and containers |

The token `BG_PAGE` MUST already be importable from `kakumi_app/styles/tokens.py` (it exists in the current codebase). The change spec for this requirement is in scope; implementation MUST add the import where missing.

#### Scenario: index page uses BG_PAGE

- GIVEN the file `kakumi_app/kakumi_app.py`
- WHEN searching for `background_color=`
- THEN every `background_color="white"` MUST be replaced with `background_color=BG_PAGE`
- AND `BG_PAGE` MUST be imported via `from kakumi_app.styles.tokens import BG_PAGE`

#### Scenario: exhibition page uses BG_PAGE

- GIVEN the file `kakumi_app/pages/exhibition.py`
- WHEN searching for `background_color=`
- THEN every `background_color="white"` in the `exhibition()` function MUST be replaced with `background_color=BG_PAGE`
- AND `BG_PAGE` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: protected_layout uses BG_PAGE

- GIVEN the file `kakumi_app/components/protected_layout.py`
- WHEN searching for `background_color=`
- THEN `background_color="white"` in the authenticated layout branch MUST be replaced with `background_color=BG_PAGE`
- AND `BG_PAGE` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: All page-level containers use BG_PAGE

- GIVEN each file listed in the affected-files table
- WHEN the file is scanned for `background_color="white"`
- THEN the file MUST contain zero occurrences of `background_color="white"` at page-container level

---

### Requirement: Login Page Centering

The login page (`kakumi_app/pages/auth/login.py`) MUST render its login card component centered both horizontally and vertically within the viewport.

The current layout uses `rx.center` with `rx.vstack(..., spacing="5", justify_content="center", min_height="100vh")` inside a `rx.box`. After the change, the visual result MUST be that the card appears centered vertically and horizontally with no offset, regardless of viewport size.

Additionally, the hint text `"Por favor, ingrese sus credenciales."` currently using `color="gray"` MUST use the token `TEXT_TERTIARY` instead.

#### Scenario: Login card centered horizontally and vertically

- GIVEN a browser viewport of any reasonable size (>= 400px width, >= 600px height)
- WHEN the `/login` page is rendered
- THEN the login card (`rx.card` containing the form) MUST be centered both horizontally and vertically within the viewport
- AND there MUST be no horizontal or vertical scrollbar caused by centering layout

#### Scenario: Hint text uses TEXT_TERTIARY

- GIVEN the file `kakumi_app/pages/auth/login.py`
- WHEN searching for `color="gray"` in the login page component
- THEN it MUST be replaced with `color=TEXT_TERTIARY`
- AND `TEXT_TERTIARY` MUST be imported from `kakumi_app.styles.tokens`

---

### Requirement: Replace color="black" with TEXT_PRIMARY

Every occurrence of `color="black"` in the following files MUST be replaced with `color=TEXT_PRIMARY`, importing `TEXT_PRIMARY` from `kakumi_app/styles/tokens.py` where not already present:

| File |
|---|
| `kakumi_app/kakumi_app.py` |
| `kakumi_app/pages/exhibition.py` |
| `kakumi_app/pages/tournament.py` |
| `kakumi_app/pages/results.py` |
| `kakumi_app/pages/registries.py` |
| `kakumi_app/pages/admin/users_page.py` |
| `kakumi_app/pages/admin/teams_page.py` |
| `kakumi_app/pages/admin/import_page.py` |
| `kakumi_app/components/sidebar.py` |
| `kakumi_app/components/registry_crud.py` |
| `kakumi_app/pages/viewer.py` |

Exceptions:
- `border_color="black"` in `kakumi_app/kakumi_app.py` is NOT a text color and MUST remain unchanged (unless a future border token is introduced).

#### Scenario: color="black" replaced in kakumi_app.py

- GIVEN the file `kakumi_app/kakumi_app.py`
- WHEN searching for `color="black"`
- THEN every occurrence MUST be replaced with `color=TEXT_PRIMARY`
- AND `TEXT_PRIMARY` MUST be imported from `kakumi_app.styles.tokens`
- AND any `border_color="black"` MUST NOT be changed

#### Scenario: color="black" replaced in tournament.py

- GIVEN the file `kakumi_app/pages/tournament.py`
- WHEN searching for `color="black"`
- THEN every occurrence MUST be replaced with `color=TEXT_PRIMARY`
- AND `TEXT_PRIMARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="black" replaced in registries.py

- GIVEN the file `kakumi_app/pages/registries.py`
- WHEN searching for `color="black"`
- THEN every occurrence MUST be replaced with `color=TEXT_PRIMARY`
- AND `TEXT_PRIMARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="black" replaced in all listed files

- GIVEN each file listed in the affected-files table
- WHEN the file is scanned for `color="black"` (excluding `border_color`)
- THEN the file MUST contain zero occurrences of `color="black"` in text/prop context

---

### Requirement: Replace color="gray" with TEXT_TERTIARY

Every occurrence of `color="gray"` in the following files MUST be replaced with `color=TEXT_TERTIARY`, importing `TEXT_TERTIARY` from `kakumi_app/styles/tokens.py` where not already present:

| File |
|---|
| `kakumi_app/pages/auth/login.py` |
| `kakumi_app/pages/auth/change_password.py` |
| `kakumi_app/pages/results.py` |
| `kakumi_app/pages/tournament.py` |
| `kakumi_app/pages/admin/users_page.py` |
| `kakumi_app/pages/admin/teams_page.py` |
| `kakumi_app/pages/admin/export_page.py` |
| `kakumi_app/pages/admin/import_page.py` |
| `kakumi_app/pages/viewer.py` |
| `kakumi_app/components/protected_layout.py` |
| `kakumi_app/components/match_card.py` |
| `kakumi_app/components/tables.py` |

Exceptions:
- Files under `pages/competition/` (competition pages) and `pages/public_display.py` (public display pages) are OUT of scope per proposal boundaries. If they contain `color="gray"`, they MUST remain unchanged.
- The sidebar component's `color="gray"` usages are OUT of scope per proposal (sidebar is already polished).

#### Scenario: color="gray" replaced in login.py

- GIVEN the file `kakumi_app/pages/auth/login.py`
- WHEN searching for `color="gray"`
- THEN every occurrence MUST be replaced with `color=TEXT_TERTIARY`
- AND `TEXT_TERTIARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="gray" replaced in results.py

- GIVEN the file `kakumi_app/pages/results.py`
- WHEN searching for `color="gray"`
- THEN every occurrence MUST be replaced with `color=TEXT_TERTIARY`
- AND `TEXT_TERTIARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="gray" replaced in tournament.py

- GIVEN the file `kakumi_app/pages/tournament.py`
- WHEN searching for `color="gray"`
- THEN every occurrence MUST be replaced with `color=TEXT_TERTIARY`
- AND `TEXT_TERTIARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="gray" replaced in protected_layout.py

- GIVEN the file `kakumi_app/components/protected_layout.py`
- WHEN searching for `color="gray"`
- THEN every occurrence MUST be replaced with `color=TEXT_TERTIARY`
- AND `TEXT_TERTIARY` MUST be imported from `kakumi_app.styles.tokens`

#### Scenario: color="gray" replaced in all listed files

- GIVEN each file listed in the affected-files table
- WHEN the file is scanned for `color="gray"`
- THEN the file MUST contain zero occurrences of `color="gray"`
- AND files explicitly marked as OUT of scope (competition pages, public display pages, sidebar) MUST NOT be modified

---

### Requirement: Token Import Hygiene — No orphaned imports

When a file removes its last usage of a token that was previously imported, the corresponding import line MUST also be removed to prevent unused-import lint warnings.

#### Scenario: Unused imports removed

- GIVEN a file that previously imported a token (e.g., from `registry_crud`) and that token is now sourced from `kakumi_app.styles.tokens`
- WHEN the file no longer references the old import target
- THEN the old import line MUST be removed
- AND the file MUST pass `ruff check --select F401` (unused import check) without violations related to style tokens

---

## Token Value Reference

| Token | Value | Replaces |
|---|---|---|
| `CARD_BG` | `"#ffffff"` | Inline `#ffffff` in registry_crud.py |
| `HEADER_BG` | `"#f2f2f2"` | Inline `#f2f2f2` in registry_crud.py |
| `MUTED_TEXT` | `"#534342"` | Inline `#534342` in registry_crud.py |
| `BG_PAGE` | `"#f5f5f5"` | `background_color="white"` in page containers |
| `TEXT_PRIMARY` | `"#000000"` | `color="black"` |
| `TEXT_SECONDARY` | `"#000000"` | (semantic alias, same value) |
| `TEXT_TERTIARY` | `"#808080"` | `color="gray"` |

---

## Out of Scope

The following areas MUST NOT be modified by this change:

- Competition pages (`pages/competition/`) — including bracket, category, live match pages
- Public display pages (`pages/public_display.py`, `components/public_kumite_display.py`)
- Sidebar component (`components/sidebar.py`) — already considered polished
- Dark mode implementation
- Any `border_color="black"` occurrences (border colors are out of scope)
- Kumite scoreboard component (`components/kumite_scoreboard.py`)
- Kata scoreboard component
