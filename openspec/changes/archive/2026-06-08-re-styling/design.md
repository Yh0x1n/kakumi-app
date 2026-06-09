# SDD Design: Re-styling (Dark Theme for Operator Pages)

## Executive Summary

Subtractive re-styling of 17 operator-facing Python files: remove explicit light-theme colour props (`bg=BG_PAGE`, `color=TEXT_PRIMARY`, `background_color="white"`, etc.) and let Reflex's built-in dark theme supply background/text colours. Brand-only imports (`BRAND_RED`, `BRAND_RED_HOVER`, `ACCENT_GOLD`, `TEXT_WHITE`) survive. Hardcoded `border="1px solid black"` on white-bg inputs is adapted to `border="1px solid white"` for visibility on dark pages. No `dark_tokens.py` is created — this is purely subtractive.

**Estimated changed lines:** ~200 across 17 files (0 new files, 0 deletions).

---

## ADR-1: Subtractive over additive

| Field | Value |
|-------|-------|
| **Decision** | Remove explicit light colour props entirely rather than aliasing dark tokens over them |
| **Rationale** | Reflex dark theme handles bg/text/card defaults automatically. Removing props is fewer lines changed, zero token duplication, and easier rollback. Proposal's `dark_tokens.py`+import-alias approach is unnecessary. |
| **Trade-off** | Pages lose fine-grained colour control — they rely on Reflex's built-in dark palette. Cards that were `CARD_BG=#ffffff` become Reflex's dark card bg. This is acceptable per spec requirement. |

## ADR-2: White-input border adaptation

| Field | Value |
|-------|-------|
| **Decision** | `border="1px solid black"` → `border="1px solid white"` only where the component had `background_color="white"` |
| **Rationale** | White background is removed (dark theme supplies input bg), but the black border would be invisible on dark bg. White border ensures the input boundary is visible. |
| **Trade-off** | Input borders are thicker/more visible than Reflex defaults. Acceptable for form clarity. |

## ADR-3: Hardcoded light-gray borders left unchanged

| Field | Value |
|-------|-------|
| **Decision** | `border="1px solid #ddd"` in `users_page.py` and `teams_page.py` is left as-is |
| **Rationale** | Spec requirement explicitly addresses only `1px solid black` → `1px solid white`. `#ddd` borders will be very faint on dark bg but are outside spec scope. |
| **Trade-off** | These cards may appear borderless on dark theme. Acceptable for now; can be revisited if visual smoke test flags them. |

## ADR-4: `date_calendar.py` partial adaptation

| Field | Value |
|-------|-------|
| **Decision** | Change the trigger display's `border="1px solid black"` → `"1px solid white"` and remove `background_color="white"` from the trigger style dict. Leave the popover overlay (`background_color="white"`, `border="1px solid #ddd"`) untouched. |
| **Rationale** | The trigger is visible on the dark registries page and needs border adaptation. The popover overlay is a white card floating above content — its own bg/border are independent of the page theme. |
| **Trade-off** | Slight visual disconnect between trigger (dark-themed) and popover (light card). Acceptable; popovers are ephemeral. |

---

## Data Flow Diagram

```
User request → Reflex Router → Page Component (rx.box/vstack)
                                    │
                                    ├── bg=BG_PAGE          ✗ REMOVED  → Reflex dark bg
                                    ├── color=TEXT_PRIMARY   ✗ REMOVED  → Reflex light text
                                    ├── color=TEXT_TERTIARY  ✗ REMOVED  → Reflex muted text
                                    ├── border="1px solid black"  → "1px solid white"
                                    ├── background_color="white"  ✗ REMOVED
                                    └── <child components>
                                         │
                                         ├── registry_crud  → brand tokens KEPT, others REMOVED
                                         ├── date_calendar  → trigger border adapted
                                         └── registries_items → UNCHANGED (brand only)
```

**No state, no database, no logic changes.** Pure cosmetic — every change is in component props or import lines.

---

## File-by-File Plan

### 1. `kakumi_app/styles/tokens.py` — NO CHANGES
**Status:** Untouched (rollback anchor)

---

### 2. `kakumi_app/kakumi_app.py` — Remove token imports + hardcoded colors
**Current imports (line 45):**
```python
from .styles.tokens import BG_PAGE, HOVER_GRAY, TEXT_PRIMARY
```

**Changes:**
| Line(s) | Current | After |
|---------|---------|-------|
| 45 | `from .styles.tokens import BG_PAGE, HOVER_GRAY, TEXT_PRIMARY` | Remove entire import line (no brand tokens to keep) |
| 81 | `color=TEXT_PRIMARY,` (heading) | Remove prop entirely |
| 99 | `color=TEXT_PRIMARY,` (card text) | Remove prop entirely |
| 109 | `border_color="black",` (card) | Remove prop entirely |
| 110 | `"background-color": HOVER_GRAY,` (hover style) | Remove entire `,_hover` dict or replace with empty dict |
| 112 | `background_color=BG_PAGE,` (outer box) | Remove prop entirely |

**Pattern:** All three tokens are light-theme only. `HOVER_GRAY` (`#e0e0e0`) is a hover highlight on light bg — irrelevant in dark theme. `border_color="black"` on `rx.card` is a light-theme default.

**Border ruling:** `border_color="black"` is not `1px solid black` on a white-bg input — it's a card border on a card whose bg is not explicitly set. Remove and let Reflex theme handle card borders.

**Edge case:** The welcome page's 4 card grid loses explicit hover highlight. Cards will use Reflex's default card hover behaviour.

---

### 3. `kakumi_app/pages/registries.py` — Heavy edits (~55 lines changed)
**Current imports (line 24):**
```python
from kakumi_app.styles.tokens import MUTED_TEXT, TEXT_PRIMARY
```

**Changes:**
| Category | Count | Action |
|----------|-------|--------|
| Import line | 1 | Remove entire `from kakumi_app.styles.tokens import MUTED_TEXT, TEXT_PRIMARY` |
| `color=TEXT_PRIMARY` | ~30 (headings, table cells, labels, checkboxes) | Remove each `color=TEXT_PRIMARY` prop |
| `color=MUTED_TEXT` | 1 (registries intro text) | Remove `color=MUTED_TEXT` prop |
| `background_color="white"` | ~14 (rx.input, rx.select style dicts) | Remove each `background_color="white"` entry |
| `border="1px solid black"` on rx.input | ~10 | Change to `border="1px solid white"` |
| `"border": "1px solid black"` in style dicts | ~4 (rx.select) | Change to `"border": "1px solid white"` |
| `"background_color": "black"` (gender select, line 120) | 1 | **UNCHANGED** — not a white-bg component |

**Specific style-dict transformations:**

Input pattern (direct props):
```python
# BEFORE
rx.input(..., border="1px solid black", background_color="white", color=TEXT_PRIMARY)
# AFTER
rx.input(..., border="1px solid white")  # bg and color removed
```

Select pattern (style dict):
```python
# BEFORE
style={"border": "1px solid black", "color": TEXT_PRIMARY, "background_color": "white"}
# AFTER
style={"border": "1px solid white"}  # color and background_color removed
```

**Note:** The gender select's `"background_color": "black"` (line 120) stays — it's an existing dark-bg select with black text (`TEXT_PRIMARY` = `#000000`). This pre-existing readability issue is outside the scope of this re-styling.

---

### 4. `kakumi_app/pages/results.py` — Remove tokens + adapt border
**Current imports (line 8):**
```python
from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE
```

**Changes:**
| Line(s) | Current | After |
|---------|---------|-------|
| 8 | Import `TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE` | Remove import entirely |
| 15, 57, 154, 176, 225, 231, 243, 321, 404, 409, 431, 453 | `color=TEXT_PRIMARY` (headings) | Remove each `color=TEXT_PRIMARY` |
| 16, 26, 60, 65, 70, 101, 102, 165, 248, 253, 345 | `color=TEXT_TERTIARY` (subtitles, breadcrumbs, stats) | Remove each `color=TEXT_TERTIARY` |
| 31 | `background_color=BG_PAGE` (status badge) | Remove `background_color=BG_PAGE` |
| 30 | `border="1px solid #e2e8f0"` | Change to `border="1px solid white"` |

---

### 5. `kakumi_app/pages/tournament.py` — Remove text tokens
**Current imports (line 6):**
```python
from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY
```

**Changes:** Remove import line. Remove all ~35 occurrences of `color=TEXT_PRIMARY` and ~6 occurrences of `color=TEXT_TERTIARY`.

**No borders, no hardcoded colors** — pure text-colour removal across headings, table cells, and paragraph text.

---

### 6. `kakumi_app/pages/viewer.py` — Remove bg + text tokens
**Current imports (line 9):**
```python
from kakumi_app.styles.tokens import BG_CARD_ALT, BG_PAGE, TEXT_PRIMARY, TEXT_TERTIARY
```

**Changes:**
| Line(s) | Current | After |
|---------|---------|-------|
| 9 | Import all four | Remove entire import line |
| 64 | `color=TEXT_TERTIARY` | Remove prop |
| 79, 111, 147, 165, 173 | `background_color=BG_PAGE` | Remove each `background_color=BG_PAGE` |
| 102 | `color=TEXT_PRIMARY` (dashboard heading) | Remove prop |
| 121 | `background_color=BG_CARD_ALT` | Remove prop |
| 162 | `color=TEXT_TERTIARY` (bracket placeholder) | Remove prop |

---

### 7. `kakumi_app/pages/exhibition.py` — Remove bg + text tokens
**Current imports (line 15):**
```python
from ..styles.tokens import BG_PAGE, TEXT_PRIMARY
```

**Changes:**
| Line(s) | Current | After |
|---------|---------|-------|
| 15 | Import both | Remove entire import line |
| 53, 60 | `color=TEXT_PRIMARY` | Remove both props |
| 70, 73 | `background_color=BG_PAGE` | Remove both props |

---

### 8. `kakumi_app/pages/auth/login.py` — Remove tokens
**Current imports (line 9):**
```python
from kakumi_app.styles.tokens import BG_PAGE, TEXT_TERTIARY, TEXT_PRIMARY
```

**Changes:** Remove import. Remove `color=TEXT_PRIMARY` (2), `color=TEXT_TERTIARY` (1), `background_color=BG_PAGE` (1).

---

### 9. `kakumi_app/pages/auth/change_password.py` — Remove tokens
**Current imports (line 10):**
```python
from kakumi_app.styles.tokens import BG_PAGE, CARD_BG, TEXT_TERTIARY
```

**Changes:** Remove import. Remove `color=TEXT_TERTIARY` (1), `bg=CARD_BG` (1), `background_color=BG_PAGE` (1).

---

### 10–12. Admin pages — Remove token imports

#### `pages/admin/users_page.py`
**Import (line 10):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE`
- Remove import. Remove `color=TEXT_PRIMARY` (~20, table cells + headings), `color=TEXT_TERTIARY` (3), `background_color=BG_PAGE` (1).
- `border="1px solid #ddd"` (line 249) — UNCHANGED (per ADR-3).
- `color="red"` (line 303) — UNCHANGED (semantic error colour).

#### `pages/admin/teams_page.py`
**Import (line 10):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE`
- Same pattern as users_page.py. Remove import, remove all token usages.
- `border="1px solid #ddd"` (line 158) — UNCHANGED.
- `color="red"` (line 212) — UNCHANGED.

#### `pages/admin/export_page.py`
**Import (lines 8–15):** `BG_CODE_PREVIEW, BORDER_LIGHT, BORDER_SUBTLE, TEXT_TERTIARY, BG_PAGE, TEXT_PRIMARY`
- Remove entire import. Remove all 6 token usages across the file.
- `background_color=BG_CODE_PREVIEW` (line 85) — removed.

#### `pages/admin/import_page.py`
**Import (line 5):** `TEXT_PRIMARY, TEXT_TERTIARY`
- Remove import. Remove `color=TEXT_PRIMARY` (1) and `color=TEXT_TERTIARY` (1).

---

### 13. `components/registry_crud.py` — Selective brand-keep
**Current imports (lines 10–19):**
```python
from kakumi_app.styles.tokens import (
    BG_PAGE,
    BORDER_LIGHT,
    BRAND_RED,        # ← KEEP
    BRAND_RED_HOVER,  # ← KEEP
    CARD_BG,
    HEADER_BG,
    MUTED_TEXT,
    TEXT_PRIMARY,
)
```

**Changes:**

| Token | Action | Reason |
|-------|--------|--------|
| `BG_PAGE` | Remove | Light-theme bg |
| `BORDER_LIGHT` | Remove | Light-theme border colour — used in borders that change to `"1px solid white"` |
| `BRAND_RED` | **KEEP** | Brand colour for buttons/badges |
| `BRAND_RED_HOVER` | **KEEP** | Brand hover colour |
| `CARD_BG` | Remove | Light-theme card bg |
| `HEADER_BG` | Remove | Light-theme header bg |
| `MUTED_TEXT` | Remove | Light-theme text colour |
| `TEXT_PRIMARY` | Remove | Light-theme text colour |

**Hardcoded colour removals:**
| Line | Current | After |
|------|---------|-------|
| 60 | `color="#1a1c1c"` (heading in `registry_actions_header`) | Remove `color="#1a1c1c"` |
| 252 | `background_color="#e8e8e8"` (empty-state icon container) | Remove `background_color="#e8e8e8"` |

**Border adaptations:**
| Line(s) | Current | After |
|---------|---------|-------|
| 137 | `border=f"1.5px dashed {BORDER_LIGHT}"` (upload zone) | `border="1.5px dashed white"` |
| 176 | `border=f"1px solid {BORDER_LIGHT}"` (import panel card) | `border="1px solid white"` |
| 204 | `border=f"1px solid {BORDER_LIGHT}"` (search input) | `border="1px solid white"` |
| 294 | `border_bottom=f"1px solid {BORDER_LIGHT}"` (filter row) | `border_bottom="1px solid white"` |
| 335 | `border_top=f"1px solid {BORDER_LIGHT}"` (pagination footer) | `border_top="1px solid white"` |
| 341 | `border=f"1px solid {BORDER_LIGHT}"` (table card) | `border="1px solid white"` |

**Other prop removals:**
- `background_color=BG_PAGE` (lines 41, 135, 202) — Remove each
- `color=TEXT_PRIMARY` (lines 116, 141, 196, 204, 257, 257) — Remove each
- `color=MUTED_TEXT` (lines 61, 64, 119, 125, 218, 258, 291, 313) — Remove each
- `background_color=CARD_BG` (lines 175, 341) — Remove each
- `background_color=HEADER_BG` (line 292) — Remove

---

### 14. `components/protected_layout.py` — Remove tokens
**Current imports (line 10):**
```python
from kakumi_app.styles.tokens import TEXT_TERTIARY, BG_PAGE
```

**Changes:** Remove import. Remove `background_color=BG_PAGE` (line 45), `color=TEXT_TERTIARY` (line 60).

---

### 15. `components/tables.py` — Remove token
**Current import (line 8):**
```python
from kakumi_app.styles.tokens import TEXT_TERTIARY
```

**Changes:** Remove import. Remove `color=TEXT_TERTIARY` (line 14, placeholder text).

---

### 16. `components/match_card.py` — Remove token
**Current import (line 7):**
```python
from kakumi_app.styles.tokens import TEXT_TERTIARY
```

**Changes:** Remove import. Remove `color=TEXT_TERTIARY` (line 31, "vs" separator).

---

### 17. `components/registries_items.py` — NO CHANGES
**Current imports:**
```python
from kakumi_app.styles.tokens import BRAND_RED_HOVER, BRAND_RED_HOVER_LIGHT, TEXT_WHITE
```

All three are brand/functional tokens (red backgrounds, white text on red). No light-theme tokens present. **Untouched.**

---

### 18. `components/date_calendar.py` — Partial border adaptation (dependency of registries.py)
**No token imports to remove** (no light-theme tokens imported). Hardcoded colours only.

**Changes:**
| Line | Current | After | Rationale |
|------|---------|-------|-----------|
| 132 | `background_color="white"` (popover overlay) | **UNCHANGED** | White popup on dark bg — deliberate contrast |
| 133 | `border="1px solid #ddd"` (popover overlay) | **UNCHANGED** | Subtle border on white popup is fine |
| 151 | `color="black"` (date display text) | **UNCHANGED** | On white popup, black text is correct |
| 162 | `"border": "1px solid black"` (trigger style dict) | `"border": "1px solid white"` | Trigger sits on dark registries page |
| 163 | `"background_color": "white"` (trigger style dict) | Remove entry | Let Reflex dark theme style the trigger |
| 153 | `color="#999"` (placeholder text) | **UNCHANGED** | Placeholder inside white popup |

---

## Token Survival Matrix

| Token | `tokens.py` | Pages using it | Status |
|-------|-------------|----------------|--------|
| `BRAND_RED` | Yes | `registry_crud.py` | ✅ KEPT |
| `BRAND_RED_HOVER` | Yes | `registry_crud.py`, `registries_items.py` | ✅ KEPT |
| `BRAND_RED_HOVER_LIGHT` | Yes | `registries_items.py` | ✅ KEPT |
| `ACCENT_GOLD` | Yes | `sidebar.py` (out of scope) | ✅ UNTOUCHED |
| `TEXT_WHITE` | Yes | `registries_items.py`, `sidebar.py` | ✅ KEPT |
| `BG_PAGE` | Yes | 12 files | ❌ Removed from all |
| `BG_CARD_ALT` | Yes | `viewer.py` | ❌ Removed |
| `BG_CODE_PREVIEW` | Yes | `export_page.py` | ❌ Removed |
| `CARD_BG` | Yes | `change_password.py`, `registry_crud.py` | ❌ Removed |
| `HEADER_BG` | Yes | `registry_crud.py` | ❌ Removed |
| `TEXT_PRIMARY` | Yes | 13 files | ❌ Removed from all |
| `TEXT_SECONDARY` | Yes | (unused in scope) | ❌ Unused |
| `TEXT_TERTIARY` | Yes | 9 files | ❌ Removed from all |
| `MUTED_TEXT` | Yes | `registries.py`, `registry_crud.py` | ❌ Removed |
| `HOVER_GRAY` | Yes | `kakumi_app.py` | ❌ Removed |
| `BORDER_LIGHT` | Yes | `registry_crud.py`, `export_page.py` | ❌ Removed |
| `BORDER_SUBTLE` | Yes | `export_page.py` | ❌ Removed |

---

## Affected Files Summary

| # | File | Import Change | Prop Removals | Border Adaptation | Est. Lines |
|---|------|---------------|---------------|-------------------|------------|
| 1 | `kakumi_app/styles/tokens.py` | — | — | — | 0 |
| 2 | `kakumi_app/kakumi_app.py` | Remove 3 tokens | 5 prop removals | Remove `border_color="black"` | 5 |
| 3 | `kakumi_app/pages/registries.py` | Remove 2 tokens | ~45 prop removals | 14 borders → white | 55 |
| 4 | `kakumi_app/pages/results.py` | Remove 3 tokens | ~20 prop removals | 1 border → white | 8 |
| 5 | `kakumi_app/pages/tournament.py` | Remove 2 tokens | ~41 prop removals | — | 12 |
| 6 | `kakumi_app/pages/viewer.py` | Remove 4 tokens | ~9 prop removals | — | 8 |
| 7 | `kakumi_app/pages/exhibition.py` | Remove 2 tokens | 4 prop removals | — | 4 |
| 8 | `kakumi_app/pages/auth/login.py` | Remove 3 tokens | 4 prop removals | — | 4 |
| 9 | `kakumi_app/pages/auth/change_password.py` | Remove 3 tokens | 3 prop removals | — | 4 |
| 10 | `kakumi_app/pages/admin/users_page.py` | Remove 3 tokens | ~24 prop removals | — | 8 |
| 11 | `kakumi_app/pages/admin/teams_page.py` | Remove 3 tokens | ~6 prop removals | — | 8 |
| 12 | `kakumi_app/pages/admin/export_page.py` | Remove 6 tokens | ~6 prop removals | — | 6 |
| 13 | `kakumi_app/pages/admin/import_page.py` | Remove 2 tokens | 2 prop removals | — | 3 |
| 14 | `kakumi_app/components/registry_crud.py` | Keep 2, remove 6 | ~30 prop removals | 5 borders → white | 35 |
| 15 | `kakumi_app/components/protected_layout.py` | Remove 2 tokens | 2 prop removals | — | 3 |
| 16 | `kakumi_app/components/tables.py` | Remove 1 token | 1 prop removal | — | 2 |
| 17 | `kakumi_app/components/match_card.py` | Remove 1 token | 1 prop removal | — | 2 |
| 18 | `kakumi_app/components/registries_items.py` | — | — | — | 0 |
| 19 | `kakumi_app/components/date_calendar.py` | — | 1 prop removal | 1 border → white | 2 |
| **Total** | **19 files** | | | | **~170** |

---

## Rollback Strategy

**Primary:** `git revert HEAD` — all changes in one commit, clean revert.

**Fallback (per-file revert):**
```bash
git checkout HEAD -- kakumi_app/kakumi_app.py
git checkout HEAD -- kakumi_app/pages/registries.py
# ... repeat for each file
git checkout HEAD -- kakumi_app/styles/tokens.py  # no-op check
```

**Verification:**
```bash
python -m pytest -v                     # All tests pass
reflex run --loglevel debug 2>&1        # No import errors at startup
python -c "from kakumi_app.styles.tokens import BRAND_RED, BRAND_RED_HOVER, ACCENT_GOLD, TEXT_WHITE; print('brand tokens OK')"
```

**Rollback window:** Any time — zero database state, zero logic changes, zero data dependence.

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **`registries.py` missed border** — one of 14 `border="1px solid black"` not caught | Invisible input on dark bg | Post-apply visual smoke test of every registries form |
| **`registry_crud.py` style-dict `border`** — style dict keys may behave differently from direct `border=` props | Border not applied | Test `registry_import_panel` and `registry_table_card` explicitly |
| **Sidebar style bleed** — if sidebar inherits page-level bg change | Sidebar bg shifts | Sidebar is in a separate `rx.hstack` sibling — its own crimson bg is unaffected |
| **`#ddd` borders in admin pages** — very faint on dark bg | Cards look borderless | ADR-3 accepts this; revisit if smoke test shows issue |
| **Reflex dark theme not active** — if `rxconfig.py` has no `theme=dark` | Removing explicit bg reveals white default | Must ensure `rxconfig.py` has `dark` theme mode (separate task; not part of this design) |
| **`date_calendar.py` popover** — white popover on dark bg may look disconnected | Visual seam | Acceptable per ADR-4; popover is ephemeral overlay |

---

## Delivery Order (Recommended Apply Order)

1. **`styles/tokens.py`** — no-op, verify it's clean
2. **Simple files** (import-only, no borders): `tables.py`, `match_card.py`, `protected_layout.py`, `import_page.py`, `login.py`, `change_password.py`
3. **Medium files** (import + prop removals, no borders): `tournament.py`, `viewer.py`, `exhibition.py`, `users_page.py`, `teams_page.py`, `export_page.py`
4. **Complex files** (import + borders): `registries.py`, `results.py`, `registry_crud.py`
5. **Root file**: `kakumi_app.py`
6. **Dependency file**: `date_calendar.py`
7. **Verify**: `python -m pytest` + `reflex run` smoke test

---

## Verification Checklist

- [ ] `python -m pytest` passes (all existing tests)
- [ ] `reflex run` starts without import errors
- [ ] `/registries/athletes` — all form inputs have visible borders, headings are light text on dark bg
- [ ] `/login` — centred card on dark bg, text readable
- [ ] `/results` — status badge has white border, headings readable
- [ ] `/tournament` — all headings and table cells readable
- [ ] `/exhibition` — menu page header readable
- [ ] `/viewer` — login page and dashboard readable
- [ ] Admin pages (`/admin/users`, `/admin/teams`, `/admin/export`, `/admin/import`) — readable
- [ ] Sidebar — visually unchanged (crimson bg, white icons/text)
- [ ] Public display pages — visually unchanged
- [ ] `kakumi_app/styles/tokens.py` — zero modifications
