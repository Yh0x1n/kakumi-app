# Proposal: Re-styling — Dark Mode for Light-Themed Pages

## Skill Resolution

- status: paths-injected
- skills_loaded: caveman, python-pro, reflex-dev, frontend-design

## Proposal question round

The following questions surfaced during exploration and shape the proposal below. Review the assumptions in each section and correct them before we proceed to the spec phase.

| # | Question | Assumption in this proposal |
|---|----------|-----------------------------|
| 1 | **Dark bg color**: What specific dark background? | `#1a1a2e` (deep navy) as `DARK_BG_PAGE`, defined as a variable in `dark_tokens.py` so it's tweakable. |
| 2 | **Card containers on dark bg**: Should table cards and panels also go dark, or stay white for contrast? | Keep `CARD_BG = #ffffff` (white cards) on dark pages — highest contrast for data-heavy tables. |
| 3 | **Form inputs on dark bg**: Should inputs get a dark treatment, or stay light? | Keep inputs light (`bg=white`, `border=dark`) — acceptable UX pattern, avoids bloating the change. |
| 4 | **Sidebar**: Touch it or leave it? | Leave sidebar untouched (crimson tones, white icons) — it's already dark-styled and not part of the page-bg layer. |
| 5 | **Dark pages**: Visualizers, brackets, public display — change them? | No — they already have their own dark styling and are screen-facing (not operator-facing). |

## Intent

Invert light-themed operator-facing pages from light backgrounds (`#f5f5f5`, white cards) to dark backgrounds (`#1a1a2e` deep navy) with light text. This reduces eye strain for tournament operators who spend long sessions in the app, and gives the UI a more modern, professional feel — without touching the existing dark pages (public displays, visualizers) or the sidebar.

The change is **purely cosmetic** — no logic, state, or data-model changes.

## Scope

### In scope

1. **New token file**: `kakumi_app/styles/dark_tokens.py` — inverted colour palette imported from `tokens.py` structure.
2. **Page shell backgrounds**: 8 files importing `BG_PAGE` → swap to `DARK_BG_PAGE`.
3. **Page text colours**: Swap `TEXT_PRIMARY` (`#000000`) → light text (`#e0e0e0` or `#ffffff`), `TEXT_TERTIARY` (`#808080`) → muted light (`#a0a0a0`).
4. **Component token swaps**: `registry_crud.py`, `protected_layout.py`, `registries_items.py` — swap background and text tokens only.
5. **`kakumi_app.py`** main app shell: `bg=BG_PAGE` → `bg=DARK_BG_PAGE`.
6. **Hardcoded inline colours** in `pages/registries.py`: ~40 occurrences of `background_color="white"` and `border="1px solid black"` — selectively replace with token constants (light inputs stay, but input border changes from `black` to a dark-border token).
7. **`pages/results.py`**: Hardcoded `border="1px solid #e2e8f0"` → token constant.

### Out of scope

- Sidebar component (`components/sidebar.py`) — untouched.
- Dark display pages: `public_kata_display.py`, `public_kumite_display.py`, `kumite_scoreboard.py`, `kata_scoreboard.py`, `pages/public_display.py`.
- Buttons and interactive elements — `color_scheme` props are Reflex-internal, not token-based.
- `tokens.py` — kept as-is for rollback compatibility.
- `rxconfig.py` — no Reflex theme changes.
- Any `.css`, `.js`, `.ts`, `.html` files.
- Functional/logic changes of any kind.
- Database models, migrations, or state changes.

## Proposed solution

### 1. New file: `kakumi_app/styles/dark_tokens.py`

```python
"""Dark-mode colour tokens for re-styled operator pages."""

# ── Backgrounds ────────────────────────────────────
DARK_BG_PAGE = "#1a1a2e"        # replaces BG_PAGE (#f5f5f5)
DARK_BG_CARD = "#ffffff"        # keep white cards for data contrast
DARK_BG_CARD_ALT = "#16213e"    # replaces BG_CARD_ALT (#f0f0f0)
DARK_HEADER_BG = "#0f3460"      # replaces HEADER_BG (#f2f2f2)
DARK_BG_CODE_PREVIEW = "#1a1a2e"# replaces BG_CODE_PREVIEW (#f9f9f9)

# ── Text ───────────────────────────────────────────
DARK_TEXT_PRIMARY = "#e0e0e0"   # replaces TEXT_PRIMARY (#000000)
DARK_TEXT_SECONDARY = "#c0c0c0" # replaces TEXT_SECONDARY (#000000)
DARK_TEXT_TERTIARY = "#a0a0a0"  # replaces TEXT_TERTIARY (#808080)
DARK_MUTED_TEXT = "#b0a0a0"     # replaces MUTED_TEXT (#534342)

# ── Borders (toned down for dark bg) ────────────────
DARK_BORDER_SUBTLE = "#2a2a4a"  # replaces BORDER_SUBTLE (#ddd)
DARK_BORDER_LIGHT = "#3a3a5a"   # replaces BORDER_LIGHT (#aaaaaa)

# ── Brand (unchanged — keep for buttons/badges) ────
# BRAND_RED, BRAND_RED_HOVER, ACCENT_GOLD stay from tokens.py

# ── Inputs (light-on-dark pattern) ──────────────────
DARK_INPUT_BG = "#ffffff"       # keep light input fields
DARK_INPUT_BORDER = "#4a4a6a"   # subtle border on dark bg
DARK_INPUT_TEXT = "#000000"     # dark text inside light inputs
```

### 2. Targeted import swaps

Each file that currently does:

```python
from kakumi_app.styles.tokens import BG_PAGE, TEXT_PRIMARY, TEXT_TERTIARY
```

Changes to **one of two patterns** depending on the file:

**Pattern A — full page darkening** (registries, login, change_password, results, viewer, admin pages, exhibition):
```python
from kakumi_app.styles.tokens import (
    BRAND_RED, BRAND_RED_HOVER, BORDER_LIGHT, CARD_BG,
)
from kakumi_app.styles.dark_tokens import (
    DARK_BG_PAGE as BG_PAGE,
    DARK_TEXT_PRIMARY as TEXT_PRIMARY,
    DARK_TEXT_TERTIARY as TEXT_TERTIARY,
    DARK_MUTED_TEXT as MUTED_TEXT,
    DARK_BORDER_LIGHT as BORDER_LIGHT,
    DARK_BG_CARD as CARD_BG,
    DARK_BG_CARD_ALT as BG_CARD_ALT,
)
```

This way the rest of the file code needs **zero changes** — the token names stay the same, only the file they import from changes.

**Pattern B — components with mixed usage** (`registry_crud.py`):
```python
from kakumi_app.styles.dark_tokens import (
    DARK_BG_PAGE as BG_PAGE,
    DARK_TEXT_PRIMARY as TEXT_PRIMARY,
    DARK_MUTED_TEXT as MUTED_TEXT,
    DARK_BORDER_LIGHT as BORDER_LIGHT,
    DARK_BG_CARD as CARD_BG,
)
# BRAND_RED, BRAND_RED_HOVER stay imported from tokens.py
```

### 3. registries.py hardcoded inline fixes

`pages/registries.py` has ~40 spots with:
- `background_color="white"` on inputs → keep (light inputs on dark bg)
- `border="1px solid black"` on inputs → `border=f"1px solid {DARK_INPUT_BORDER}"`
- `background_color="white"` on `rx.select` `style` dicts → keep
- `"background_color": "white"` in `style` dicts → `DARK_BG_CARD` or keep if input

Import `DARK_INPUT_BORDER` from `dark_tokens` and apply selectively.

### 4. Hardcoded borders elsewhere

- `pages/results.py` line 30: `border="1px solid #e2e8f0"` → `border=f"1px solid {DARK_BORDER_SUBTLE}"`

## Architecture decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Token overriding via import alias** | Import dark tokens as the **same names** (e.g. `DARK_BG_PAGE as BG_PAGE`) | Zero changes to the rest of the file — pure import swap. Keeps diff small and reviewable. |
| **Separate file vs. conditional tokens** | New file `dark_tokens.py` | `tokens.py` stays untouched for rollback. No runtime branching — the dark variant is the only variant. |
| **Light inputs on dark bg** | Keep white inputs | Avoids re-styling input components (Reflex-internal). Users expect white input fields. Proven UX pattern. |
| **White cards on dark bg** | Keep white table cards | Data tables need high contrast for readability. Dark cards with dark text would harm scannability. |
| **Sidebar excluded** | No changes | Already dark-styled with crimson tones. Changing it would create a separate design scope. |
| **Dark display pages excluded** | No changes | They target a different audience (public screens, not operators). Their styling is intentional for projector/large-screen use. |

## Affected modules

| File | Change | Estimated lines |
|------|--------|-----------------|
| `kakumi_app/styles/dark_tokens.py` | **New file** — all dark tokens | ~45 |
| `kakumi_app/kakumi_app.py` | Import swap (`BG_PAGE` → dark) | ~2 |
| `kakumi_app/pages/registries.py` | Import swap + ~40 inline border/token refs | ~55 |
| `kakumi_app/pages/results.py` | Import swap + 1 hardcoded border | ~5 |
| `kakumi_app/pages/tournament.py` | Import swap | ~4 |
| `kakumi_app/pages/viewer.py` | Import swap | ~4 |
| `kakumi_app/pages/exhibition.py` | Import swap | ~4 |
| `kakumi_app/pages/auth/login.py` | Import swap | ~4 |
| `kakumi_app/pages/auth/change_password.py` | Import swap | ~4 |
| `kakumi_app/pages/admin/users_page.py` | Import swap | ~4 |
| `kakumi_app/pages/admin/teams_page.py` | Import swap | ~4 |
| `kakumi_app/pages/admin/export_page.py` | Import swap | ~4 |
| `kakumi_app/pages/admin/import_page.py` | Import swap | ~4 |
| `kakumi_app/components/registry_crud.py` | Import swap | ~10 |
| `kakumi_app/components/protected_layout.py` | Import swap | ~4 |
| `kakumi_app/components/registries_items.py` | Import swap (careful — uses `TEXT_WHITE` which stays) | ~2 |
| `kakumi_app/components/tables.py` | Import swap | ~2 |
| `kakumi_app/components/match_card.py` | Import swap | ~2 |
| **Total** | **18 files (1 new)** | **~160–200** |

## Excluded modules (no changes)

| File | Reason |
|------|--------|
| `components/sidebar.py` | Already dark-styled; outside scope |
| `components/public_kata_display.py` | Public display; stays black |
| `components/public_kumite_display.py` | Public display; stays black |
| `components/kumite_scoreboard.py` | Display-facing; stays as-is |
| `components/kata_scoreboard.py` | Display-facing; stays as-is |
| `pages/public_display.py` | Public display; stays black |
| `pages/admin/referees_page.py` | Uses `registry_page_shell` — inherits bg from `registry_crud.py` |
| `pages/admin/athletes_page.py` | Same as above — inherits bg |
| `styles/tokens.py` | **Deliberately kept** — rollback anchor |
| `rxconfig.py` | No theme config |

## Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Import alias confusion** — `DARK_BG_PAGE as BG_PAGE` then someone imports `BG_PAGE` from `tokens.py` and gets a different value | Visual inconsistency | Document the pattern clearly. The `dark_tokens.py` import block must be the **only** source of `BG_PAGE` in each file. Remove the old `tokens.py` import for swapped tokens. |
| **registries.py inline regressions** — missed `"white"` string or wrong border colour | One-off light-on-light or invisible border | Post-apply visual smoke test: visit every registries sub-page and confirm form fields, tables, and headings are readable. |
| **`rx.select` `style` dicts** — Reflex handles `style` keys differently; `background_color` in style dict may not override correctly | Select fields look wrong | Test each select component. If style dict doesn't respond, use explicit `background_color=` prop instead. |
| **Exhibition and viewer pages** — they have less traffic; a missed import could go unnoticed | Broken layout | Include smoke-test notes for each page in the spec phase. |
| **`CARD_BG` imported from both `tokens.py` and `dark_tokens.py`** — alias collision | Python `ImportError: cannot import name` | Each file must import each name from exactly one module. When aliasing as `CARD_BG`, drop the original import. |

## Rollback plan

1. **Primary**: `git revert` the entire commit — reverts all file changes cleanly.
2. **Fallback**: Delete `dark_tokens.py`, then revert imports in each file back to `from kakumi_app.styles.tokens import ...`.
3. **Verification**: `python -m pytest` passes; `reflex run` starts without import errors.
4. **No DB impact**: Zero database changes — no migration needed.
5. **Rollback window**: Safe to roll back at any time — no data dependence.

## Success criteria

1. All operator-facing pages render with dark background (`#1a1a2e`) and light text.
2. Input fields remain white/readable with dark borders.
3. Table cards (`registry_crud.py`) keep white backgrounds for data readability.
4. Sidebar and public display pages are visually unchanged.
5. No runtime import errors — `reflex run` starts cleanly.
6. `python -m pytest` passes all existing tests.
7. Visual smoke test passes on: `/registries/athletes`, `/login`, `/results`, `/tournament`, `/exhibition`, `/viewer`, admin pages.
