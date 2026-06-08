# Viewer QR Code — Implementation Tasks

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~200 (prod: ~90, tests: ~110) |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

```
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

## Dependency Map

```
Task 1.1 (model field)     → prereq for 1.4 (migration)
Task 1.2 (service bugs)    → prereq for 2.4 (state handlers)
Task 1.3 (viewer_state B5) → prereq for 3.2 (query param extraction)
Task 1.4 (migration)       → depends on 1.1
Task 1.5 (service tests)   → verify 1.2
Task 2.1 (reqs)            → prereq for 2.2 (qr_helper)
Task 2.2 (qr_helper)       → prereq for 2.4 (state handlers)
Task 2.3 (qr_helper tests) → verify 2.2
Task 2.4 (state handlers)  → depends on 1.2, 2.1, 2.2
Task 2.5 (state tests)     → verify 2.4
Task 3.1 (UI card)         → depends on 2.4
Task 3.2 (query param)     → depends on 1.3
Task 3.3 (viewer tests)    → verify 3.2
Task 3.4 (manual verify)   → depends on all
```

The 7-step rollout from design.md maps to:
- **Steps 1-2** → Task group 1 (bug fixes + model + migration + tests)
- **Steps 3-4** → Task group 2 (QR infra + state handlers + tests)
- **Steps 5-7** → Task group 3 (UI card + query param + full flow)

---

## STRICT TDD MODE

Every code task must follow: **RED → GREEN → TRIANGULATE → REFACTOR**

1. Write failing test(s) first
2. Write minimal production code to pass
3. Add edge-case tests
4. Refactor while keeping tests green

Test runner: `python -m pytest tests -v`

---

## Task Group 1 — Bug Fixes + Model (Steps 1-2)

- [x] Task 1.1 — Add `viewer_code_generated_at` to Tournament model
- [x] Task 1.2 — Fix bugs B1-B4 in `viewer_service.py`
- [x] Task 1.3 — Fix B5 (double `@rx.event`) in `viewer_state.py`
- [x] Task 1.4 — Create Alembic migration for new column
- [x] Task 1.5 — Write tests for viewer_service fixes
- [x] Task 2.1 — Add `qrcode[pil]` to requirements.txt
- [x] Task 2.2 — Create `qr_helper.py`
- [x] Task 2.3 — Write tests for qr_helper
- [x] Task 2.4 — Add QR state vars + handlers to TournamentState
- [x] Task 2.5 — Write tests for TournamentState QR handlers
- [x] Task 3.1 — Add `_qr_card()` to tournament workspace
- [x] Task 3.2 — Add `?code=` query param extraction in ViewerState
- [x] Task 3.3 — Write tests for viewer_state QR integration
- [x] Task 3.4 — Verify full flow (manual)

### Task 1.1 — Add `viewer_code_generated_at` to Tournament model

**File:** `kakumi_app/models/tournament_model.py`

**Change:** Add field after `viewer_code` (line 169):

```python
viewer_code: Optional[str] = Field(default=None, max_length=8)
viewer_code_generated_at: Optional[datetime.datetime] = Field(default=None)
```

**Import needed:** `datetime` already imported at top.

**Verify:**
- Model compiles: `python -c "from kakumi_app.models.tournament_model import Tournament; print(hasattr(Tournament, 'viewer_code_generated_at'))"`
- Field type is `Optional[datetime.datetime]`
- Default is `None` (nullable)
- No existing code references broken (other modules don't import this field yet)

**Depends on:** nothing
**Prereq for:** 1.4, 1.5

---

### Task 1.2 — Fix bugs B1-B4 in `viewer_service.py`

**File:** `kakumi_app/services/viewer_service.py`

**TDD:** Write test 1.5 first (RED), then fix code (GREEN), then triangulate.

**Changes (all in one edit):**

| # | Where | Old | New |
|---|-------|-----|-----|
| B3 | Line 17 | `EXPIRATION_DAYS = 30` | `EXPIRATION_HOURS = 5` |
| B2/B4 | Lines 27-31 | `if tournament.viewer_code_generated_at is None: return False` and `age.days` | `return True` for NULL, `age.total_seconds()` |
| B1 | Line 1 | no import | `import secrets` at top |
| B1 | Line 76 | `new_code = Tournament.generate_viewer_code()` | `new_code = secrets.token_hex(4)` |
| B2 | Line 78 | — unchanged, but now `viewer_code_generated_at` exists on model | works |

**Full `_is_code_expired` after fix:**

```python
@staticmethod
def _is_code_expired(tournament: Tournament) -> bool:
    if tournament.viewer_code_generated_at is None:
        return True
    age = datetime.datetime.utcnow() - tournament.viewer_code_generated_at
    return age.total_seconds() > ViewerService.EXPIRATION_HOURS * 3600
```

**Verify:**
- `python -c "from kakumi_app.services.viewer_service import ViewerService; print(ViewerService.EXPIRATION_HOURS)"` → 5
- `ruff check kakumi_app/services/viewer_service.py`
- All tests in Task 1.5 pass

**Depends on:** Task 1.1 (model field must exist)
**Prereq for:** Task 2.4

---

### Task 1.3 — Fix B5 (double `@rx.event`) in `viewer_state.py`

**File:** `kakumi_app/states/viewer_state.py`

**Change at lines 136-138:**

```python
# OLD:
    @rx.event
    @rx.event
    async def load_viewer_dashboard(self) -> Any:

# NEW:
    @rx.event
    async def load_viewer_dashboard(self) -> Any:
```

**Verify:**
- `ruff check kakumi_app/states/viewer_state.py`
- `python -c "from kakumi_app.states.viewer_state import ViewerState; print('OK')"`
- Task 3.3 tests cover this

**Depends on:** nothing
**Prereq for:** Task 3.2

---

### Task 1.4 — Create Alembic migration for new column

**New file:** `alembic/versions/b8d4e6f2a9c1_add_viewer_code_generated_at.py`

**Migration chain:**
- `down_revision = "a1b2c3d4e5f6"` (current head — add_force_password_change)
- `revision = "b8d4e6f2a9c1"`

**Migration content:**

```python
"""add viewer_code_generated_at to tournaments

Revision ID: b8d4e6f2a9c1
Revises: a1b2c3d4e5f6
Create Date: 2026-06-06
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision: str = "b8d4e6f2a9c1"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("viewer_code_generated_at", sa.DateTime(), nullable=True)
        )

def downgrade() -> None:
    with op.batch_alter_table("tournaments", schema=None) as batch_op:
        batch_op.drop_column("viewer_code_generated_at")
```

**Verify:**
- `alembic upgrade head` — applies cleanly
- `alembic downgrade -1` — drops column
- `alembic upgrade head` — reapplies (roundtrip verified)
- Check column exists: `sqlite3 kakumi.db ".schema tournaments" | grep viewer_code_generated_at`

**Depends on:** Task 1.1

---

### Task 1.5 — Write tests for viewer_service fixes

**New file:** `tests/test_viewer_service.py`

**Test categories (all in one file):**

#### Tests for `_is_code_expired()`:

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 1 | `test_is_code_expired_within_5h` | code 4.5h old → False | Unit |
| 2 | `test_is_code_expired_exactly_at_5h` | code 5h+1s old → True | Unit |
| 3 | `test_is_code_expired_null` | NULL timestamp → True | Unit |
| 4 | `test_is_code_expired_fresh` | code 1min old → False | Unit |

#### Tests for `generate_viewer_code()`:

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 5 | `test_generate_viewer_code_success` | valid ID → returns 8-char hex, saves to DB | Integration |
| 6 | `test_generate_viewer_code_not_found` | bogus ID → None | Integration |
| 7 | `test_generate_viewer_code_format` | matches `^[0-9a-f]{8}$` | Integration |

#### Tests for `validate_viewer_code()`:

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 8 | `test_validate_viewer_code_valid` | valid code + within 5h → returns tournament | Integration |
| 9 | `test_validate_viewer_code_nonexistent` | code not in DB → None, records attempt | Integration |
| 10 | `test_validate_viewer_code_expired` | code 6h old → None | Integration |
| 11 | `test_validate_viewer_code_locked` | 5+ fails within 5min → None | Unit |

#### Tests for `check_viewer_access()`:

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 12 | `test_check_viewer_access_correct` | valid code + matching tournament → True | Integration |
| 13 | `test_check_viewer_access_wrong_tournament` | valid code + wrong tournament → False | Integration |

**Testing patterns from conftest.py to use:**
- `db_session` fixture (autouse) — provides isolated SQLite DB per test
- `sample_tournament` fixture — creates tournament with known ID
- For unit tests: create `Tournament` objects directly, no DB needed
- For integration tests: use `rx.session()` which is monkeypatched

**Verify:**
- `python -m pytest tests/test_viewer_service.py -v` — all 13 tests pass

**Depends on:** Tasks 1.1, 1.2
**Verifies:** Task 1.2

---

## Task Group 2 — QR Infrastructure (Steps 3-4)

### Task 2.1 — Add `qrcode[pil]` to requirements.txt

**File:** `requirements.txt`

**Change:** Add `qrcode[pil]==8.1.0` after the `pillow` line:

```
pillow==12.2.0
qrcode[pil]==8.1.0
```

**Verify:**
- `pip install -r requirements.txt` — installs cleanly
- `python -c "import qrcode; print(qrcode.__version__)"` — ≥ 8.1.0
- `python -c "import qrcode; img = qrcode.make('test'); print(type(img))"` — `<class 'PIL.Image.Image'>`

**Depends on:** nothing
**Prereq for:** Task 2.2

---

### Task 2.2 — Create `qr_helper.py`

**New file:** `kakumi_app/services/qr_helper.py`

**TDD:** Write failing test(s) first (Task 2.3), then implement.

```python
"""
QR Code generation helper.
Produces SSR-safe data URIs with no file I/O.
"""

from io import BytesIO
import base64

import qrcode


def _make_qr_data_url(url: str) -> str:
    """Generate a QR code image and return as base64 data URI.

    Args:
        url: URL string to encode in QR.

    Returns:
        Data URI string: data:image/png;base64,<encoded>
    """
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
```

**Verify:**
- `python -c "from kakumi_app.services.qr_helper import _make_qr_data_url; uri = _make_qr_data_url('/viewer/dashboard/1?code=test'); print(uri[:30])"` → `data:image/png;base64,`
- `ruff check kakumi_app/services/qr_helper.py`
- All tests in Task 2.3 pass

**Depends on:** Task 2.1
**Prereq for:** Task 2.4

---

### Task 2.3 — Write tests for qr_helper

**New file:** `tests/test_qr_helper.py`

**Tests:**

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 1 | `test_make_qr_data_url_returns_data_uri` | Output starts with `data:image/png;base64,` | Unit |
| 2 | `test_make_qr_data_url_valid_base64` | Decoded content is valid PNG (header `\x89PNG`) | Unit |
| 3 | `test_make_qr_data_url_no_file_io` | No file writes (monkeypatch `open` if needed) | Unit |
| 4 | `test_make_qr_data_url_deterministic` | Same URL → same output | Unit |
| 5 | `test_make_qr_encodes_correct_url` | URL `/viewer/dashboard/42?code=a1b2c3d4` encodes in QR | Unit |
| 6 | `test_make_qr_empty_url` | Empty string returns valid data URI | Unit |
| 7 | `test_make_qr_special_chars` | URL with special chars works | Unit |

**Pattern:**
- Use `base64.b64decode()` to verify PNG header bytes
- Compare outputs for deterministic test
- Mock `qrcode.make()` if needed for unit isolation, or use real `qrcode` (preferred since it's a dependency)

**Verify:**
- `python -m pytest tests/test_qr_helper.py -v` — all tests pass

**Depends on:** Task 2.2
**Verifies:** Task 2.2

---

### Task 2.4 — Add QR state vars + handlers to TournamentState

**File:** `kakumi_app/states/tournament_state.py`

**TDD:** Write failing tests first (Task 2.5), then implement.

**Changes in one edit block:**

**A) Add imports at top (after existing imports):**

```python
import datetime
from kakumi_app.services.viewer_service import ViewerService
from kakumi_app.services.qr_helper import _make_qr_data_url
```

**B) Add QR state vars after existing class vars (around line 45, after `validation_warnings`):**

```python
    # ── QR state vars ──────────────────────────────────
    qr_data_url: str = ""
    qr_code_text: str = ""
    qr_generated_at: str = ""
    qr_expires_at: str = ""
```

**C) Add handlers after `cancel_tournament` (before the last line of class):**

```python
    # ── QR event handlers ──────────────────────────

    @rx.event
    async def generate_qr(self) -> None:
        """Generate viewer code + QR for current tournament."""
        tournament_id = self._get_tournament_id()
        if tournament_id is None:
            yield rx.toast.error("No tournament selected")
            return

        code = ViewerService.generate_viewer_code(tournament_id)
        if code is None:
            yield rx.toast.error("Could not generate viewer code")
            return

        url = f"/viewer/dashboard/{tournament_id}?code={code}"
        data_uri = _make_qr_data_url(url)

        now = datetime.datetime.utcnow()
        expires = now + datetime.timedelta(hours=5)

        self.qr_data_url = data_uri
        self.qr_code_text = code
        self.qr_generated_at = now.strftime("%Y-%m-%d %H:%M UTC")
        self.qr_expires_at = expires.strftime("%Y-%m-%d %H:%M UTC")

        yield rx.toast.success("QR generado")

    @rx.event
    async def regenerate_qr(self) -> None:
        """Regenerate viewer code + QR (invalidates previous code)."""
        async for event in self.generate_qr():
            yield event
```

**Verify:**
- `ruff check kakumi_app/states/tournament_state.py`
- `python -c "from kakumi_app.states.tournament_state import TournamentState; print([v for v in dir(TournamentState) if 'qr' in v.lower()])"` — shows all 4 vars + 2 handlers
- All tests in Task 2.5 pass

**Depends on:** Tasks 1.2 (ViewerService fixed), 2.2 (qr_helper exists)
**Prereq for:** Tasks 2.5, 3.1

---

### Task 2.5 — Write tests for TournamentState QR handlers

**New file:** `tests/test_tournament_state_qr.py`

**Tests:**

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 1 | `test_generate_qr_default_state` | New TournamentState → all QR vars empty | Integration |
| 2 | `test_generate_qr_success` | Tournament selected → vars populated, data URI valid | Integration |
| 3 | `test_generate_qr_no_tournament` | No current_tournament → error toast, vars stay empty | Integration |
| 4 | `test_regenerate_qr_new_code` | Regenerate → new code differs from previous | Integration |
| 5 | `test_regenerate_qr_old_code_invalid` | Old code no longer validates after regenerate | Integration |
| 6 | `test_generate_qr_expiry_correct` | `qr_expires_at` is 5h after `qr_generated_at` | Integration |

**Pattern:**
- Create `TournamentState` instance with mock `current_tournament`
- Call `generate_qr()` and inspect state vars
- Use `db_session` fixture for DB access
- For no-tournament test: ensure `current_tournament` is None

**Verify:**
- `python -m pytest tests/test_tournament_state_qr.py -v` — all 6 tests pass

**Depends on:** Task 2.4
**Verifies:** Task 2.4

---

## Task Group 3 — UI + Viewer Integration (Steps 5-7)

### Task 3.1 — Add `_qr_card()` to tournament workspace

**File:** `kakumi_app/pages/tournament.py`

**TDD:** This is UI — verify via `reflex run` visual inspection (no test framework for components).

**A) Add `_qr_card()` function after `_tatami_card()` (before `tournament()` fn):**

```python
def _qr_card() -> rx.Component:
    """Render QR generation card in tournament workspace."""
    state = TournamentState
    return rx.card(
        rx.vstack(
            rx.heading("QR de Espectadores", size="5", color=TEXT_PRIMARY),
            rx.text(
                "Genera un código QR para que los espectadores accedan "
                "al dashboard del torneo.",
                color=TEXT_TERTIARY,
            ),
            rx.cond(
                state.qr_data_url != "",
                rx.vstack(
                    rx.image(
                        src=state.qr_data_url,
                        width="200px",
                        height="200px",
                    ),
                    rx.text(
                        f"Código: {state.qr_code_text}",
                        color=TEXT_PRIMARY,
                    ),
                    rx.text(
                        f"Expira: {state.qr_expires_at}",
                        color=TEXT_TERTIARY,
                        font_size="sm",
                    ),
                    rx.button(
                        "Regenerar QR",
                        on_click=state.regenerate_qr,
                        variant="outline",
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                rx.vstack(
                    rx.button(
                        "Generar QR",
                        on_click=state.generate_qr,
                        disabled=~state.has_selected_tournament,
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        width="100%",
    )
```

**B) Add `_qr_card()` to the grid in `tournament()` function:**

```python
# OLD — line ~329:
rx.grid(
    _selector_card(),
    _lifecycle_card(),
    _categories_card(),
    _tatami_card(),
    columns="2",
    spacing="4",
    width="100%",
),

# NEW:
rx.grid(
    _selector_card(),
    _lifecycle_card(),
    _categories_card(),
    _tatami_card(),
    _qr_card(),
    columns="2",
    spacing="4",
    width="100%",
),
```

**Import check:** `TournamentState` is already imported at top of file.

**Verify:**
- `ruff check kakumi_app/pages/tournament.py`
- `reflex run` — workspace loads, 5th card appears in grid
- No QR: shows "Generar QR" button (disabled when no tournament)
- Generate QR → shows QR image + code + expiry + "Regenerar QR"

**Depends on:** Task 2.4

---

### Task 3.2 — Add `?code=` query param extraction in ViewerState

**File:** `kakumi_app/states/viewer_state.py`

**TDD:** Write failing test(s) first (Task 3.3), then implement.

**Change in `load_viewer_dashboard()`:**

```python
    @rx.event
    async def load_viewer_dashboard(self) -> Any:
        """Load tournament from route param for dashboard on_load."""
        # Extract ?code= query param (critical gap fix)
        self.viewer_code = self.router.page.params.get("code", "")

        tournament_id = self.router.page.params.get("tournament_id")
        if tournament_id:
            return await self.load_tournament_by_id(int(tournament_id))
        return rx.redirect("/viewer")
```

**Note:** Task 1.3 already removed the duplicate `@rx.event` — this edit goes after that fix.

**Verify:**
- `ruff check kakumi_app/states/viewer_state.py`
- All tests in Task 3.3 pass

**Depends on:** Task 1.3 (B5 fix applied first)

---

### Task 3.3 — Write tests for viewer_state QR integration

**New file:** `tests/test_viewer_state_qr.py`

**Tests:**

| # | Test name | Scenario | Type |
|---|-----------|----------|------|
| 1 | `test_load_dashboard_extracts_code_param` | Mock router params → `viewer_code` set to code value | Unit |
| 2 | `test_load_dashboard_no_code_param` | Empty router params → `viewer_code` = `""` | Unit |
| 3 | `test_load_dashboard_valid_code` | Valid code + matching tournament → dashboard loads | Integration |
| 4 | `test_load_dashboard_invalid_code` | Invalid code → redirect to `/viewer` | Integration |
| 5 | `test_double_event_decorator_removed` | `load_viewer_dashboard` has exactly one `@rx.event` | Unit |

**Pattern for testing router params:**
- Monkeypatch `self.router.page.params` before calling handler
- For unit tests, instantiate `ViewerState` directly and set `router` mock
- For integration tests, use `db_session` fixture + `sample_tournament` fixture

**Verify:**
- `python -m pytest tests/test_viewer_state_qr.py -v` — all 5 tests pass

**Depends on:** Tasks 1.3, 3.2
**Verifies:** Tasks 1.3, 3.2

---

### Task 3.4 — Verify full flow (manual spot-check)

**No code changes.** Manual verification after `reflex run`.

**Checklist:**

1. Admin opens tournament workspace → sees QR card with "Generar QR" button (disabled if no tournament selected)
2. Select tournament → "Generar QR" enabled
3. Click "Generar QR" → QR image appears with code text + expiry
4. QR scan (or open URL manually) → `/viewer/dashboard/{id}?code={code}` → dashboard loads categories
5. After 5h window (or set tournament `viewer_code_generated_at` 6h ago in DB) → QR scan redirects to `/viewer`
6. Click "Regenerar QR" → new code displayed, old code invalidated
7. `python -m pytest tests -v` — all tests pass

**Depends on:** All prior tasks

---

## Rollback Per Task

| Task | Rollback |
|------|----------|
| 1.1 | `git checkout -- kakumi_app/models/tournament_model.py` |
| 1.2 | `git checkout -- kakumi_app/services/viewer_service.py` |
| 1.3 | `git checkout -- kakumi_app/states/viewer_state.py` |
| 1.4 | `alembic downgrade -1` + delete migration file |
| 1.5 | `rm tests/test_viewer_service.py` |
| 2.1 | `git checkout -- requirements.txt` |
| 2.2 | `rm kakumi_app/services/qr_helper.py` |
| 2.3 | `rm tests/test_qr_helper.py` |
| 2.4 | `git checkout -- kakumi_app/states/tournament_state.py` |
| 2.5 | `rm tests/test_tournament_state_qr.py` |
| 3.1 | `git checkout -- kakumi_app/pages/tournament.py` |
| 3.2 | `git checkout -- kakumi_app/states/viewer_state.py` |
| 3.3 | `rm tests/test_viewer_state_qr.py` |
| 3.4 | No rollback needed (verification only) |

## Files Created vs Modified

| Action | File |
|--------|------|
| Modify | `kakumi_app/models/tournament_model.py` |
| Modify | `kakumi_app/services/viewer_service.py` |
| Modify | `kakumi_app/states/viewer_state.py` |
| Modify | `kakumi_app/states/tournament_state.py` |
| Modify | `kakumi_app/pages/tournament.py` |
| Modify | `requirements.txt` |
| Create | `kakumi_app/services/qr_helper.py` |
| Create | `alembic/versions/b8d4e6f2a9c1_add_viewer_code_generated_at.py` |
| Create | `tests/test_viewer_service.py` |
| Create | `tests/test_qr_helper.py` |
| Create | `tests/test_tournament_state_qr.py` |
| Create | `tests/test_viewer_state_qr.py` |
