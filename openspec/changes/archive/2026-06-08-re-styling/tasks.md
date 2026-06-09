# SDD Tasks: Re-styling (Dark Theme for Operator Pages)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~170–200 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Low
```

---

## Execution Strategy

**Approach:** Subtractive — remove explicit light-theme colour props (`bg=BG_PAGE`, `color=TEXT_PRIMARY`, `background_color="white"`, etc.) from 17 operator-facing files. Let Reflex's built-in dark theme (`appearance="dark"`) supply background/text colours. Brand-only tokens (`BRAND_RED`, `BRAND_RED_HOVER`, `ACCENT_GOLD`, `TEXT_WHITE`) survive. Hardcoded `border="1px solid black"` on white-bg inputs is adapted to `border="1px solid white"`. No `dark_tokens.py` is created.

**TDD Pattern:** Each task follows RED → GREEN → EVIDENCE cycles:
- **RED**: Run the canonical command that must pass (pytest suite, reflex import check). Failure before changes proves the baseline.
- **GREEN**: Apply the file edits described in the task.
- **EVIDENCE**: Re-run the same command, capture output. For visual-only changes, produce a specific verification statement.

**Delivery order:** Lowest risk first. Simple import-only files before complex border-adaptation files.

---

## Prerequisite Check

Before any task, confirm the working tree is clean:
```bash
cd /var/home/yhoxr/Documentos/kakumi-app
git status --short
```
If dirty, commit or stash first. All changes in this PR must be revertible via `git revert HEAD`.

---

## Task 0 — RED: Baseline test suite green

### Description
Establish that the existing test suite passes cleanly before any styling changes.

### Action
```bash
python -m pytest tests/ -v 2>&1
```

### Success criteria
- Exit code 0
- All tests pass (no failures, no errors)

### Evidence recording
Save output to `openspec/changes/re-styling/evidence/task-00-baseline-pytest.txt`.

### Fallback
If baseline fails, diagnose and fix before proceeding. Do not start cosmetic changes on a broken suite.

---

## Task 1 — GREEN: Enable Reflex dark theme in `kakumi_app.py`

### Description
The subtractive approach relies on Reflex's built-in dark mode. Without it, removing explicit `background_color` / `color` props leaves white-on-white layouts. Investigate and apply the minimal Reflex 0.8 dark-theme hook.

### Investigation target
Read Reflex 0.8.28 docs or `rx.App` signature to determine the correct API:

```bash
python -c "import reflex as rx; help(rx.App.__init__)" 2>&1 | head -20
python -c "import reflex as rx; help(rx.theme)" 2>&1 | head -40
```

Likely approach (Reflex 0.8.x):
```python
# kakumi_app/kakumi_app.py
app = rx.App(
    theme=rx.theme(appearance="dark", has_background=True),
)
```

### Action
Edit `kakumi_app/kakumi_app.py` line 123:
- Current: `app = rx.App()`
- After: `app = rx.App(theme=rx.theme(appearance="dark", has_background=True))`

### Verification (GREEN)
```bash
python -m pytest tests/ -v 2>&1   # still green
reflex run --loglevel debug 2>&1 | head -5   # startup succeeds
```

### Evidence recording
Save evidence to `openspec/changes/re-styling/evidence/task-01-dark-theme.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/kakumi_app.py
```

---

## Task 2 — GREEN: Simple component files (tokens import removal only)

### Description
Remove token imports and their single-use props from three leaf components. No border adaptation — these use `TEXT_TERTIARY` only.

### Files to modify

#### 2a. `kakumi_app/components/tables.py`
| Current | After |
|---------|-------|
| Line 8: `from kakumi_app.styles.tokens import TEXT_TERTIARY` | Remove entire line |
| Line 14: `color=TEXT_TERTIARY,` (placeholder text) | Remove `color=TEXT_TERTIARY,` |

#### 2b. `kakumi_app/components/match_card.py`
| Current | After |
|---------|-------|
| Line 7: `from kakumi_app.styles.tokens import TEXT_TERTIARY` | Remove entire line |
| Line 31: `color=TEXT_TERTIARY,` ("vs" separator) | Remove `color=TEXT_TERTIARY,` |

#### 2c. `kakumi_app/components/protected_layout.py`
| Current | After |
|---------|-------|
| Line 10: `from kakumi_app.styles.tokens import TEXT_TERTIARY, BG_PAGE` | Remove entire line |
| Line 45: `background_color=BG_PAGE,` | Remove prop |
| Line 60: `color=TEXT_TERTIARY,` | Remove prop |

### Verification (RED → GREEN)
```bash
# RED: confirm current state
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5

# GREEN: apply edits, then verify
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "from kakumi_app.components import tables, match_card, protected_layout; print('imports OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-02-simple-components.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/components/tables.py kakumi_app/components/match_card.py kakumi_app/components/protected_layout.py
```

---

## Task 3 — GREEN: Auth and import-only admin pages

### Description
Remove token imports and usages from small auth/admin pages with no border adaptations.

### Files to modify

#### 3a. `kakumi_app/pages/auth/login.py`
**Import (line 9):** `from kakumi_app.styles.tokens import BG_PAGE, TEXT_TERTIARY, TEXT_PRIMARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_PRIMARY,` (2 occurrences)
- `color=TEXT_TERTIARY,` (1 occurrence)
- `background_color=BG_PAGE,` (1 occurrence)

#### 3b. `kakumi_app/pages/auth/change_password.py`
**Import (line 10):** `from kakumi_app.styles.tokens import BG_PAGE, CARD_BG, TEXT_TERTIARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_TERTIARY,` (1 occurrence)
- `bg=CARD_BG,` (1 occurrence)
- `background_color=BG_PAGE,` (1 occurrence)

#### 3c. `kakumi_app/pages/admin/import_page.py`
**Import (line 5):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_PRIMARY,` (1 occurrence)
- `color=TEXT_TERTIARY,` (1 occurrence)

#### 3d. `kakumi_app/pages/admin/export_page.py`
**Import (lines 8–15):** `from kakumi_app.styles.tokens import (BG_CODE_PREVIEW, BORDER_LIGHT, BORDER_SUBTLE, TEXT_TERTIARY, BG_PAGE, TEXT_PRIMARY)`
→ Remove entire import block.

Prop removals (6 total):
- All `color=TEXT_PRIMARY` (2) / `color=TEXT_TERTIARY` (1) / `background_color=BG_PAGE` (1) / `background_color=BG_CODE_PREVIEW` (1) / `border=BORDER_SUBTLE` (1)
- Note: `BORDER_LIGHT` may be used in an f-string; remove the f-string border prop entirely.

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "
from kakumi_app.pages.auth.login import login
from kakumi_app.pages.auth.change_password import change_password
from kakumi_app.pages.admin.import_page import import_page
from kakumi_app.pages.admin.export_page import export_page
print('all imports OK')
"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-03-auth-admin-simple.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/pages/auth/login.py kakumi_app/pages/auth/change_password.py kakumi_app/pages/admin/import_page.py kakumi_app/pages/admin/export_page.py
```

---

## Task 4 — GREEN: Admin medium-complexity pages (no borders)

### Description
Remove token imports and props from admin pages that have no hardcoded borders requiring adaptation. Keep semantic colours (`color="red"`) in place.

### Files to modify

#### 4a. `kakumi_app/pages/admin/users_page.py`
**Import (line 10):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE`
→ Remove entire line.

Prop removals:
- `color=TEXT_PRIMARY,` (~20 occurrences — table cells, headings)
- `color=TEXT_TERTIARY,` (3 occurrences — subtitles, breadcrumbs)
- `background_color=BG_PAGE,` (1 occurrence)

Preserved:
- `border="1px solid #ddd"` (line 249) — left unchanged per ADR-3
- `color="red"` (line 303) — semantic error colour, kept

#### 4b. `kakumi_app/pages/admin/teams_page.py`
**Import (line 10):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE`
→ Remove entire line.

Prop removals:
- All `color=TEXT_PRIMARY` / `color=TEXT_TERTIARY` / `background_color=BG_PAGE`

Preserved:
- `border="1px solid #ddd"` (line 158) — left unchanged per ADR-3
- `color="red"` (line 212) — semantic error colour, kept

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "
from kakumi_app.pages.admin.users_page import users_page
from kakumi_app.pages.admin.teams_page import teams_page
print('admin pages import OK')
"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-04-admin-medium.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/pages/admin/users_page.py kakumi_app/pages/admin/teams_page.py
```

---

## Task 5 — GREEN: Page files with text-only tokens

### Description
Remove background/text token props from three operator-facing page files. No border adaptation.

### Files to modify

#### 5a. `kakumi_app/pages/tournament.py`
**Import (line 6):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_PRIMARY,` (~35 occurrences — headings, table cells, labels)
- `color=TEXT_TERTIARY,` (~6 occurrences — subtitles, stats)

#### 5b. `kakumi_app/pages/viewer.py`
**Import (line 9):** `from kakumi_app.styles.tokens import BG_CARD_ALT, BG_PAGE, TEXT_PRIMARY, TEXT_TERTIARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_TERTIARY,` (line 64)
- `background_color=BG_PAGE,` (lines 79, 111, 147, 165, 173)
- `color=TEXT_PRIMARY,` (line 102)
- `background_color=BG_CARD_ALT,` (line 121)
- `color=TEXT_TERTIARY,` (line 162)

#### 5c. `kakumi_app/pages/exhibition.py`
**Import (line 15):** `from ..styles.tokens import BG_PAGE, TEXT_PRIMARY`
→ Remove entire line.

Prop removals:
- `color=TEXT_PRIMARY,` (lines 53, 60)
- `background_color=BG_PAGE,` (lines 70, 73)

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "
from kakumi_app.pages.tournament import tournament
from kakumi_app.pages.viewer import viewer
from kakumi_app.pages.exhibition import exhibition
print('page imports OK')
"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-05-text-only-pages.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/pages/tournament.py kakumi_app/pages/viewer.py kakumi_app/pages/exhibition.py
```

---

## Task 6 — GREEN: Root `kakumi_app.py`

### Description
Remove token imports and hardcoded colour props from the main app shell (`index()` function).

**Import (line 45):** `from .styles.tokens import BG_PAGE, HOVER_GRAY, TEXT_PRIMARY`
→ Remove entire line.

Prop removals:

| Line | Current | After |
|------|---------|-------|
| 81 | `color=TEXT_PRIMARY,` (heading) | Remove prop |
| 99 | `color=TEXT_PRIMARY,` (card text) | Remove prop |
| 109 | `border_color="black",` (card) | Remove prop entirely |
| 110–111 | `"_hover": {"background-color": HOVER_GRAY, ...}` | Remove entire `style={"_hover": ...}` dict from the `rx.card` |
| 112 | `background_color=BG_PAGE,` (outer box) | Remove prop |

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "from kakumi_app.kakumi_app import index; print('index import OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-06-root-app.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/kakumi_app.py
```

---

## Task 7 — GREEN: `date_calendar.py` (border adaptation)

### Description
`date_calendar.py` has no token imports but has hardcoded `background_color="white"` and `border="1px solid black"` on the trigger button style dict. The popover overlay (`background_color="white"`, `border="1px solid #ddd"`) is left untouched per ADR-4.

### File to modify

**`kakumi_app/components/date_calendar.py`**

| Line | Current | After | Rationale |
|------|---------|-------|-----------|
| 132 | `background_color="white"` (popover overlay) | **UNCHANGED** | White popup on dark bg deliberate |
| 133 | `border="1px solid #ddd"` (popover) | **UNCHANGED** | Subtle border on white popup |
| 151 | `color="black"` (date text) | **UNCHANGED** | On white popup, correct |
| 153 | `color="#999"` (placeholder) | **UNCHANGED** | Inside white popup |
| 162 | `"border": "1px solid black"` (trigger style) | `"border": "1px solid white"` | Button on dark registries page |
| 163 | `"background_color": "white"` (trigger style) | Remove entry | Let Reflex dark theme style the trigger |

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "from kakumi_app.components.date_calendar import date_calendar_popover; print('date_calendar import OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-07-date-calendar.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/components/date_calendar.py
```

---

## Task 8 — GREEN: `results.py` (token removal + border adaptation)

### Description
Remove three text/bg tokens and adapt one hardcoded border.

### File to modify

**`kakumi_app/pages/results.py`**

**Import (line 8):** `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE`
→ Remove entire line.

Prop removals (all `color=TEXT_PRIMARY` and `color=TEXT_TERTIARY` across the file):
| Lines | Token | Action |
|-------|-------|--------|
| 15, 57, 154, 176, 225, 231, 243, 321, 404, 409, 431, 453 | `color=TEXT_PRIMARY` | Remove each |
| 16, 26, 60, 65, 70, 101, 102, 165, 248, 253, 345 | `color=TEXT_TERTIARY` | Remove each |
| 31 | `background_color=BG_PAGE` | Remove prop |

Border adaptation:
| Current | After |
|---------|-------|
| line 30: `border="1px solid #e2e8f0"` | `border="1px solid white"` |

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "from kakumi_app.pages.results import results; print('results import OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-08-results.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/pages/results.py
```

---

## Task 9 — GREEN: `registries.py` (heaviest — border adaptation + token removal)

### Description
The most complex file. Remove 2 token imports, ~45 prop removals, and adapt 14 borders.

### File to modify

**`kakumi_app/pages/registries.py`**

**Import (line 24):** `from kakumi_app.styles.tokens import MUTED_TEXT, TEXT_PRIMARY`
→ Remove entire line.

**Prop removals:**

| Category | Count | Action |
|----------|-------|--------|
| `color=TEXT_PRIMARY` | ~30 (headings, table cells, labels, checkboxes) | Remove each |
| `color=MUTED_TEXT` | 1 (intro text) | Remove |
| `background_color="white"` | ~14 (rx.input, rx.select style dicts) | Remove each entry |

**Border adaptations (rx.input direct props):**
`border="1px solid black"` → `border="1px solid white"` (~10 occurrences)

**Border adaptations (rx.select style dicts):**
`"border": "1px solid black"` → `"border": "1px solid white"` (~4 occurrences)

**Preserved:**
- `"background_color": "black"` (line 120, gender select) — not a white-bg component, left unchanged

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "from kakumi_app.pages.registries import registries; print('registries import OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-09-registries.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/pages/registries.py
```

---

## Task 10 — GREEN: `registry_crud.py` (selective brand keep + border adaptation)

### Description
The most nuanced file. Keep `BRAND_RED` and `BRAND_RED_HOVER`, remove 6 light-theme tokens, adapt 5 borders from `BORDER_LIGHT` f-strings to `"1px solid white"`.

### File to modify

**`kakumi_app/components/registry_crud.py`**

**Import transformation:**

| Current (lines 10–19) | Action |
|------------------------|--------|
| `BG_PAGE` | Remove |
| `BORDER_LIGHT` | Remove |
| `BRAND_RED` | **KEEP** |
| `BRAND_RED_HOVER` | **KEEP** |
| `CARD_BG` | Remove |
| `HEADER_BG` | Remove |
| `MUTED_TEXT` | Remove |
| `TEXT_PRIMARY` | Remove |

Resulting import block:
```python
from kakumi_app.styles.tokens import (
    BRAND_RED,        # ← kept
    BRAND_RED_HOVER,  # ← kept
)
```

**Prop removals:**
| Lines | Prop | Action |
|-------|------|--------|
| 60 | `color="#1a1c1c"` (heading) | Remove entire `color="#1a1c1c"` |
| 252 | `background_color="#e8e8e8"` (empty-state icon) | Remove prop |
| 41, 135, 202 | `background_color=BG_PAGE` | Remove each |
| 116, 141, 196, 204, 257, 257 | `color=TEXT_PRIMARY` | Remove each |
| 61, 64, 119, 125, 218, 258, 291, 313 | `color=MUTED_TEXT` | Remove each |
| 175, 341 | `background_color=CARD_BG` | Remove each |
| 292 | `background_color=HEADER_BG` | Remove |

**Border adaptations (BORDER_LIGHT → white):**
| Line | Current | After |
|------|---------|-------|
| 137 | `border=f"1.5px dashed {BORDER_LIGHT}"` (upload zone) | `border="1.5px dashed white"` |
| 176 | `border=f"1px solid {BORDER_LIGHT}"` (import panel card) | `border="1px solid white"` |
| 204 | `border=f"1px solid {BORDER_LIGHT}"` (search input) | `border="1px solid white"` |
| 294 | `border_bottom=f"1px solid {BORDER_LIGHT}"` (filter row) | `border_bottom="1px solid white"` |
| 335 | `border_top=f"1px solid {BORDER_LIGHT}"` (pagination footer) | `border_top="1px solid white"` |
| 341 | `border=f"1px solid {BORDER_LIGHT}"` (table card) | `border="1px solid white"` |

### Verification
```bash
python -m pytest tests/ -v --tb=short -q 2>&1 | tail -5
python -c "
from kakumi_app.components.registry_crud import (
    registry_page_shell, registry_content,
    registry_actions_header, registry_empty_state
)
print('registry_crud imports OK')
"
# Also verify brand tokens still importable
python -c "from kakumi_app.styles.tokens import BRAND_RED, BRAND_RED_HOVER; print('brand tokens OK')"
```

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-10-registry-crud.txt`.

### Rollback
```bash
git checkout HEAD -- kakumi_app/components/registry_crud.py
```

---

## Task 11 — VERIFY: Integration smoke test

### Description
Run the full verification suite and produce the evidence package.

### Actions

1. **Full test suite:**
   ```bash
   python -m pytest tests/ -v 2>&1
   ```

2. **Import integrity check:**
   ```bash
   python -c "
   # Confirm no dangling token imports
   from kakumi_app.styles.tokens import (
       BRAND_RED, BRAND_RED_HOVER, BRAND_RED_HOVER_LIGHT,
       ACCENT_GOLD, TEXT_WHITE,
   )
   print('Surviving brand tokens: OK')

   # Confirm no light-theme-only tokens survive in any modified file
   import ast, sys
   MODIFIED_FILES = [
       'kakumi_app/kakumi_app.py',
       'kakumi_app/pages/registries.py',
       'kakumi_app/pages/results.py',
       'kakumi_app/pages/tournament.py',
       'kakumi_app/pages/viewer.py',
       'kakumi_app/pages/exhibition.py',
       'kakumi_app/pages/auth/login.py',
       'kakumi_app/pages/auth/change_password.py',
       'kakumi_app/pages/admin/users_page.py',
       'kakumi_app/pages/admin/teams_page.py',
       'kakumi_app/pages/admin/export_page.py',
       'kakumi_app/pages/admin/import_page.py',
       'kakumi_app/components/registry_crud.py',
       'kakumi_app/components/protected_layout.py',
       'kakumi_app/components/tables.py',
       'kakumi_app/components/match_card.py',
       'kakumi_app/components/date_calendar.py',
   ]
   LIGHT_TOKENS = {'BG_PAGE', 'BG_CARD_ALT', 'BG_CODE_PREVIEW', 'CARD_BG',
                   'HEADER_BG', 'TEXT_PRIMARY', 'TEXT_TERTIARY', 'MUTED_TEXT',
                   'HOVER_GRAY', 'BORDER_LIGHT', 'BORDER_SUBTLE'}
   for path in MODIFIED_FILES:
       with open(path) as f:
           tree = ast.parse(f.read())
       for node in ast.walk(tree):
           if isinstance(node, ast.Name) and node.id in LIGHT_TOKENS:
               print(f'ISSUE: {path} still references {node.id}')
               sys.exit(1)
   print('All light tokens removed from modified files: OK')
   "
   ```

3. **Reflex startup check:**
   ```bash
   reflex run --loglevel debug 2>&1 | head -20
   ```

### Visual smoke-test checklist (manual)
- [ ] `/registries/athletes` — form inputs have visible borders (white on dark), headings readable
- [ ] `/login` — centred card readable on dark bg
- [ ] `/results` — headings and status badges readable
- [ ] `/tournament` — all headings and table cells readable
- [ ] `/exhibition` — menu page header readable
- [ ] `/viewer` — login page and dashboard readable
- [ ] `/admin/users` — table rows readable, filter controls visible
- [ ] `/admin/teams` — table rows readable
- [ ] `/admin/export` — page content readable
- [ ] `/admin/import` — page content readable
- [ ] Sidebar — crimson bg, white text/icons (unchanged)
- [ ] Public display pages — unchanged

### Evidence recording
Save to `openspec/changes/re-styling/evidence/task-11-integration.txt` containing:
1. pytest exit code + summary line
2. Import integrity check output
3. Reflex startup first 5 lines
4. Visual checklist (mark each as PASS or FAIL)

### Rollback
Full-revert command:
```bash
git revert HEAD --no-edit
```

---

## Files Confirmed No Changes

The following files were surveyed and verified to require zero modifications:

| File | Reason |
|------|--------|
| `kakumi_app/styles/tokens.py` | Canonical token definitions, kept as rollback anchor |
| `kakumi_app/styles/dark_tokens.py` | **Does not exist and will not be created** (subtractive approach) |
| `kakumi_app/components/sidebar.py` | Already dark-styled with crimson bg, excluded by spec |
| `kakumi_app/components/registries_items.py` | Only uses `BRAND_RED_HOVER, BRAND_RED_HOVER_LIGHT, TEXT_WHITE` — all brand tokens, all kept |
| `kakumi_app/pages/admin/referees_page.py` | Inherits bg from `registry_page_shell`; no direct token imports |
| `kakumi_app/pages/admin/athletes_page.py` | Same as above |
| `rxconfig.py` | No theme config needed (theme set via `rx.App(theme=...)`) |

---

## Summary

| Metric | Value |
|--------|-------|
| Files modified | 17 |
| Files created | 0 |
| Files deleted | 0 |
| Estimated changed lines | ~170–200 |
| Token types removed | 11 (BG_PAGE, BG_CARD_ALT, BG_CODE_PREVIEW, CARD_BG, HEADER_BG, TEXT_PRIMARY, TEXT_TERTIARY, MUTED_TEXT, HOVER_GRAY, BORDER_LIGHT, BORDER_SUBTLE) |
| Token types kept | 5 (BRAND_RED, BRAND_RED_HOVER, BRAND_RED_HOVER_LIGHT, ACCENT_GOLD, TEXT_WHITE) |
| Borders adapted to white | ~21 total |
| TDD cycles | 10 RED→GREEN cycles, 1 verify cycle |
| Rollback | Single `git revert HEAD` |

---

## Phase Envelope

| Field | Value |
|-------|-------|
| **Phase** | `sdd/tasks` |
| **Status** | ✅ Complete |
| **Artifact Store Mode** | `openspec` (file-backed; Engram unavailable in session) |

### Executive Summary

Written `tasks.md` with 11 concrete implementation tasks organized from lowest risk (prerequisite dark theme) through simple leaf components, auth pages, admin pages, text-only pages, root app file, border-adaptation files, and finally the heaviest file `registries.py` and the nuanced `registry_crud.py`. Each task follows RED→GREEN→EVIDENCE TDD cycles. The review workload forecast estimates ~170–200 changed lines across 17 files, well within the 400-line budget — a single PR is sufficient. No chained PRs are recommended. Rollback is a single `git revert HEAD`.

### Skills Resolved

| Skill | Status |
|-------|--------|
| `caveman` | Path-injected |
| `python-pro` | Path-injected |
| `reflex-dev` | Path-injected |
| `frontend-design` | Path-injected |
| **Skill resolution type** | `paths-injected` |

### Risks in Tasks

| Risk | Mitigation |
|------|------------|
| **Task 1 (dark theme API)** — Reflex 0.8.28's `rx.theme(appearance="dark")` may differ from expected | Task includes investigation step via `help(rx.theme)` before applying; fallback to alternative API |
| **`registries.py` missed border** — one of 14 `border="1px solid black"` not caught | Task 11 visual checklist explicitly requires inspecting all registries forms |
| **`registry_crud.py` BORDER_LIGHT in style dict** — f-string substitution may differ from direct props | Explicitly enumerated each border location in Task 10 |
| **Style dict `border` vs direct `border=`** — Reflex may handle them differently | Border adaptation tasks target both patterns; visual checklist verifies each |
| **`#ddd` borders in admin pages** — faint on dark bg | ADR-3 accepts this; flagged as known limitation |
| **Baseline test suite red** (Task 0) | Fallback instructs: diagnose before proceeding |

### Next Recommended

Proceed to `sdd/apply` phase — execute Tasks 0 through 11 in order, accumulating evidence in `openspec/changes/re-styling/evidence/`.
