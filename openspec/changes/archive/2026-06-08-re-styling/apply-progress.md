# Apply Progress — re-styling

## Task 0: Baseline tests ✅
- `python -m pytest tests -v` → 915 passed, 1 skipped

## Task 1: Dark theme already set ✅
- `kakumi_app.py` already had `rx.theme(appearance="dark")` — no change needed

## Task 2: Simple component files ✅
- `components/tables.py` — removed TEXT_TERTIARY import + usage
- `components/match_card.py` — removed TEXT_TERTIARY import + usage
- `components/protected_layout.py` — removed TEXT_TERTIARY, BG_PAGE import + usages

## Task 3: Auth + import-only admin pages ✅
- `pages/auth/login.py` — removed BG_PAGE, TEXT_TERTIARY, TEXT_PRIMARY import + usages
- `pages/auth/change_password.py` — removed BG_PAGE, CARD_BG, TEXT_TERTIARY import + usages
- `pages/admin/import_page.py` — removed TEXT_PRIMARY, TEXT_TERTIARY import + usages
- `pages/admin/export_page.py` — removed 6 token imports + usages

## Task 4: Admin medium-complexity pages ✅
- `pages/admin/users_page.py` — removed TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE import + usages
- `pages/admin/teams_page.py` — removed TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE import + usages

## Task 5: Pages with text-only tokens ✅
- `pages/tournament.py` — removed TEXT_PRIMARY, TEXT_TERTIARY import + usages
- `pages/viewer.py` — removed BG_CARD_ALT, BG_PAGE, TEXT_PRIMARY, TEXT_TERTIARY import + usages
- `pages/exhibition.py` — removed BG_PAGE, TEXT_PRIMARY import + usages

## Task 6: Root kakumi_app.py ✅
- Removed BG_PAGE, HOVER_GRAY, TEXT_PRIMARY import + usages including border_color="black" and hover style

## Task 7: date_calendar.py ✅
- Changed trigger border: `"1px solid black"` → `"1px solid white"`
- Removed `background_color="white"` from trigger style dict
- Popover overlay left unchanged (white popup on dark bg)

## Task 8: results.py ✅
- Removed TEXT_PRIMARY, TEXT_TERTIARY, BG_PAGE import + usages
- Changed `border="1px solid #e2e8f0"` → `border="1px solid white"`

## Task 9: registries.py (heaviest) ✅
- Removed MUTED_TEXT, TEXT_PRIMARY import + usages (~45 prop removals)
- Changed 14 borders: `"1px solid black"` → `"1px solid white"`

## Task 10: registry_crud.py ✅
- Kept BRAND_RED, BRAND_RED_HOVER; removed 6 light tokens
- 5 borders adapted from BORDER_LIGHT f-strings to `"1px solid white"`
- Removed hardcoded `color="#1a1c1c"` and `background_color="#e8e8e8"`

## Task 11: Integration smoke test ✅
- `python -m pytest tests -v` → 915 passed, 1 skipped
- Sidebar icon fix: changed `color=TEXT_PRIMARY` → `color="white"` in trigger button

## Summary

| Metric | Value |
|--------|-------|
| Files modified | 17 |
| Lines added | 168 |
| Lines removed | 359 |
| Tests | 915 passed, 1 skipped |
| Sidebar, dark pages, buttons | Untouched |
| tokens.py | Untouched |
