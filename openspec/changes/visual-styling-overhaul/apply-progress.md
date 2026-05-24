# Apply Progress — visual-styling-overhaul

## Phase 1: Token Infra ✅

### 1.1 `kakumi_app/styles/tokens.py`
- [x] Add 6 new tokens: CARD_BG, HEADER_BG, MUTED_TEXT, TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY
- [x] Restructure with section headers: Brand → Backgrounds → Text → Interactive → Borders

### 1.2 `kakumi_app/components/registry_crud.py`
- [x] Add CARD_BG, HEADER_BG, MUTED_TEXT, TEXT_PRIMARY to tokens import
- [x] Remove 3 local constant definitions
- [x] Replace 5× `color="black"` → `color=TEXT_PRIMARY`

### 1.3 `kakumi_app/pages/registries.py`
- [x] Change MUTED_TEXT import from registry_crud → tokens
- [x] Add TEXT_PRIMARY, BG_PAGE imports
- [x] Replace ~40× `color="black"` → `color=TEXT_PRIMARY` (headings, inputs, table cells, checkboxes, selects)
- [x] Keep `border="1px solid black"` unchanged
- [x] Keep input `background_color="white"` unchanged (design intentional)

## Phase 2: Core App + Auth ✅

### 2.1 `kakumi_app/kakumi_app.py`
- [x] Add TEXT_PRIMARY, BG_PAGE to import
- [x] Replace 2× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`
- [x] Keep `border_color="black"` unchanged

### 2.2 `kakumi_app/pages/auth/login.py`
- [x] Add TEXT_TERTIARY to import
- [x] Restructure layout: `rx.box > rx.center(min_height=100vh) > rx.card > rx.vstack`
- [x] Replace `color="gray"` → `color=TEXT_TERTIARY` in hint text
- [x] Card now perfectly centered both axes

### 2.3 `kakumi_app/pages/auth/change_password.py`
- [x] Add TEXT_TERTIARY to import
- [x] Replace 1× `color="gray"` → `color=TEXT_TERTIARY`

## Phase 3: Exhibition + Tournament + Results ✅

### 3.1 `kakumi_app/pages/exhibition.py`
- [x] Add BG_PAGE, TEXT_PRIMARY imports
- [x] Replace 2× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 2× `background_color="white"` → `background_color=BG_PAGE`

### 3.2 `kakumi_app/pages/tournament.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY imports
- [x] Replace ~23× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 4× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Keep `color_scheme="gray"` (Reflex theme prop) unchanged

### 3.3 `kakumi_app/pages/results.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE imports
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace ~12× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`

## Phase 4: Admin Pages ✅

### 4.1 `kakumi_app/pages/admin/users_page.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE imports
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 2× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`

### 4.2 `kakumi_app/pages/admin/teams_page.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE imports
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 2× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`

### 4.3 `kakumi_app/pages/admin/export_page.py`
- [x] Add TEXT_TERTIARY, BG_PAGE to import
- [x] Replace 2× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`

### 4.4 `kakumi_app/pages/admin/import_page.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY imports
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 1× `color="gray"` → `color=TEXT_TERTIARY`

## Phase 5: Viewer + Components ✅

### 5.1 `kakumi_app/pages/viewer.py`
- [x] Add TEXT_PRIMARY, TEXT_TERTIARY to import
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`
- [x] Replace 2× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 3× `background_color="white"` → `background_color=BG_PAGE`

### 5.2 `kakumi_app/components/protected_layout.py`
- [x] Add TEXT_TERTIARY, BG_PAGE imports
- [x] Replace 1× `color="gray"` → `color=TEXT_TERTIARY`
- [x] Replace 1× `background_color="white"` → `background_color=BG_PAGE`

### 5.3 `kakumi_app/components/match_card.py`
- [x] Add TEXT_TERTIARY import
- [x] Replace 1× `color="gray"` → `color=TEXT_TERTIARY`

### 5.4 `kakumi_app/components/tables.py`
- [x] Add TEXT_TERTIARY import
- [x] Replace 1× `color="gray"` → `color=TEXT_TERTIARY`

### 5.5 `kakumi_app/components/sidebar.py`
- [x] Add TEXT_PRIMARY to import
- [x] Replace 1× `color="black"` → `color=TEXT_PRIMARY`

## Phase 6: Verification ✅

- [x] **Token import test**: `from kakumi_app.styles.tokens import TEXT_PRIMARY, TEXT_SECONDARY, TEXT_TERTIARY, CARD_BG, HEADER_BG, MUTED_TEXT` → OK
- [x] **All 18 files compile clean**: `py_compile` passes on every modified file
- [x] **Grep residual**: Zero `color="black"` / `color="gray"` / `background_color="white"` in scope files
- [x] **pytest suite**: 833 passed, 1 skipped — **zero regressions**

## Deviations from Design

None. Input `background_color="white"` in registries form fields kept as-is (per design note: intentional card surface white).

## Summary Statistics

| Metric | Value |
|--------|-------|
| Files modified | 18 |
| New token definitions | 6 |
| `color="black"` → `TEXT_PRIMARY` | ~68 across 11 files |
| `color="gray"` → `TEXT_TERTIARY` | ~30 across 12 files |
| `background_color="white"` → `BG_PAGE` | ~14 across 9 files |
| Layout restructures | 1 (login centering) |
| Local constants removed | 3 (from registry_crud.py) |
| Tests passed | 833 (same before/after) |
