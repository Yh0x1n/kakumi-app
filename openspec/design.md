# Design: Dashboard Winner Result Cards

## Overview

Replace the 4 static "Resultado N" placeholder cards on `/home` with live winner-result cards. Each card shows winner name, score, category name, and tournament name. Max 4 cards, ordered by most recently completed category. Empty state shows "Sin resultados aún".

## Affected Files

| Action | File | Description |
|---|---|---|
| **EDIT** | `kakumi_app/services/results_service.py` | Add `get_recent_winners()` static method |
| **CREATE** | `kakumi_app/states/dashboard_state.py` | New `DashboardState` with `winner_cards` var + `load_recent_winners` event |
| **EDIT** | `kakumi_app/kakumi_app.py` | Import `DashboardState`, wire `on_load`, replace grid template |

No schema changes, no migrations, no new dependencies.

---

## 1. New Service Method: `ResultsService.get_recent_winners()`

### Location

`kakumi_app/services/results_service.py` — add after existing `list_tournament_cards()`.

### Signature

```python
@staticmethod
def get_recent_winners() -> list[dict[str, Any]]:
```

### Query Flow (all inside single `rx.session()`)

```
1. SELECT tc.*, t.name AS tournament_name
   FROM tournament_categories tc
   JOIN tournaments t ON t.id = tc.tournament_id
   WHERE tc.status = 'COMPLETED'
     AND tc.first_place_id IS NOT NULL
   ORDER BY tc.id DESC
   LIMIT 4
```

2. Collect unique `first_place_id` values → bulk-query `Athlete` table for names (same bulk-load pattern used by `get_podiums_view()`).

3. For each row, resolve score per modality:

   | Condition | Score Source |
   |---|---|
   | `modality == 'KATA_INDIVIDUAL'` **and** `competition_system == 'ROUND_ROBIN'` | Query `kata_informal_performances` for highest `id` matching `(category_id, first_place_id)` → `final_score` |
   | Everything else (Kumite, Kata elimination) | Query `Match` where `category_id == tc.id` and `status == 'COMPLETED'` and `winner_id == tc.first_place_id` — most recent `id`. If found: `aka_score` if `winner_id == aka_id` else `ao_score`. |
   | Team modalities | `0` (no match-level score model for teams) |
   | No match found | `0` |

4. Return shape:

```python
[
    {
        "winner_name": str,        # Athlete.name
        "winner_score": str,       # str(score) — always string
        "category_name": str,      # TournamentCategory.name
        "tournament_name": str,    # Tournament.name
        "category_id": int,        # for linking
    },
    ...
]
```

### Import Delta

Add import at top of file:
```python
from kakumi_app.models.kata_model import KataInformalPerformance
```

### Score Resolution Detail

**Kata informal** — use the index `ix_kata_informal_performances_category_athlete`:

```python
perf = session.exec(
    select(KataInformalPerformance)
    .where(
        KataInformalPerformance.category_id == category_id,
        KataInformalPerformance.athlete_id == first_place_id,
    )
    .order_by(KataInformalPerformance.id.desc())
).first()
score = perf.final_score if perf else 0.0
```

**Kumite / Kata elimination** — find the last match where the winner is `first_place_id`:

```python
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
    score = match.aka_score if match.winner_id == match.aka_id else match.ao_score
else:
    score = 0
```

**Score → string**: `str(int(score))` if score is a whole number, `str(score)` otherwise. Simplest: `str(score)` per spec — for floats this gives `"24.5"`, for ints `"3"`.

---

## 2. New State: `DashboardState`

### File

`kakumi_app/states/dashboard_state.py` — new file, following the `ResultsState` pattern.

### State Class

```python
"""Reflex state for dashboard winner cards."""

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

### Design Notes

- No error_message/empty_message vars on state — the empty state is handled in the template (single card if `winner_cards` is empty).
- Following `ResultsState` patterns: `@rx.event`, try/except, logging.
- Thin wrapper — all query logic lives in `ResultsService`.

---

## 3. Changes to `kakumi_app.py`

### 3a. Import

Add to existing import block (alphabetical order after `states.*` imports):

```python
from .states.dashboard_state import DashboardState
```

### 3b. Replace `dashboard()` grid template

**Before** — 4 static placeholder cards:

```python
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
```

**After** — live winner cards with empty state:

```python
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
```

### 3c. Wire `on_load`

Change the `/home` route registration from:

```python
app.add_page(
    dashboard,
    route="/home",
    title="Kakumi Tournament Manager",
    on_load=AuthState.check_auth_redirect,
)
```

To:

```python
app.add_page(
    dashboard,
    route="/home",
    title="Kakumi Tournament Manager",
    on_load=[AuthState.check_auth_redirect, DashboardState.load_recent_winners],
)
```

This ensures auth guard fires first. If unauthenticated, `check_auth_redirect` redirects before `load_recent_winners` runs.

---

## Data Flow (End-to-End)

```
Browser loads /home
  → Reflex runs on_load chain:
    1. AuthState.check_auth_redirect() → redirect to /login if not authed
    2. DashboardState.load_recent_winners()
       → ResultsService.get_recent_winners()
         → SQL: SELECT tc.*, t.name FROM tournament_categories tc
                JOIN tournaments t ON t.id = tc.tournament_id
                WHERE tc.status='COMPLETED' AND tc.first_place_id IS NOT NULL
                ORDER BY tc.id DESC LIMIT 4
         → For each row:
           - Bulk-load athlete names (one query for all unique first_place_ids)
           - Resolve score per modality (kata informal → performance table,
             else → match winner score)
         → Return list[dict] capped at 4
       → DashboardState.winner_cards = result
  → Template re-renders:
    - If winner_cards non-empty: grid of up to 4 cards
    - If empty: single "Sin resultados aún" card
```

## Empty-State Design

- `DashboardState.winner_cards` starts as `[]`
- `get_recent_winners()` returns `[]` when no completed categories exist
- Template uses `rx.cond(DashboardState.winner_cards.length() > 0, ..., empty_card)`
- Empty card: same visual weight as winner cards, says "Sin resultados aún"

## Edge Cases

| Case | Behavior |
|---|---|
| Same athlete wins 2 categories | Both cards appear (max 4) |
| 0 completed categories | Empty-state card |
| 2 completed categories | Exactly 2 cards, no gaps |
| 6 completed categories | Only 4 newest cards (ordered by category id DESC) |
| Kata informal with no performances row for winner | Score shows 0 (query returns None → fallback to 0) |
| Team modality winner | Score shows 0 (no match-level scoring for teams) |
| Database error on load | `winner_cards` stays `[]` → empty-state card renders |

## Test Strategy

### Unit tests on `ResultsService.get_recent_winners()`

Write test cases in `test_file.py` (or a new test file):

1. **Empty DB** → `[]`
2. **Single completed category (kumite)** → 1 card with correct winner name, score from match, category name, tournament name
3. **Single completed category (kata informal)** → 1 card with `final_score` from `KataInformalPerformance`
4. **Multiple categories, some incomplete** → only COMPLETED categories with first_place_id appear
5. **6 completed categories** → only 4 returned, ordered by id DESC
6. **Kata elimination (not informal)** → score resolved from match aka_score/ao_score
7. **Match where winner_id doesn't match aka_id or ao_id** → score 0 (shouldn't happen in practice, but safe)
8. **Team modality** → score 0

### Page load test

- Assert `on_load` chain includes both `AuthState.check_auth_redirect` and `DashboardState.load_recent_winners` in that order
- Assert `rx.cond` renders empty card when `winner_cards` is empty
- Assert grid renders when `winner_cards` non-empty

## Rollback

```bash
git checkout kakumi_app/kakumi_app.py
git checkout kakumi_app/services/results_service.py
rm kakumi_app/states/dashboard_state.py
```

## Commit Strategy

Single commit covering all three files — the feature is atomic and small. No intermediate state is meaningful.

### Suggested commit message

```
feat(dashboard): replace placeholder cards with live winner result cards

- Add ResultsService.get_recent_winners() — queries up to 4 most recently
  completed categories with winner name, score, category, tournament
- Score resolution per modality: kata informal reads final_score from
  KataInformalPerformance; kumite/kata elimination reads match aka/ao score
- Create DashboardState with winner_cards var and load_recent_winners event
- Wire on_load=[AuthState.check_auth_redirect, DashboardState.load_recent_winners]
- Replace 4 static "Resultado N" cards with rx.cond/rx.foreach grid
- Empty state shows "Sin resultados aún" card
- No schema changes, no new dependencies
```
