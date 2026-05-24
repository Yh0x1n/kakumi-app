# SDD Tasks — visual-styling-overhaul

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~200–250 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**NOTE**: Strict TDD is enabled (`openspec/config.yaml`). Tasks are ordered as RED (test-first) → GREEN (implement) → REFACTOR/tidy. Several tasks are intertwined; follow the dependency chain to avoid broken intermediate states.

---

## Phase 0: Token Infrastructure — Test First (RED)

### 0.1 `RED` — Add tests for new design tokens

**Files to modify**: `tests/test_batch2_rx_event_fixups_and_tokens.py`

**Changes**:
- Add `test_new_tokens_exist_for_visual_styling_overhaul()` that imports and asserts all 6 new tokens:
  - `CARD_BG == "#ffffff"`, `HEADER_BG == "#f2f2f2"`, `MUTED_TEXT == "#534342"`
  - `TEXT_PRIMARY == "#000000"`, `TEXT_SECONDARY == "#000000"`, `TEXT_TERTIARY == "#808080"`
- Add test that `from kakumi_app.styles.tokens import CARD_BG, HEADER_BG, MUTED_TEXT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY` succeeds
- Add `test_batch2_target_files_have_no_raw_hex_literals_v2()` covering ALL 18 modified files from the change list, asserting `_hex_literals_in_file(file_path) == []` for each (except `test_batch2_target_files_have_no_raw_hex_literals` still covers the original 5 files)

**Dependencies**: None (test-only, no production code needed yet)

**Effort**: Small

---

### 0.2 `RED` — Add tests for `registry_crud` re-export compatibility

**Files to modify**: `tests/test_batch2_rx_event_fixups_and_tokens.py` (or a new test file)

**Changes**:
- Add `test_registry_crud_reexports_tokens()`:
  - `from kakumi_app.components.registry_crud import CARD_BG, HEADER_BG, MUTED_TEXT`
  - Assert values match the token definitions
- This ensures the Python re-export contract holds after the migration

**Dependencies**: None

**Effort**: Small

---

### 0.3 `GREEN` — Add 6 new design tokens to `styles/tokens.py`

**Files to modify**: `kakumi_app/styles/tokens.py`

**Changes**:
- Add section comments: `# ── Backgrounds ────────────────────────────────────`, `# ── Text ───────────────────────────────────────────`, `# ── Interactive ────────────────────────────────────`, `# ── Borders ────────────────────────────────────────`
- Add token definitions under the appropriate section:
  - `CARD_BG = "#ffffff"` (Backgrounds)
  - `HEADER_BG = "#f2f2f2"` (Backgrounds)
  - `MUTED_TEXT = "#534342"` (Text)
  - `TEXT_PRIMARY = "#000000"` (Text)
  - `TEXT_SECONDARY = "#000000"` (Text)
  - `TEXT_TERTIARY = "#808080"` (Text)

**Dependencies**: 0.1 must pass (tests verify these exist)

**Effort**: Small (~15 lines added)

---

## Phase 1: Registry CRUD Migration

### 1.1 `GREEN` — Migrate `registry_crud.py` local constants to token imports

**Files to modify**: `kakumi_app/components/registry_crud.py`

**Changes**:
1. **Import change**: Extend the existing import line:
   - `from kakumi_app.styles.tokens import BG_PAGE, BORDER_LIGHT, BRAND_RED, BRAND_RED_HOVER, CARD_BG, HEADER_BG, MUTED_TEXT`
2. **Remove** the 3 local constant assignment lines:
   - `CARD_BG = "#ffffff"`
   - `HEADER_BG = "#f2f2f2"`
   - `MUTED_TEXT = "#534342"`
3. **Replace `color="black"` → `color=TEXT_PRIMARY`** in 5 locations:
   - `registry_import_panel`: `rx.heading("Importar archivo", size="5", color="black")` (line ~67)
   - `registry_import_panel`: `rx.text(selected_file_name, color="black", font_weight="medium")` (line ~92)
   - `registry_table_filters`: `rx.icon(tag="search", width="16", heigth="12", color="black")` (line ~135) — note: already `color="black"` not `color=TEXT_PRIMARY`
   - `registry_table_filters`: `color="black"` on input (line ~137)
   - `registry_empty_state`: `rx.heading(title, size="6", color="black")` (line ~187)
   - `registry_empty_state`: `rx.button(..., color="black")` — NO, this uses `color="white"`. Let me re-read...

Actually, let me check line 195 and 248 from the design spec. Let me re-read:

**Design says lines 111, 135, 187, 195, 248**. Let me verify against the file I read:
- Line 111 (approximately): In `registry_import_panel` — `rx.text(selected_file_name, color="black", font_weight="medium")` — YES
- Line 135 (approximately): In `registry_table_filters` — `color="black"` on the search icon and the input — yes, `rx.icon(..., color="black")` and `color="black"` on input
- Line 187 (approximately): In `registry_empty_state` — `rx.heading(title, size="6", color="black")` — YES
- Line 195 (approximately): Let me check... actually in `registry_empty_state` there's `rx.button(cta_label, ..., color="white")` — that's "white" not "black". Hmm.
  Let me re-read more carefully. Looking at the actual file, the mock line numbers in the source might differ from the design's estimate. Let me focus on actual patterns.

In `registry_crud.py`:
1. `registry_import_panel`: `rx.heading("Importar archivo", size="5", color="black")` — line ~67
2. `registry_import_panel`: `rx.text(selected_file_name, color="black", font_weight="medium")` — line ~93
3. `registry_table_filters`: `rx.icon(tag="search", ..., color="black")` — line ~135
4. `registry_table_filters`: `color="black"` on `rx.input(...)` — line ~139  
5. `registry_empty_state`: `rx.heading(title, size="6", color="black")` — line ~182

That's 5 occurrences.

Also, the `registry_actions_header` has `color="#1a1c1c"` on a heading (not "black" — different hex). The design does NOT mention changing `color="#1a1c1c"` — that's out of scope.

**Dependencies**: Phase 0 (token definitions must exist)

**Effort**: Small

---

### 1.2 `GREEN` — Update `registries.py` import source and apply token replacements

**Files to modify**: `kakumi_app/pages/registries.py`

**Changes**:
1. **Import change**: Replace:
   ```python
   from kakumi_app.components.registry_crud import (
       MUTED_TEXT,
       registry_actions_header,
       ...
   )
   ```
   with:
   ```python
   from kakumi_app.styles.tokens import MUTED_TEXT, TEXT_PRIMARY, BG_PAGE
   from kakumi_app.components.registry_crud import (
       registry_actions_header,
       ...
   )
   ```
   (Remove `MUTED_TEXT` from the `registry_crud` import line, keep all other symbols)

2. **Replace `color="black"` → `color=TEXT_PRIMARY`** in ~40+ occurrences:
   - `_registry_form_heading`: `rx.heading(title, size="6", color="black")` (1×)
   - `registries()`: `rx.heading("Registros", size="8", color="black")` (1×)
   - `_athlete_form()`, `_referee_form()`, `_tournament_form()`: All `rx.heading(..., size="3", color="black")` for field labels (~15×)
   - Form inputs: `color="black"` in `rx.input(..., color="black")` (~9×)
   - Form selects: `style={"color": "black", ...}` in `rx.select(...)` style dicts (~4×)
   - Table cells: `rx.table.cell(..., color="black")` in row renderers (~12×)
   - **EXCLUDE** `border="1px solid black"` — these are structural borders, not text colors

3. **Replace `background_color="white"` → `background_color=BG_PAGE`** in all form fields (~15×):
   - All `rx.input(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: 1.1 (token imports in registry_crud must work)

**Effort**: Large (many replacements, careful per-line verification needed)

---

## Phase 2: Core App & Auth Pages

### 2.1 `GREEN` — Apply tokens to `kakumi_app.py`

**Files to modify**: `kakumi_app/kakumi_app.py`

**Changes**:
1. **Import change**: Extend existing import:
   ```python
   from .styles.tokens import HOVER_GRAY, TEXT_PRIMARY, BG_PAGE
   ```
2. **Replace `color="black"`** (2× in `index()`):
   - `rx.heading("Welcome to...", ..., color="black")` → `color=TEXT_PRIMARY`
   - `rx.text(f"Resultado {i + 1}", ..., color="black")` → `color=TEXT_PRIMARY`
3. **Replace `background_color="white"`** (1×):
   - `rx.box(..., background_color="white", ...)` → `background_color=BG_PAGE`
4. **EXCLUDE**: `border_color="black"` — keep as-is

**Dependencies**: Phase 0

**Effort**: Small

---

### 2.2 `GREEN` — Apply tokens and centering fix to `login.py`

**Files to modify**: `kakumi_app/pages/auth/login.py`

**Changes**:
1. **Import change**: Extend existing import:
   ```python
   from kakumi_app.styles.tokens import BG_PAGE, TEXT_TERTIARY
   ```
2. **Replace `color="gray"`** (1×):
   - `rx.text("Por favor, ingrese...", ..., color="gray", ...)` → `color=TEXT_TERTIARY`
3. **Restructure centering layout**:
   - Current: `rx.box > rx.vstack(spacing=5, justify_content="center", min_height="100vh", bg=BG_PAGE) > rx.center > rx.card`
   - New: `rx.box(width="100%", min_height="100vh", background_color=BG_PAGE) > rx.center(min_height="100vh") > rx.card(w=400px, box_shadow="lg", border_radius="lg") > rx.vstack(padding="2em", width="100%")`
   
   The `rx.center` with `min_height="100vh"` handles both horizontal and vertical centering in one element, removing the intermediate `rx.vstack`. Card content stays identical.

**Dependencies**: Phase 0

**Effort**: Medium (layout restructuring requires visual verification)

---

### 2.3 `GREEN` — Apply tokens to `change_password.py`

**Files to modify**: `kakumi_app/pages/auth/change_password.py`

**Changes**:
1. **Import change**: Extend existing import:
   ```python
   from kakumi_app.styles.tokens import BG_PAGE, TEXT_TERTIARY
   ```
2. **Replace `color="gray"`** (1×):
   - `rx.text("Your first login requires...", ..., color="gray", ...)` → `color=TEXT_TERTIARY`
3. Also replace `color="gray"` in `rx.text("This action...", font_size="sm", color="gray")` in `users_page()` style deny messages inside `change_password_page()` — actually, that's in `change_password.py` too. Let me check...

Looking at the file, `color="gray"` occurs in:
- `change_password_form()`: `rx.text("Your first login...", color="gray", ...)` — 1×

That's it for `change_password.py`.

**Dependencies**: Phase 0

**Effort**: Small

---

## Phase 3: Exhibition & Tournament Pages

### 3.1 `GREEN` — Apply tokens to `exhibition.py`

**Files to modify**: `kakumi_app/pages/exhibition.py`

**Changes**:
1. **Import**: Add new import line (currently imports nothing from tokens):
   ```python
   from kakumi_app.styles.tokens import BG_PAGE, TEXT_PRIMARY
   ```
2. **Replace `color="black"`** (2× in `exhibition()`):
   - `rx.heading("Exhibición", ..., color="black")` → `color=TEXT_PRIMARY`
   - `rx.text("Aquí se mostrarán...", ..., color="black")` → `color=TEXT_PRIMARY`
3. **Replace `background_color="white"`** (2× in `exhibition()`):
   - `rx.vstack(..., background_color="white")` → `background_color=BG_PAGE`
   - `rx.box(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 3.2 `GREEN` — Apply tokens to `tournament.py`

**Files to modify**: `kakumi_app/pages/tournament.py`

**Changes**:
1. **Import**: Add new import line (currently imports nothing from tokens):
   ```python
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY
   ```
2. **Replace `color="black"`** → `color=TEXT_PRIMARY` (~15+ occurrences):
   - `_workspace_header`: `rx.heading("Torneo", ..., color="black")`, `rx.text(..., color="black")` (2×)
   - `_selector_card`: `rx.heading("Torneos disponibles", ..., color="black")`, `rx.text("No hay...", color="black")` (2×)
   - `_selection_summary`: Multiple `rx.heading(... color="black")`, `rx.text(... color="black")` (~5×)
   - `_lifecycle_card`: `rx.heading("Controles de ciclo", ..., color="black")` (1×)
   - `_categories_card`: Multiple headings and texts with `color="black"` (~6×)
   - `_tatami_card`: Multiple headings and texts with `color="black"` (~6×)
3. **Replace `color="gray"`** → `color=TEXT_TERTIARY` (4 occurrences):
   - `_lifecycle_card`: `rx.text("Solo operadores...", color="gray")` (1×)
   - `_lifecycle_card`: `rx.text("No tienes permisos...", color="gray")` (1×)
   - `_categories_card`: `rx.text("Selecciona un torneo...", color="gray")` (1×)
   - `_tatami_card`: `rx.text("No hay tatamis...", color="gray")` (1×)
4. **EXCLUDE**: `color_scheme="gray"` in `rx.badge(..., color_scheme="gray")` — these are Reflex theme props, not text colors

**Dependencies**: Phase 0

**Effort**: Medium (many replacements, careful scanning)

---

### 3.3 `GREEN` — Apply tokens to `results.py`

**Files to modify**: `kakumi_app/pages/results.py`

**Changes**:
1. **Import**: Add new import line (currently imports nothing from tokens):
   ```python
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE
   ```
2. **Replace `color="black"`** (1×):
   - `_results_header`: `rx.heading(title, size="8", color="black")` → `color=TEXT_PRIMARY`
3. **Replace `color="gray"`** (~12×):
   - `_results_header`: `rx.text(subtitle, color="gray")` (1×)
   - `_empty_state`: `rx.text(message, color="gray", ...)` (1×)
   - `results()`: `rx.text(f"Sede: {t['venue']}", color="gray")` and similar in tournament cards (3×)
   - `category_results()`: breadcrumb `rx.link(..., color="gray")` and `rx.text("›", color="gray")` (2×)
   - `category_results()`: text `color="gray"` on score display (1×)
   - `tournament_results()`: texts with `color="gray"` in category cards (2×)
   - `podium_results()`: `rx.text(..., color="gray")` (1×)
4. **Replace `background_color="white"`** (1×):
   - `_empty_state`: `rx.box(..., background_color="white")` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Medium

---

## Phase 4: Admin Pages

### 4.1 `GREEN` — Apply tokens to `users_page.py`

**Files to modify**: `kakumi_app/pages/admin/users_page.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE
   ```
2. **Replace `color="black"`** (1×):
   - `users_page()`: `rx.heading("Gestión de Usuarios", ..., color="black")` → `color=TEXT_PRIMARY`
3. **Replace `color="gray"`** (3×):
   - `users_page()`: `rx.text("Administrar usuarios...", color="gray")` (1×)
   - `users_table()`: `rx.text("Esta acción no se puede...", color="gray")` (1×)
   - `users_page()` (denied branch): `rx.text("You don't have permission...", color="gray")` (1×)
4. **Replace `background_color="white"`** (1×):
   - `users_page()`: `rx.vstack(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 4.2 `GREEN` — Apply tokens to `teams_page.py`

**Files to modify**: `kakumi_app/pages/admin/teams_page.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE
   ```
2. **Replace `color="black"`** (1×):
   - `teams_page()`: `rx.heading("Gestión de Equipos", ..., color="black")` → `color=TEXT_PRIMARY`
3. **Replace `color="gray"`** (2×):
   - `teams_page()`: `rx.text("Administrar equipos...", color="gray")` (1×)
   - `teams_page()` (denied branch): `rx.text("You don't have permission...", color="gray")` (1×)
4. **Replace `background_color="white"`** (1×):
   - `teams_page()`: `rx.vstack(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 4.3 `GREEN` — Apply tokens to `export_page.py`

**Files to modify**: `kakumi_app/pages/admin/export_page.py`

**Changes**:
1. **Import**: Extend existing import:
   ```python
   from kakumi_app.styles.tokens import BG_CODE_PREVIEW, BORDER_LIGHT, BORDER_SUBTLE, TEXT_TERTIARY, BG_PAGE
   ```
2. **Replace `color="gray"`** (2×):
   - `export_form()`: `rx.text("Selecciona un torneo...", ..., color="gray")` (1×)
   - `export_page()` (denied branch): `rx.text("You don't have permission...", color="gray")` (1×)
3. **Replace `background_color="white"`** (1×):
   - `export_page()`: `rx.vstack(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 4.4 `GREEN` — Apply tokens to `import_page.py`

**Files to modify**: `kakumi_app/pages/admin/import_page.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_TERTIARY
   ```
2. **Replace `color="black"`** (1×):
   - `import_athletes()`: `rx.heading("Importación de registros", size="6", color="black")` → `color=TEXT_PRIMARY`
3. **Replace `color="gray"`** (1×):
   - `import_athletes()`: `rx.text("Redirigiendo...", color="gray")` → `color=TEXT_TERTIARY`

**Dependencies**: Phase 0

**Effort**: Small

---

## Phase 5: Viewer & Component Pages

### 5.1 `GREEN` — Apply tokens to `viewer.py`

**Files to modify**: `kakumi_app/pages/viewer.py`

**Changes**:
1. **Import**: Extend existing import:
   ```python
   from kakumi_app.styles.tokens import BG_CARD_ALT, BG_PAGE, TEXT_PRIMARY, TEXT_TERTIARY
   ```
2. **Replace `color="black"`** (1×):
   - `viewer_dashboard_page()`: `rx.heading(f"Torneo: ...", ..., color="black")` → `color=TEXT_PRIMARY`
3. **Replace `color="gray"`** (2×):
   - `viewer_login_page()`: `rx.text("El código le permitirá...", ..., color="gray")` (1×)
   - `viewer_dashboard_page()`: `rx.text("La visualización...", ..., color="gray")` (1×)
4. **Replace `background_color="white"`** (3× in `viewer_dashboard_page()`):
   - `rx.hstack(..., background_color="white")` (1×)
   - `rx.box(..., background_color="white")` in categories section (1×)
   - `rx.box(..., background_color="white")` in bracket section (1×)
   All → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 5.2 `GREEN` — Apply tokens to `protected_layout.py`

**Files to modify**: `kakumi_app/components/protected_layout.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_TERTIARY, BG_PAGE
   ```
2. **Replace `color="gray"`** (1×):
   - `protected_layout()` (denied branch): `rx.text("You don't have permission...", ..., color="gray")` → `color=TEXT_TERTIARY`
3. **Replace `background_color="white"`** (1×):
   - `protected_layout()`: `rx.vstack(..., background_color="white", ...)` → `background_color=BG_PAGE`

**Dependencies**: Phase 0

**Effort**: Small

---

### 5.3 `GREEN` — Apply tokens to `match_card.py`

**Files to modify**: `kakumi_app/components/match_card.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_TERTIARY
   ```
2. **Replace `color="gray"`** (1×):
   - `match_card()`: `rx.text("vs", color="gray")` → `color=TEXT_TERTIARY`

**Dependencies**: Phase 0

**Effort**: Small

---

### 5.4 `GREEN` — Apply tokens to `tables.py`

**Files to modify**: `kakumi_app/components/tables.py`

**Changes**:
1. **Import**: Add new import line:
   ```python
   from kakumi_app.styles.tokens import TEXT_TERTIARY
   ```
2. **Replace `color="gray"`** (1×):
   - `athletes_table()`: `rx.text("Tabla de atletas...", color="gray")` → `color=TEXT_TERTIARY`

**Dependencies**: Phase 0

**Effort**: Small

---

### 5.5 `GREEN` — Apply tokens to `sidebar.py`

**Files to modify**: `kakumi_app/components/sidebar.py`

**Changes**:
1. **Import**: Extend existing import:
   ```python
   from kakumi_app.styles.tokens import (
       ACCENT_GOLD, BRAND_RED, BRAND_RED_HOVER, HOVER_GRAY, TEXT_WHITE,
       TEXT_PRIMARY,
   )
   ```
2. **Replace `color="black"`** (1×):
   - `sidebar()`: `rx.icon("align-justify", ..., color="black")` → `color=TEXT_PRIMARY`
3. **EXCLUDE**: `color="gray"` in sidebar is out of scope per spec — do NOT change

**Dependencies**: Phase 0

**Effort**: Small

---

## Phase 6: Verification (REFACTOR / CLEANUP)

### 6.1 Run linting and import hygiene check

**Changes**:
1. Run `ruff check --select F401` on all 18 modified files:
   ```bash
   ruff check --select F401 kakumi_app/styles/tokens.py kakumi_app/components/registry_crud.py kakumi_app/kakumi_app.py kakumi_app/pages/auth/login.py kakumi_app/pages/auth/change_password.py kakumi_app/pages/exhibition.py kakumi_app/pages/tournament.py kakumi_app/pages/results.py kakumi_app/pages/registries.py kakumi_app/pages/admin/users_page.py kakumi_app/pages/admin/teams_page.py kakumi_app/pages/admin/export_page.py kakumi_app/pages/admin/import_page.py kakumi_app/pages/viewer.py kakumi_app/components/protected_layout.py kakumi_app/components/match_card.py kakumi_app/components/tables.py kakumi_app/components/sidebar.py
   ```
2. Remove any orphaned imports discovered (especially `MUTED_TEXT` from `registry_crud` in files that import it transitively but don't use it directly)
3. Run `ruff format` on modified files to ensure PEP 8 compliance

**Dependencies**: All GREEN tasks completed

**Effort**: Small

---

### 6.2 Verify no remaining hardcoded color values in modified files

**Changes**:
1. Grep for remaining `color="black"` in all modified files — expect zero matches
2. Grep for remaining `color="gray"` in all modified files — expect zero matches (sidebar excluded)
3. Grep for remaining `background_color="white"` in all modified files — expect zero matches
4. Grep for `color="black"` inside `border`, `border_color`, or `border="1px solid black"` — these are structural and should remain

**Dependencies**: 6.1

**Effort**: Small

---

### 6.3 Run token import verification

**Changes**:
1. ```bash
   python -c "
   from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, CARD_BG, HEADER_BG, MUTED_TEXT
   print('All tokens import OK')
   assert TEXT_PRIMARY == '#000000'
   assert TEXT_SECONDARY == '#000000'
   assert TEXT_TERTIARY == '#808080'
   assert CARD_BG == '#ffffff'
   assert HEADER_BG == '#f2f2f2'
   assert MUTED_TEXT == '#534342'
   print('All token values match spec')
   "
   ```
2. Verify re-export compatibility:
   ```bash
   python -c "
   from kakumi_app.components.registry_crud import CARD_BG, HEADER_BG, MUTED_TEXT
   print('registry_crud re-exports OK')
   "
   ```

**Dependencies**: All GREEN tasks completed

**Effort**: Small

---

### 6.4 Run test suite

**Changes**:
1. ```bash
   python -m pytest tests -v --tb=short 2>&1 | tail -40
   ```
2. Verify ALL tests pass, including:
   - `test_new_tokens_exist_for_visual_styling_overhaul` (new)
   - `test_registry_crud_reexports_tokens` (new)
   - `test_batch2_target_files_have_no_raw_hex_literals_v2` (new)
   - `test_batch2_target_files_have_no_raw_hex_literals` (existing — still covers original 5 files)
   - `test_new_tokens_exist_for_batch2` (existing — still passes since all old tokens unchanged)

**Dependencies**: 6.3

**Effort**: Small

---

### 6.5 Visual smoke test

**Changes**:
1. Start app with `python -m kakumi_app.kakumi_app` (or `reflex run`)
2. Visually verify:
   - Login page centers correctly (no scrollbar, card centered)
   - All pages have consistent background color (BG_PAGE)
   - No "black" or "gray" text color regressions
   - `border_color="black"` in `kakumi_app.py` still visibly shows black border
   - Sidebar `color="gray"` values are unchanged

**Dependencies**: 6.4

**Effort**: Medium (manual visual verification)

---

## Summary: File Change Matrix

| # | File | Phase | Task | Effort |
|---|------|-------|------|--------|
| 1 | `styles/tokens.py` | 0.3 | Add 6 new tokens | Small |
| 2 | `components/registry_crud.py` | 1.1 | Migrate constants → tokens, fix `color="black"` | Small |
| 3 | `kakumi_app.py` | 2.1 | Apply `TEXT_PRIMARY`, `BG_PAGE` | Small |
| 4 | `pages/auth/login.py` | 2.2 | Apply `TEXT_TERTIARY` + centering fix | Medium |
| 5 | `pages/auth/change_password.py` | 2.3 | Apply `TEXT_TERTIARY` | Small |
| 6 | `pages/exhibition.py` | 3.1 | Apply `TEXT_PRIMARY`, `BG_PAGE` | Small |
| 7 | `pages/tournament.py` | 3.2 | Apply `TEXT_PRIMARY`, `TEXT_TERTIARY` | Medium |
| 8 | `pages/results.py` | 3.3 | Apply all three tokens | Medium |
| 9 | `pages/registries.py` | 1.2 | Import + replace `color="black"` (40×) + `bg="white"` (15×) | Large |
| 10 | `pages/admin/users_page.py` | 4.1 | Apply all three tokens | Small |
| 11 | `pages/admin/teams_page.py` | 4.2 | Apply all three tokens | Small |
| 12 | `pages/admin/export_page.py` | 4.3 | Apply `TEXT_TERTIARY`, `BG_PAGE` | Small |
| 13 | `pages/admin/import_page.py` | 4.4 | Apply `TEXT_PRIMARY`, `TEXT_TERTIARY` | Small |
| 14 | `pages/viewer.py` | 5.1 | Apply all three tokens | Small |
| 15 | `components/protected_layout.py` | 5.2 | Apply `TEXT_TERTIARY`, `BG_PAGE` | Small |
| 16 | `components/match_card.py` | 5.3 | Apply `TEXT_TERTIARY` | Small |
| 17 | `components/tables.py` | 5.4 | Apply `TEXT_TERTIARY` | Small |
| 18 | `components/sidebar.py` | 5.5 | Apply `TEXT_PRIMARY` | Small |

---

## Critical Exclusions (Do NOT Touch)

| Location | Pattern | Reason |
|----------|---------|--------|
| `kakumi_app.py` | `border_color="black"` | Structural border, not text |
| `tournament.py` | `color_scheme="gray"` | Reflex theme prop, not text color |
| `registries.py` | `border="1px solid black"` | Structural border, not text color |
| `sidebar.py` | `color="gray"` | Out of scope per spec |
| All `pages/competition/` | Any pattern | Explicitly excluded from this change |
| `pages/public_display.py` | Any pattern | Explicitly excluded from this change |

---

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| `border_color="black"` misidentified as `color="black"` | Incorrect replacement | Use exact string search `color="black"` (with leading quote), verify each match |
| `color_scheme="gray"` confused with `color="gray"` | Incorrect replacement | Different prop name — no regex ambiguity, but manual scan recommended in tournament.py |
| Login centering introduces scrollbar | UX regression | Proposed structure uses single `rx.center(min_height="100vh")` with no overflow props. Test at 400×600 viewport |
| Token re-export breaks transitive import | Runtime import error | Python re-exports guarantee `registry_crud.CARD_BG` continues to work. Verification task 6.3 covers this |
| Tests fail because `test_batch2_target_files_have_no_raw_hex_literals` hasn't been updated | CI failure | Phase 0.1 adds the updated test. The old test still covers original 5 files — both pass independently |
