# UI Theme Specification — Dark Theme for Operator Pages

## Domain

`ui-theme`

## Purpose

Define the dark-theme behaviour for operator-facing pages in Kakumi App. The system relies on Reflex's built-in dark theme to render backgrounds and text without explicit light-mode override tokens. All explicit light-background and dark-text props are removed from operator pages, allowing the default dark theme to apply automatically. Hardcoded black borders on inputs and containers are changed to white borders for visibility on the dark background.

## Risk: Domain Inference

This proposal has no explicit "Capabilities" section. The domain `ui-theme` was inferred from the affected areas — colour tokens, page backgrounds, text colours, and component styling in operator-facing pages. If the expected domain differs, adjust the path accordingly.

## Requirements

### Requirement: No New Token File

The system MUST NOT introduce a new token file (e.g. `dark_tokens.py`) for the re-styling. The change MUST rely exclusively on removing or commenting out explicit light-mode token props so that Reflex's built-in dark theme takes effect.

#### Scenario: No dark_tokens.py created

- GIVEN the re-styling change is applied
- WHEN inspecting the `kakumi_app/styles/` directory
- THEN no file named `dark_tokens.py` SHALL exist
- AND all dark-background rendering MUST come from Reflex's built-in dark theme, not from custom token imports

### Requirement: Explicit Light Token Removal from Pages

All explicit light-mode token props (`bg=BG_PAGE`, `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `color=MUTED_TEXT`, `bg=CARD_BG`) MUST be removed from the following files:

- `kakumi_app/kakumi_app.py`
- `kakumi_app/pages/registries.py`
- `kakumi_app/pages/results.py`
- `kakumi_app/pages/tournament.py`
- `kakumi_app/pages/viewer.py`
- `kakumi_app/pages/exhibition.py`
- `kakumi_app/pages/auth/login.py`
- `kakumi_app/pages/auth/change_password.py`
- `kakumi_app/pages/admin/users_page.py`
- `kakumi_app/pages/admin/teams_page.py`
- `kakumi_app/pages/admin/export_page.py`
- `kakumi_app/pages/admin/import_page.py`
- `kakumi_app/components/registry_crud.py`
- `kakumi_app/components/protected_layout.py`
- `kakumi_app/components/registries_items.py`
- `kakumi_app/components/tables.py`
- `kakumi_app/components/match_card.py`
- `kakumi_app/components/date_calendar.py`

Removed props MAY be commented out with an explanatory comment (e.g. `# bg=BG_PAGE  # removed for dark theme`) or deleted entirely. After removal, components without explicit colour props MUST inherit the Reflex default dark-theme colours (dark background, light text).

#### Scenario: Page renders in dark mode

- GIVEN an operator navigates to any page listed above
- WHEN the page loads
- THEN the primary background MUST be dark (not `#f5f5f5` light grey)
- AND the page-level text MUST be light-coloured (not `#000000` black)
- AND the change MUST be achieved by removing explicit token props, not by adding new token values

### Requirement: Hardcoded White Background Removal

All hardcoded `bg="white"` and `background_color="white"` props MUST be removed from all pages listed in the Explicit Light Token Removal requirement. This includes:

- `pages/registries.py`: ~20 instances of `background_color="white"` on input fields, select containers, and text input wrappers
- `components/date_calendar.py`: `background_color="white"` in the calendar overlay and `style["background_color"] = "white"` in the trigger button

After removal, these containers MUST inherit the Reflex default dark-theme background.

#### Scenario: Registries form fields inherit dark background

- GIVEN the registries page loads
- WHEN inspecting the athlete registration form
- THEN none of the form field containers SHALL have `background_color="white"` or `bg="white"` explicitly set
- AND the form SHALL render with Reflex's default background colour on the dark theme

### Requirement: Border Color Adaptation

Where a `border="1px solid black"` was previously applied to a component that also had a white background removed, the border value MUST be changed to `border="1px solid white"` for visibility against the dark theme. This applies to:

- `pages/registries.py`: All `border="1px solid black"` occurrences on input fields (rx.input, rx.textarea) and select style dicts
- `components/date_calendar.py`: The `style["border"] = "1px solid black"` in the calendar popover trigger button

#### Scenario: Input border visible on dark background

- GIVEN a registries page with form inputs
- WHEN the page renders in dark theme
- THEN each input field SHALL display a visible white border (`1px solid white`)
- AND no input SHALL retain a `border="1px solid black"` prop

### Requirement: results.py Hardcoded Border Conversion

The hardcoded `border="1px solid #e2e8f0"` in `kakumi_app/pages/results.py` MUST be removed or changed so that the border is visible on the dark background. Since `#e2e8f0` is a very light grey, removing the explicit border lets Reflex's default theme apply a visible border, or the border MUST be changed to a colour visible on dark backgrounds.

#### Scenario: Results section border visible on dark background

- GIVEN a user navigates to the results page
- WHEN the section with the hardcoded border renders
- THEN the border SHALL NOT be `#e2e8f0` (invisible on dark)
- AND the border SHALL be visible against the dark background

### Requirement: tokens.py Unmodified

The file `kakumi_app/styles/tokens.py` MUST NOT be modified in any way. It remains as the canonical light-mode token definition and serves as a rollback anchor.

#### Scenario: tokens.py unchanged

- GIVEN the re-styling change is applied
- WHEN inspecting `kakumi_app/styles/tokens.py`
- THEN its contents SHALL be identical to the pre-change version
- AND all token values (`BG_PAGE`, `TEXT_PRIMARY`, `CARD_BG`, etc.) SHALL remain at their original light-mode values

### Requirement: Sidebar Unchanged

The sidebar component (`kakumi_app/components/sidebar.py`) MUST NOT be modified. This includes its token imports, text colours, background colours, and border styling. The sidebar MUST retain its current crimson/dark styling regardless of the page theme change.

#### Scenario: Sidebar retains original styling

- GIVEN any operator page renders
- WHEN the sidebar is visible
- THEN the sidebar's background, text colours, and branding SHALL be identical to the pre-change version
- AND the sidebar SHALL NOT inherit the page-level dark background change

### Requirement: Display Pages Unchanged

The following public display and visualizer pages MUST NOT be modified:

- `kakumi_app/components/public_kata_display.py`
- `kakumi_app/components/public_kumite_display.py`
- `kakumi_app/components/kumite_scoreboard.py`
- `kakumi_app/components/kata_scoreboard.py`
- `kakumi_app/pages/public_display.py`

These pages target spectator/projector use cases and MUST retain their existing dark styling.

#### Scenario: Public display pages visually identical

- GIVEN a public display page loads
- WHEN inspecting its rendered output
- THEN its background, text colours, and all styling SHALL be identical to the pre-change version

### Requirement: Buttons Unchanged

Button components and their `color_scheme` props MUST NOT be modified. All buttons (rx.button, rx.icon_button) across all pages SHALL retain their existing `color_scheme` values and styling.

#### Scenario: Button colours unchanged

- GIVEN a page with buttons renders
- WHEN inspecting any button component
- THEN its `color_scheme` prop SHALL be identical to the pre-change version
- AND its background colour SHALL remain as originally defined

### Requirement: No Functional Changes

The re-styling change MUST NOT alter any application logic, state management, database operations, data models, or API behaviour. The change is purely cosmetic and limited to colour token references and border values.

#### Scenario: Application logic unaffected

- GIVEN the re-styling change is applied
- WHEN executing all existing tests
- THEN all tests SHALL pass without modification
- AND all application features (registration, tournament lifecycle, results, authentication) SHALL behave identically to the pre-change version

### Requirement: Rollback via Git Revert

The change MUST be structured as a single atomic commit that can be fully reverted via `git revert` without side effects. No database migrations, data transformations, or irreversible modifications SHALL be included.

#### Scenario: Clean git revert

- GIVEN the re-styling commit is applied
- WHEN a developer runs `git revert <commit-hash>`
- THEN the revert SHALL complete without conflicts
- AND all pages SHALL return to their original light-mode appearance
- AND all tests SHALL continue to pass

## Affected Files Summary

| File | Operation |
|------|-----------|
| `kakumi_app/pages/registries.py` | Remove `color=TEXT_PRIMARY`, `color=MUTED_TEXT`; remove ~20 `background_color="white"`; change ~20 `border="1px solid black"` to `border="1px solid white"`; remove unused `MUTED_TEXT`, `TEXT_PRIMARY` imports |
| `kakumi_app/kakumi_app.py` | Remove `color=TEXT_PRIMARY`, `background_color=BG_PAGE`; remove `BG_PAGE`, `TEXT_PRIMARY` from import |
| `kakumi_app/pages/tournament.py` | Remove all `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`; remove `TEXT_PRIMARY`, `TEXT_TERTIARY` from import |
| `kakumi_app/pages/viewer.py` | Remove all `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; remove `BG_PAGE`, `TEXT_PRIMARY`, `TEXT_TERTIARY` from import |
| `kakumi_app/pages/exhibition.py` | Remove `color=TEXT_PRIMARY`, `background_color=BG_PAGE`; remove `BG_PAGE`, `TEXT_PRIMARY` from import |
| `kakumi_app/pages/results.py` | Remove or adapt `border="1px solid #e2e8f0"` |
| `kakumi_app/pages/auth/login.py` | Remove `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; remove `BG_PAGE`, `TEXT_TERTIARY`, `TEXT_PRIMARY` from import |
| `kakumi_app/pages/auth/change_password.py` | Remove `color=TEXT_TERTIARY`, `bg=CARD_BG`, `background_color=BG_PAGE`; remove `BG_PAGE`, `CARD_BG`, `TEXT_TERTIARY` from import |
| `kakumi_app/pages/admin/users_page.py` | Remove `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; update import |
| `kakumi_app/pages/admin/teams_page.py` | Remove `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; update import |
| `kakumi_app/pages/admin/export_page.py` | Remove `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; update import |
| `kakumi_app/pages/admin/import_page.py` | Remove `color=TEXT_PRIMARY`, `color=TEXT_TERTIARY`; update import |
| `kakumi_app/components/registry_crud.py` | Remove `color=TEXT_PRIMARY`, `color=MUTED_TEXT`, `background_color=BG_PAGE`, `background_color=CARD_BG`; update import |
| `kakumi_app/components/protected_layout.py` | Remove `color=TEXT_TERTIARY`, `background_color=BG_PAGE`; update import |
| `kakumi_app/components/tables.py` | Remove `color=TEXT_TERTIARY`; update import |
| `kakumi_app/components/match_card.py` | Remove `color=TEXT_TERTIARY`; update import |
| `kakumi_app/components/date_calendar.py` | Remove `background_color="white"`; change `border="1px solid black"` in style dict; remove `border="1px solid #ddd"` or adapt to dark-visible border |
| `kakumi_app/styles/tokens.py` | **No changes** |

## Excluded Files (Verified)

| File | Reason for Exclusion |
|------|---------------------|
| `kakumi_app/styles/tokens.py` | Rollback anchor — must remain unchanged |
| `kakumi_app/components/sidebar.py` | Already dark-styled, out of scope |
| `kakumi_app/components/public_kata_display.py` | Public display, out of scope |
| `kakumi_app/components/public_kumite_display.py` | Public display, out of scope |
| `kakumi_app/components/kumite_scoreboard.py` | Public display, out of scope |
| `kakumi_app/components/kata_scoreboard.py` | Public display, out of scope |
| `kakumi_app/pages/public_display.py` | Public display, out of scope |
| `kakumi_app/pages/admin/referees_page.py` | Inherits bg from registry_crud shell |
| `kakumi_app/pages/admin/athletes_page.py` | Inherits bg from registry_crud shell |
| `rxconfig.py` | No theme config changes |

## Technical Constraints

- All changes MUST be limited to Python files (`.py`). No `.css`, `.js`, `.ts`, `.html`, or `.md` files SHALL be created or modified.
- The change MUST NOT introduce any new Python dependencies or third-party packages.
- The change MUST NOT alter any database schemas, migrations, or data-access logic.
- Token removal MAY use commenting (`# ...`) instead of full deletion to aid diff readability, provided the commented prop has no effect at runtime.
- The `reflex run` development server MUST start without import errors after the change.
