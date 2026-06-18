I've completed a thorough exploration of the codebase. Here are my findings:

---

## SDD Exploration — Dashboard Winner Cards

### 1. Current State

The dashboard (`kakumi_app.py:dashboard()`) renders **4 placeholder cards** using `rx.Var.range(4)` showing "Resultado 1" through "Resultado 4". No data, no state.

### 2. Data Model (relevant)

| Table | Key columns for this feature |
|---|---|
| `tournament_categories` | `id`, `name`, `modality`, `competition_system`, `kata_flow_mode`, `status`, `first_place_id`, `tournament_id` |
| `tournaments` | `id`, `name` |
| `athletes` | `id`, `name` |
| `matches` | `id`, `category_id`, `winner_id`, `aka_id`, `ao_id`, `aka_score`, `ao_score`, `status` |
| `kata_informal_performances` | `id`, `category_id`, `athlete_id`, `final_score` |

Filter: `status = 'COMPLETED' AND first_place_id IS NOT NULL`, ordered by `tournament_categories.id DESC`, limit 4.

### 3. Where to add query

**`kakumi_app/services/results_service.py`** — add a `get_recent_winners()` static method. It's the natural home (read-only aggregation, all needed models already imported there). Only missing import: `KataInformalPerformance`.

The method will:
1. Query `TournamentCategory` joined with `Tournament` for the top 4 completed categories with winners
2. For each, resolve the score by modality:
   - **Kata informal** (`KATA_INDIVIDUAL` + `ROUND_ROBIN`): look up `kata_informal_performances.final_score` for the winner athlete in that category (most recent)
   - **All other modalities** (kumite, kata elimination): find the last completed match where `winner_id = first_place_id`, then pick `aka_score` or `ao_score` depending on which side the winner was
3. Look up `Athlete.name` for the winner name

### 4. State to create

**New file: `kakumi_app/states/dashboard_state.py`** — `DashboardState` with:
- `winner_cards: list[dict]` — structured as `{"winner_name", "winner_score", "category_name", "tournament_name"}`
- `load_recent_winners()` — async event, calls `ResultsService.get_recent_winners()`, mirrors `ResultsState.load_results_index` pattern

### 5. Wiring on_load

Change in `kakumi_app.py`:

```python
# Before:
on_load=AuthState.check_auth_redirect,
# After:
on_load=[AuthState.check_auth_redirect, DashboardState.load_recent_winners],
```

This is already a valid Reflex pattern (used by `public_display_page`). Auth redirect fires first; if unauthenticated, user gets redirected before data loads.

### 6. Template changes

Replace the `rx.foreach(rx.Var.range(4), ...)` block with `rx.foreach(DashboardState.winner_cards, ...)` rendering actual data fields inside each card.

### 7. Edge cases noted

- **0–3 winners**: Renders what exists, with a fallback empty-state text
- **Team modalities**: `first_place_id` still maps to `athletes.id`, so name resolves. Score will be whatever the last match says (may be 0). Ceiling noted for future.
- **Kata numerical scoring**: `aka_score`/`ao_score` on Match may not be populated for numerical kata (scores live in `KataJudgeScore`). Will show 0. Ceiling noted.
- **Multiple kata informal performances per athlete**: Take the most recent one (highest `id`), which is the final/deciding performance.

### 8. Files to create/modify

| Action | File |
|---|---|
| **EDIT** | `kakumi_app/services/results_service.py` — add `get_recent_winners()` + import |
| **CREATE** | `kakumi_app/states/dashboard_state.py` — new `DashboardState` |
| **EDIT** | `kakumi_app/kakumi_app.py` — import DashboardState, wire on_load, replace grid |

**Note**: I cannot write to the file system with my current toolset (no file write tool available). The exploration notes are documented above. The parent orchestrator should proceed with the Apply phase using these findings.