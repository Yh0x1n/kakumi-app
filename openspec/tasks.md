# Tasks: Dashboard Winner Result Cards

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~220–280 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | single PR |
| Delivery strategy | single-pr |
| Chain strategy | pending |

```text
Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low
```

**Estimate breakdown:**
- `ResultsService.get_recent_winners()` — ~50 lines (method + import)
- `DashboardState` — ~35 lines (new file)
- `kakumi_app.py` edits — ~15 lines (import, template, on_load)
- Tests — ~130–180 lines (service tests + state tests)
- **Total: ~230–280 lines** — well under 400. Single PR.

---

## Strict TDD Sequence

All tasks follow **RED → GREEN → REFACTOR** per unit. Each task writes tests before implementation. No task depends on unverified work.

---

### Task 1 (RED): Write tests for `ResultsService.get_recent_winners()`

**File:** `tests/test_results_service.py` (append)

**What:** Add test functions that define the expected contract of `get_recent_winners()` before any implementation exists.

**Tests to write:**

| # | Test | Description |
|---|------|-------------|
| 1.1 | `test_get_recent_winners_empty_db` | No tournaments → `[]` |
| 1.2 | `test_get_recent_winners_no_completed_categories` | Tournament exists, categories exist but none COMPLETED → `[]` |
| 1.3 | `test_get_recent_winners_single_kumite` | 1 completed kumite category with winner + match → card with correct winner_name, score (from match aka_score/ao_score), category_name, tournament_name |
| 1.4 | `test_get_recent_winners_single_kata_informal` | 1 completed kata informal category (`KATA_INDIVIDUAL` + `ROUND_ROBIN`) with winner + performance row → score from `final_score` |
| 1.5 | `test_get_recent_winners_limits_to_4` | 6 completed categories → exactly 4 cards returned, ordered by `tc.id DESC` |
| 1.6 | `test_get_recent_winners_filters_incomplete` | Mixed completed/incomplete → only COMPLETED with `first_place_id` appear |
| 1.7 | `test_get_recent_winners_no_match_found_score_zero` | Completed category with winner but no completed match → score `"0"` |
| 1.8 | `test_get_recent_winners_team_modality_score_zero` | Completed team category (`KATA_TEAM` or `KUMITE_TEAM`) with winner → score `"0"` |
| 1.9 | `test_get_recent_winners_kata_elimination_score_from_match` | Completed kata elimination (not ROUND_ROBIN) with winner + match → score from match aka/ao_score |

**Helper to add to test file** (after existing helpers):
- `_create_athlete(name: str) -> Athlete` — create an athlete, return it
- `_create_kata_informal_performance(category_id, athlete_id, final_score) -> None`

**Pattern:** Follow existing patterns in `test_results_service.py`:
- Use `rx.session()` context manager for DB setup
- Assert exact dict shape: `"winner_name"`, `"winner_score"`, `"category_name"`, `"tournament_name"`, `"category_id"`
- Score is always `str` — e.g. `"3"`, `"24.5"`, `"0"`

**Verification:** `python -m pytest tests/test_results_service.py::test_get_recent_winners_empty_db -x -v` fails with `AttributeError` or `NameError` (method doesn't exist yet).

---

### Task 2 (GREEN): Implement `ResultsService.get_recent_winners()`

**File:** `kakumi_app/services/results_service.py`

**What:** Add the method to make Task 1 tests pass.

**Changes:**

1. Add import at top:
```python
from kakumi_app.models.kata_model import KataInformalPerformance
```

2. Add method after the existing `get_statistics_view()`:

```python
@staticmethod
def get_recent_winners() -> list[dict[str, Any]]:
    """Return up to 4 most recently completed category winners.

    Returns a list of dicts with keys:
    winner_name, winner_score (str), category_name, tournament_name, category_id.
    """
    with rx.session() as session:
        rows = session.exec(
            select(
                TournamentCategory.id,
                TournamentCategory.name,
                TournamentCategory.modality,
                TournamentCategory.competition_system,
                TournamentCategory.first_place_id,
                Tournament.name,
            )
            .join(Tournament, Tournament.id == TournamentCategory.tournament_id)
            .where(
                TournamentCategory.status == CategoryStatus.COMPLETED.value,
                TournamentCategory.first_place_id.is_not(None),
            )
            .order_by(TournamentCategory.id.desc())
            .limit(4)
        ).all()

        if not rows:
            return []

        # Collect unique athlete IDs for bulk name lookup
        athlete_ids = {row.first_place_id for row in rows if row.first_place_id}
        athletes_by_id: dict[int, str] = {}
        if athlete_ids:
            athlete_rows = session.exec(
                select(Athlete).where(Athlete.id.in_(athlete_ids))
            ).all()
            for a in athlete_rows:
                athletes_by_id[a.id] = a.name

        results: list[dict[str, Any]] = []
        for row in rows:
            category_id = int(row.id)
            first_place_id = int(row.first_place_id)  # type: ignore[arg-type]
            winner_name = athletes_by_id.get(first_place_id, "")

            # Resolve score
            is_kata_informal = (
                row.modality == Modality.KATA_INDIVIDUAL.value
                and row.competition_system == CompetitionSystem.ROUND_ROBIN.value
            )
            is_team = row.modality in {
                Modality.KATA_TEAM.value,
                Modality.KUMITE_TEAM.value,
            }

            if is_team:
                score = 0
            elif is_kata_informal:
                perf = session.exec(
                    select(KataInformalPerformance)
                    .where(
                        KataInformalPerformance.category_id == category_id,
                        KataInformalPerformance.athlete_id == first_place_id,
                    )
                    .order_by(KataInformalPerformance.id.desc())
                ).first()
                score = perf.final_score if perf else 0.0
            else:
                match = session.exec(
                    select(Match)
                    .where(
                        Match.category_id == category_id,
                        Match.status == MatchStatus.COMPLETED.value,
                        Match.winner_id == first_place_id,
                    )
                    .order_by(Match.id.desc())
                ).first()
                if match:
                    score = (
                        match.aka_score
                        if match.winner_id == match.aka_id
                        else match.ao_score
                    )
                else:
                    score = 0

            results.append(
                {
                    "winner_name": winner_name,
                    "winner_score": str(score),
                    "category_name": row.name,
                    "tournament_name": row[5],  # Tournament.name from the join
                    "category_id": category_id,
                }
            )

        return results
```

**Design notes:**
- Uses `select()` with `.join()` for a single query instead of sub-queries per row for the main data.
- Athlete names resolved via bulk query (same pattern as `get_podiums_view()`).
- Per-row score resolution hits `KataInformalPerformance` or `Match` tables on demand — this is acceptable for max 4 rows.
- `row[5]` accesses the joined `Tournament.name` column. ✅ Pattern used elsewhere.

**Verification:** All tests from Task 1 pass:
```bash
python -m pytest tests/test_results_service.py -x -v
```

---

### Task 3 (RED): Write tests for `DashboardState`

**File (new):** `tests/test_dashboard_state.py`

**What:** Define the contract for `DashboardState` before creating it.

**Tests:**

```python
"""Tests for dashboard state."""

from __future__ import annotations

import pytest
import reflex as rx

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    CategoryStatus,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Tournament,
    TournamentCategory,
)
from kakumi_app.services.results_service import ResultsService


# --- Helper to create test data ---

def _create_tournament(name: str) -> Tournament:
    with rx.session() as session:
        t = Tournament(
            name=name,
            venue="Dojo Test",
            start_date=datetime.date(2026, 7, 1),
            end_date=datetime.date(2026, 7, 2),
            tatami_count=1,
            status="PLANIFICADO",
            is_public=True,
        )
        session.add(t)
        session.commit()
        session.refresh(t)
        return t


def _create_athlete(name: str) -> Athlete:
    with rx.session() as session:
        a = Athlete(
            name=name,
            age=25,
            gender="MALE",
            email=f"{name.lower().replace(' ', '.')}@test.local",
            license_number=f"LIC-{name.upper().replace(' ', '-')}",
        )
        session.add(a)
        session.commit()
        session.refresh(a)
        return a


# --- Tests ---

class TestDashboardStateLoadRecentWinners:
    """DashboardState.load_recent_winners delegates to ResultsService."""

    def test_load_recent_winners_sets_cards(self):
        """After calling load_recent_winners, winner_cards should reflect service output."""
```

**Key test scenarios:**

| # | Test | Assertion |
|---|------|-----------|
| 3.1 | `test_load_recent_winners_empty` | Called with no data → `winner_cards == []`, `is_loading == False` |
| 3.2 | `test_load_recent_winners_populates_cards` | DB has 2 winners → `len(winner_cards) == 2`, fields match |
| 3.3 | `test_load_recent_winners_handles_error` | Monkeypatch service to raise → `winner_cards == []`, `is_loading == False` |

**Pattern:** Follow `test_competition_category_state.py` patterns:
- Use `rx.session()` for DB setup
- Instantiate state: `state = DashboardState()`
- Call event: `await DashboardState.load_recent_winners.fn(state)`
- Assert state vars after event

**Verification:** `python -m pytest tests/test_dashboard_state.py -x -v` fails with `ImportError` (DashboardState doesn't exist yet).

---

### Task 4 (GREEN): Create `DashboardState`

**File (new):** `kakumi_app/states/dashboard_state.py`

**What:** Thin state wrapper that delegates to `ResultsService.get_recent_winners()`.

```python
"""Reflex state for the authenticated dashboard (route /home)."""

from __future__ import annotations

import logging
from typing import Any

import reflex as rx

from kakumi_app.services.results_service import ResultsService

logger = logging.getLogger(__name__)


class DashboardState(rx.State):
    """State container for the authenticated dashboard (route /home)."""

    winner_cards: list[dict[str, Any]] = []
    is_loading: bool = False

    @rx.event
    async def load_recent_winners(self) -> None:
        """Fetch up to 4 recent winner cards from results service."""
        self.is_loading = True
        try:
            self.winner_cards = ResultsService.get_recent_winners()
        except Exception:
            logger.exception("Error loading recent winners")
            self.winner_cards = []
        finally:
            self.is_loading = False
```

**Verification:** All tests from Task 3 pass:
```bash
python -m pytest tests/test_dashboard_state.py -x -v
```

---

### Task 5 (GREEN): Wire `on_load` and update `dashboard()` UI template

**File:** `kakumi_app/kakumi_app.py`

**What:** Three precise edits:

**5a — Add import** (after existing state imports, alphabetical):
```python
from .states.dashboard_state import DashboardState
```

**5b — Replace the `dashboard()` grid template:**

**Before:**
```python
        rx.center(
            rx.grid(
                rx.foreach(
                    rx.Var.range(4),
                    lambda i: rx.card(
                        rx.link(
                            rx.text(
                                f"Resultado {i + 1}",
                                weight="bold",
                                font_size="10",
                            ),
                            underline="none",
                            height="100%",
                        ),
                        border_width="thick",
                        border_radius="1em",
                    ),
                ),
                columns="2",
                spacing="4",
                width="50%",
                padding="0.5em",
            ),
        ),
```

**After:**
```python
        rx.center(
            rx.cond(
                DashboardState.winner_cards.length() > 0,
                rx.grid(
                    rx.foreach(
                        DashboardState.winner_cards,
                        lambda card: rx.card(
                            rx.vstack(
                                rx.text(card["winner_name"], weight="bold", size="4"),
                                rx.text(f"Puntaje: {card['winner_score']}", size="2"),
                                rx.text(card["category_name"], size="1"),
                                rx.text(card["tournament_name"], size="1", color_scheme="gray"),
                                align="center",
                                spacing="1",
                                padding="0.5em",
                            ),
                            border_width="thick",
                            border_radius="1em",
                            width="100%",
                        ),
                    ),
                    columns="2",
                    spacing="4",
                    width="50%",
                    padding="0.5em",
                ),
                rx.card(
                    rx.text("Sin resultados aún", weight="bold", size="3"),
                    border_width="thick",
                    border_radius="1em",
                    padding="1em",
                ),
            ),
        ),
```

**5c — Wire `on_load`:**

**Before:**
```python
    on_load=AuthState.check_auth_redirect,
```

**After:**
```python
    on_load=[AuthState.check_auth_redirect, DashboardState.load_recent_winners],
```

**Verification:**
```bash
python -m pytest tests/test_results_service.py tests/test_dashboard_state.py -x -v
```
And manual: `reflex run` → navigate to `/home` authenticated → see winner cards or "Sin resultados aún".

---

### Task 6 (REFACTOR): Clean up and verify

**What:** Post-implementation polish.

**Checklist:**
- [x] `ruff check kakumi_app/states/dashboard_state.py` — no errors
- [x] `ruff check kakumi_app/services/results_service.py` — no new errors
- [x] Remove any unused imports from edited files
- [x] Verify `DashboardState` has no unused vars (`winner_cards` and `is_loading` are both consumed)
- [x] Confirm `str(score)` handles `int` and `float` — e.g. `str(3)` → `"3"`, `str(24.5)` → `"24.5"`, `str(0)` → `"0"`
- [x] Confirm empty state renders when `winner_cards == []`

**Verification:** Full test suite:
```bash
python -m pytest tests/ -x -v
```

---

## Rollback

Single PR, atomic rollback:

```bash
git checkout kakumi_app/kakumi_app.py
git checkout kakumi_app/services/results_service.py
rm kakumi_app/states/dashboard_state.py
```

No migration needed — no schema changes.

---

## Dependency Graph

```
Task 1 (RED: tests for get_recent_winners) ──→ Task 2 (GREEN: implement)
                                                      │
                                                      ▼
Task 3 (RED: tests for DashboardState) ──→ Task 4 (GREEN: create state)
                                                      │
                                                      ▼
                                        Task 5 (GREEN: wire on_load + UI)
                                                      │
                                                      ▼
                                                Task 6 (REFACTOR: cleanup)
```

Tasks 1→2 and 3→4 are independent chains that converge at Task 5. Each RED step must fail before its GREEN step is started.
