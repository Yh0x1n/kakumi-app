# Apply Progress — Groups 1, 2, and 3 Complete

## Status

All 13 tasks complete. Group 3 done. Ready for verify and manual flow check (Task 3.4).

## Completed Tasks

### Group 1 — Bug Fixes + Model (Steps 1-2)

#### Task 1.1 — Add `viewer_code_generated_at` to Tournament model
- **File:** `kakumi_app/models/tournament_model.py`
- **Change:** Added `viewer_code_generated_at: Optional[datetime.datetime] = Field(default=None)` after `viewer_code`
- **Verified:** `hasattr(Tournament, 'viewer_code_generated_at')` → True
- **Tasks.md:** `- [x]` checked

#### Task 1.2 — Fix bugs B1-B4 in viewer_service.py (GREEN)
- **File:** `kakumi_app/services/viewer_service.py`
- **Changes:**
  - B1: Added `import secrets`, replaced `Tournament.generate_viewer_code()` → `secrets.token_hex(4)`
  - B2: `_is_code_expired` returns True for NULL timestamp (was False)
  - B3: `EXPIRATION_DAYS = 30` → `EXPIRATION_HOURS = 5`
  - B4: `age.days > EXPIRATION_DAYS` → `age.total_seconds() > EXPIRATION_HOURS * 3600`
- **Tasks.md:** `- [x]` checked

#### Task 1.3 — Fix B5 (double @rx.event)
- **File:** `kakumi_app/states/viewer_state.py`
- **Change:** Removed duplicate `@rx.event` at `load_viewer_dashboard`
- **Tasks.md:** `- [x]` checked

#### Task 1.4 — Alembic migration
- **File:** `alembic/versions/b8d4e6f2a9c1_add_viewer_code_generated_at.py` (new)
- **Chain:** `a1b2c3d4e5f6` → `b8d4e6f2a9c1`
- **Verified roundtrip:** Upgrade → Downgrade → Re-upgrade
- **Tasks.md:** `- [x]` checked

#### Task 1.5 — Write tests for viewer_service fixes (RED first)
- **File:** `tests/test_viewer_service.py` (new)
- **Tests:** 13 tests covering `_is_code_expired`, `generate_viewer_code`, `validate_viewer_code`, `check_viewer_access`
- **Tasks.md:** `- [x]` checked

### Group 2 — QR Infrastructure (Steps 3-4)

#### Task 2.1 — Add qrcode[pil] to requirements.txt
- **File:** `requirements.txt`
- **Change:** Added `qrcode[pil]==8.1.0` after `pillow==12.2.0`
- **Tasks.md:** `- [x]` checked

#### Task 2.2 — Create qr_helper.py (GREEN)
- **File:** `kakumi_app/services/qr_helper.py` (new)
- **Implementation:** `_make_qr_data_url()` pure function
- **Tasks.md:** `- [x]` checked

#### Task 2.3 — Write tests for qr_helper (RED first)
- **File:** `tests/test_qr_helper.py` (new)
- **Tests:** 6 tests covering data URI format, valid PNG, deterministic, URL content, empty URL, special chars
- **Tasks.md:** `- [x]` checked

#### Task 2.4 — Add QR state vars + handlers to TournamentState (GREEN)
- **File:** `kakumi_app/states/tournament_state.py`
- **Changes:** Added 4 QR state vars, 2 event handlers (`generate_qr`, `regenerate_qr`)
- **Tasks.md:** `- [x]` checked

#### Task 2.5 — Write tests for TournamentState QR handlers (RED first)
- **File:** `tests/test_tournament_state_qr.py` (new)
- **Tests:** 6 tests covering default state, success, no-tournament, expiry, regeneration, old code invalidation
- **Tasks.md:** `- [x]` checked

### Group 3 — UI + Viewer Integration (Steps 5-7)

#### Task 3.3 — Write tests for viewer_state QR integration (RED first)
- **File:** `tests/test_viewer_state_qr.py` (new)
- **Tests:** 5 tests
  - `test_load_dashboard_extracts_code_param` — router params → viewer_code set
  - `test_load_dashboard_no_code_param` — empty params → viewer_code empty
  - `test_load_dashboard_valid_code` — valid code + tournament → loads dashboard
  - `test_load_dashboard_invalid_code` — invalid code → access_denied
  - `test_double_event_decorator_removed` — single `@rx.event` guard
- **RED phase:** 2 failures (tests 1 and 3 — ?code= extraction missing)
- **Tasks.md:** `- [x]` checked

#### Task 3.2 — Add `?code=` query param extraction (GREEN)
- **File:** `kakumi_app/states/viewer_state.py`
- **Change:** Added `self.viewer_code = self.router.page.params.get("code", "")` as first line of `load_viewer_dashboard()`
- **GREEN:** all 5 tests pass
- **Tasks.md:** `- [x]` checked

#### Task 3.1 — Add `_qr_card()` to tournament workspace
- **File:** `kakumi_app/pages/tournament.py`
- **Changes:**
  - New `_qr_card()` function after `_tatami_card()` with QR display (cond: generated vs empty)
  - Added `_qr_card()` to the grid in `tournament()` function
- **Verified:** `ruff check` clean, module imports OK
- **Tasks.md:** `- [x]` checked

## TDD Cycle Evidence

| Cycle | RED | GREEN | Pass |
|-------|-----|-------|------|
| `_is_code_expired` fixes (B2/B4) | 3 fail | `EXPIRATION_HOURS`, NULL→True, `total_seconds()` | ✅ |
| `generate_viewer_code` fix (B1) | 2 fail (AttributeError) | `secrets.token_hex(4)` | ✅ |
| `_make_qr_data_url` | 6 fail (ModuleNotFound) | qrcode.make + base64 | ✅ |
| `generate_qr` / `regenerate_qr` | 6 fail (AttributeError) | QR vars + handlers | ✅ |
| `?code=` extraction | 2 fail (assert viewer_code) | `self.router.page.params.get("code", "")` | ✅ |

## Files Changed (All Groups)

| Action | File |
|--------|------|
| Modified | `kakumi_app/models/tournament_model.py` |
| Modified | `kakumi_app/services/viewer_service.py` |
| Modified | `kakumi_app/states/viewer_state.py` |
| Modified | `kakumi_app/states/tournament_state.py` |
| Modified | `kakumi_app/pages/tournament.py` |
| Modified | `requirements.txt` |
| Created | `kakumi_app/services/qr_helper.py` |
| Created | `alembic/versions/b8d4e6f2a9c1_add_viewer_code_generated_at.py` |
| Created | `tests/test_viewer_service.py` |
| Created | `tests/test_qr_helper.py` |
| Created | `tests/test_tournament_state_qr.py` |
| Created | `tests/test_viewer_state_qr.py` |

## Full Suite Status

`python -m pytest tests -v` → **873 passed, 1 skipped, 0 failed** ✅

## Remaining Task

- [ ] Task 3.4 — Verify full flow (manual spot-check)
