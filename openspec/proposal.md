# SDD Proposal: Dashboard Winner Result Cards

## Intent

Replace the 4 placeholder "Resultado N" cards on the dashboard with live winner-result cards showing the most recently completed category winners across all tournaments. Max 4 cards.

Each card shows:
- Winner name
- Winner score
- Category name  
- Tournament name

## Scope

**In scope:**
- New `DashboardState` with `winner_cards: list[dict]` and `load_recent_winners()` event
- Static method `ResultsService.get_recent_winners()` — read-only aggregation
- Wire `on_load` on `/home` to include `DashboardState.load_recent_winners`
- Replace `rx.foreach(rx.Var.range(4), ...)` in `dashboard()` with real `rx.foreach(DashboardState.winner_cards, ...)`
- Score resolution for all current modalities:
  - **Kata informal** (`KATA_INDIVIDUAL` + `ROUND_ROBIN`): `kata_informal_performances.final_score` (most recent performance for that athlete+category)
  - **Kumite & Kata elimination**: last completed match where `winner_id = first_place_id`, pick `aka_score` or `ao_score` depending on which side the winner was
- Empty state: if 0 winners, show a single "Sin resultados aún" card

**Out of scope:**
- Team-modality winner scores (will show 0 — no match-based scoring exists yet for teams in the model)
- Kata numerical elimination scoring (scores live in `KataJudgeScore`, not on Match — will show 0 until that path is implemented)
- Pagination or "view all" — only max 4, no "more" link
- Tournament-level winner cards (these are category-level)
- Podiums or 2nd/3rd place — only 1st place winner

## Affected Areas

| Action | File | Why |
|---|---|---|
| **EDIT** | `kakumi_app/services/results_service.py` | Add `get_recent_winners()` + import `KataInformalPerformance` |
| **CREATE** | `kakumi_app/states/dashboard_state.py` | New `DashboardState` class |
| **EDIT** | `kakumi_app/kakumi_app.py` | Import `DashboardState`, wire `on_load`, replace grid template |

## Data Flow

```
DashboardState.load_recent_winners() 
  → ResultsService.get_recent_winners()
    → Query tournament_categories (COMPLETED, first_place_id NOT NULL)
    → JOIN tournaments for name
    → JOIN athletes for winner name
    → Resolve score per modality (kata informal vs rest)
    → Return list[dict] capped at 4
  → DashboardState.winner_cards = result
```

## Business Rules

1. **Filter**: `status = 'COMPLETED' AND first_place_id IS NOT NULL`
2. **Order**: `tournament_categories.id DESC` (most recently completed first — higher id ≈ more recent)
3. **Limit**: 4
4. **No dedup**: if the same athlete wins two categories, both appear (max 4)
5. **Score for kata informal**: grab the `kata_informal_performances` row with highest `id` for that `(category_id, athlete_id)` pair → `final_score`
6. **Score for other modalities**: find the last completed match (`status = 'COMPLETED'`) in that category where `winner_id = first_place_id`; if the winner matches `aka_id`, use `aka_score`, else `ao_score`. If no match found, score = 0.
7. **Score display**: shown as string (integer for kumite scores, float for kata). No formatting beyond `str()`.

## Risks

| Risk | Mitigation |
|---|---|
| **Kata numerical scores show 0** | Documented ceiling; scores live in `KataJudgeScore` which isn't joined to Match. Low priority — numerical kata is rare at club level. |
| **Team modality scores show 0** | Team scoring model is undeveloped. Cards still show winner name and context correctly. |
| **Performance with many joins on on_load** | 4-card max + indexed FKs. Query is read-only, fast, and only runs on dashboard load. |
| **User sees incomplete data during tournament** | Cards only appear for COMPLETED categories. Mid-tournament the dashboard may show 0–3 cards; empty state handles this. |

## Rollback

Revert the three changed files:

```bash
git checkout kakumi_app/kakumi_app.py
git checkout kakumi_app/services/results_service.py
rm kakumi_app/states/dashboard_state.py  # new file, safe to delete
```

No migration needed — no schema changes.

## Success Criteria

1. Dashboard `/home` shows up to 4 winner cards instead of "Resultado 1–4" placeholders.
2. Each card shows: winner name, score, category name, tournament name.
3. With 0 completed categories: empty-state card "Sin resultados aún".
4. With 1–3 winners: exactly that many cards render, no gaps.
5. Score resolves correctly for kata informal (reads `final_score`) and kumite (reads match score).
6. `on_load=[AuthState.check_auth_redirect, DashboardState.load_recent_winners]` — auth redirect still fires first.
7. No new dependencies, no schema changes.
