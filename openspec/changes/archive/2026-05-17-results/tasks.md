# Tasks: Tournament Results Hub

## Review Workload Forecast

| Field                   | Value                                                                                    |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| Estimated changed lines | 760-980 total across 3 slices; target 220-340 per slice                                  |
| 400-line budget risk    | High                                                                                     |
| Chained PRs recommended | Yes                                                                                      |
| Suggested split         | PR 1 (index + tournament hub) → PR 2 (category drill-down) → PR 3 (podiums + statistics) |
| Delivery strategy       | ask-on-risk                                                                              |
| Chain strategy          | size-exception                                                                           |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: size-exception
400-line budget risk: High

## Constraints

- Strict TDD is enabled in `openspec/config.yaml`; every slice starts RED and ends with focused verification.
- Keep each review slice under the 400-line budget; if a slice grows past budget, stop and split before continuing.
- Stay Python/Reflex only; do not introduce JS/TS/CSS/HTML files.
- Use existing repo test placement patterns at project root (`conftest.py`, `test_*.py`) unless the apply step first normalizes test layout.

## Planned delivery slices

### 0. Test harness alignment

#### 0.1 Baseline test/file placement discovery

- Inspect `conftest.py`, `test_tournament_category_state.py`, `test_kata_informal_service.py`, and `test_admin_registry_alias_wrappers.py`.
- Confirm fixture reuse, async test style, and whether new results tests should remain at repo root as `test_results_state.py`, `test_results_service.py`, and `test_results_pages.py`.
- Verification: document the chosen convention in the first new test file header or module docstring.
- Rollback boundary: no production code touched.

### 1. Slice 1 — `/results` index + `/results/tournament/[id]` hub

#### 1.1 RED — add failing aggregation/state tests

- Create `test_results_service.py` with failing tests for:
  - `ResultsService.list_tournament_cards()` using `Tournament` and `TournamentCategory` fixtures.
  - `ResultsService.get_tournament_view()` aggregating `Match` rows by `category_id` even when `Match.tournament_id` is `None`.
- Create `test_results_state.py` with failing tests for:
  - `ResultsState._parse_route_id()` valid/invalid route params.
  - `ResultsState.load_results_index()` and `ResultsState.load_tournament_view()` empty/error resets.
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py -v` fails only for missing/new behavior.
- Rollback boundary: remove new test files if the slice is abandoned.

#### 1.2 GREEN — implement minimal read-only service/state

- Create `kakumi_app/services/results_service.py` with minimal read-only methods:
  - `list_tournament_cards()`
  - `get_tournament_view(tournament_id: int)`
- Create `kakumi_app/states/results_state.py` with minimal state for index and tournament hub loading.
- Reuse safe route parsing patterns from `kakumi_app/states/bracket_state.py` and `kakumi_app/states/competition_category_state.py`.
- Verification: targeted RED tests now pass.
- Rollback boundary: revert only `results_service.py` and `results_state.py` if needed.

#### 1.3 GREEN — implement hub pages and navigation entry

- Replace placeholders in `kakumi_app/pages/results.py` for:
  - `/results`
  - `/results/tournament/[id]`
- Reuse `kakumi_app/components/registry_crud.py::registry_page_shell()` for layout.
- Add visible `Resultados` entry in `kakumi_app/components/sidebar.py`.
- In `kakumi_app/kakumi_app.py`, normalize results-page import/registration only if apply discovers duplicate or missing wiring after `ResultsState` is introduced.
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py -v` plus smoke assertions added in `test_results_pages.py` for headings and empty state.
- Rollback boundary: UI-only revert independent from service/state logic.

#### 1.4 TRIANGULATE — extend coverage for hub edge cases

- Add cases in `test_results_service.py` and `test_results_pages.py` for:
  - valid tournament with no categories/matches
  - invalid tournament id
  - category rows showing progress and podium-status placeholders
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py test_results_pages.py -v`.
- Rollback boundary: test-only expansion.

#### 1.5 REFACTOR — keep slice under budget

- Extract only page-local helpers inside `kakumi_app/pages/results.py` (for header, summary cards, empty state, status badges) without creating new global component modules.
- Collapse duplicated state reset logic in `kakumi_app/states/results_state.py` if needed.
- Verification: no behavior changes; targeted suite remains green.
- Rollback boundary: helper extraction can be reverted without losing core behavior.

### 2. Slice 2 — `/results/category/[id]` drill-down

#### 2.1 RED — add failing category-detail tests

- Extend `test_results_service.py` with failing tests for `ResultsService.get_category_view(category_id: int)` covering:
  - kata informal category uses `KataInformalService.rank_category()`
  - standard category returns ordered match summaries
  - valid category with no matches shows explicit empty message
- Extend `test_results_state.py` with failing tests for `ResultsState.load_category_view()` invalid id and error reset behavior.
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py -v` fails on new category expectations only.
- Rollback boundary: tests only.

#### 2.2 GREEN — implement service/state support for category detail

- Add `get_category_view()` to `kakumi_app/services/results_service.py`.
- Extend `kakumi_app/states/results_state.py` with category-specific vars and `load_category_view()`.
- Keep payloads JSON-serializable for Reflex state.
- Verification: category service/state tests pass.
- Rollback boundary: contained to results service/state.

#### 2.3 GREEN — render category detail page

- Replace the `/results/category/[id]` placeholder in `kakumi_app/pages/results.py`.
- Reuse:
  - `kakumi_app/components/kata_informal_table.py::kata_informal_table()`
  - `kakumi_app/components/match_card.py::match_card(show_future_action=False)`
- Include breadcrumb back to `/results/tournament/[id]` and category empty/error states.
- Verification: add/update `test_results_pages.py` smoke checks for heading, breadcrumb copy, and empty-state copy.
- Rollback boundary: route UI only.

#### 2.4 TRIANGULATE + REFACTOR — tighten category scenarios

- Add tests for podium summary rendering when persisted podium data exists versus when it is incomplete.
- Refactor ordering/serialization helpers inside `kakumi_app/services/results_service.py` only after category tests are green.
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py test_results_pages.py -v`.
- Rollback boundary: helper cleanup only.

### 3. Slice 3 — `/results/podiums` + `/results/statistics`

#### 3.1 RED — add failing context/podium/statistics tests

- Extend `test_results_state.py` with failing tests for `ResultsState._parse_context_tournament_id()` and selector-fallback behavior when query params are absent or invalid.
- Extend `test_results_service.py` with failing tests for:
  - `ResultsService.get_podiums_view()` statuses: `available`, `incomplete`, `unsupported_team`, `not_completed`
  - defensive parsing of `TournamentCategory.third_place_ids`
  - `ResultsService.get_statistics_view()` counters/breakdowns by category status, modality, system, and match status
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py -v` fails on the new coverage only.
- Rollback boundary: tests only.

#### 3.2 GREEN — implement podiums/statistics service + state

- Add `get_podiums_view()` and `get_statistics_view()` to `kakumi_app/services/results_service.py`.
- Extend `kakumi_app/states/results_state.py` with:
  - `selected_tournament_id`
  - `podium_cards`
  - `statistics_view`
  - `load_podiums_view()`
  - `load_statistics_view()`
- Keep the scope read-only; do not derive official podiums for unsupported flows.
- Verification: targeted state/service tests pass.
- Rollback boundary: contained to results service/state.

#### 3.3 GREEN — implement `/results/podiums` and `/results/statistics`

- Replace `pass` implementations in `kakumi_app/pages/results.py`.
- Use tournament selector fallback when `tournament_id` context is missing.
- Render callouts for incomplete or unsupported podium data instead of guessing winners.
- Verification: add `test_results_pages.py` smoke coverage for both routes with and without context.
- Rollback boundary: route UI only.

#### 3.4 TRIANGULATE + REFACTOR — budget guard and partial-data polish

- Add tests proving statistics still count matches through tournament category ids when `Match.tournament_id` is unset.
- Reuse local badge/table helpers inside `kakumi_app/pages/results.py` to avoid page duplication.
- Stop and split the slice if podium/statistics UI + tests exceed the 400-line review budget.
- Verification: `uv run python -m pytest test_results_service.py test_results_state.py test_results_pages.py -v`.
- Rollback boundary: helper cleanup or follow-up split only.

### 4. Final verification and delivery prep

#### 4.1 Targeted regression run

- Run: `uv run python -m pytest test_results_service.py test_results_state.py test_results_pages.py test_tournament_category_state.py test_kata_informal_service.py test_admin_registry_alias_wrappers.py -v`
- Confirm the spec scenarios are covered:
  - tournament hub renders category results
  - podiums route shows top 3 when persisted data exists
  - empty tournament copy is explicit
  - statistics route shows basic counters

#### 4.2 Manual Reflex smoke check

- If a visual pass is needed, run `timeout 45s uv run reflex run` and open:
  - `/results`
  - `/results/tournament/[id]`
  - `/results/category/[id]`
  - `/results/podiums?tournament_id=[id]`
  - `/results/statistics?tournament_id=[id]`
- Confirm headings, empty states, selector fallback, and sidebar navigation.

#### 4.3 Delivery/rollback boundaries

- Deliver as three review slices in order; do not collapse them into one PR unless the user explicitly accepts a size exception.
- Keep rollback simple:
  - PR 1 rollback removes results index/hub/state/service skeleton
  - PR 2 rollback removes category-detail additions only
  - PR 3 rollback removes podiums/statistics additions only

## Notes for apply

- Existing repo evidence suggests tests currently live at project root, even though `openspec/config.yaml` mentions `tests/`; prefer the repo’s active pattern unless a dedicated test-layout cleanup is performed first.
- Engram persistence tools were not available in this session; key findings were persisted only in repository artifacts.
