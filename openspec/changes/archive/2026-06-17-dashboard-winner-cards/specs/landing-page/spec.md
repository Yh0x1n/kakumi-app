# Delta for landing-page

## MODIFIED Requirements

### Requirement: Dashboard Moved to `/home`

The system MUST serve the authenticated dashboard at the route `/home` protected by the `check_auth_redirect` guard, displaying up to 4 live winner result cards instead of placeholder cards.
(Previously: dashboard showed 4 static placeholder "Resultado N" cards)

#### Scenario: Unauthenticated access to dashboard is blocked

- GIVEN an unauthenticated user visits `/home`
- WHEN the page loads
- THEN the `check_auth_redirect` guard SHALL fire
- AND the user SHALL be redirected to `/login`

#### Scenario: Authenticated user sees winner result cards

- GIVEN an authenticated user visits `/home`
- WHEN the page loads
- THEN the user SHALL see up to 4 winner result cards
- AND each card SHALL display the winner name, winner score, category name, and tournament name
- AND the user SHALL NOT see the landing page hero content
- AND the user SHALL NOT see placeholder "Resultado N" cards

#### Scenario: Sidebar "Kakumi" link navigates to `/home`

- GIVEN an authenticated user is on any page with the sidebar
- WHEN the user clicks the "Kakumi" link in the sidebar
- THEN the browser SHALL navigate to `/home`
- AND the `href` value of the link SHALL be `"/home"` (not `"/"`)

## ADDED Requirements

### Requirement: Winner Cards Capped at Four

The system MUST display at most 4 winner result cards on the dashboard. If there are fewer than 4 completed categories with a winner, fewer cards SHALL render and no gaps or empty slots SHALL appear.

#### Scenario: Four or more completed categories

- GIVEN there are 6 completed categories with winners assigned
- WHEN the dashboard loads
- THEN exactly 4 winner cards SHALL render
- AND no additional cards SHALL appear

#### Scenario: Fewer than four completed categories

- GIVEN there are 2 completed categories with winners assigned
- WHEN the dashboard loads
- THEN exactly 2 winner cards SHALL render
- AND no empty card slots SHALL appear

### Requirement: Winner Cards Show Required Data

Each winner result card MUST display the winner full name, the winner's score as a string, the category name, and the tournament name. These four data points SHALL be visible on every rendered card.

#### Scenario: Card displays winner name, score, category, and tournament

- GIVEN a completed category with a winner assigned
- WHEN the dashboard renders the winner card for that category
- THEN the card SHALL show the winner's full name
- AND the card SHALL show the winner's score (as a string)
- AND the card SHALL show the category name
- AND the card SHALL show the tournament name

#### Scenario: Score displayed as string

- GIVEN a completed category where the winner's score is an integer (e.g. 3) or a float (e.g. 24.5)
- WHEN the dashboard renders the winner card
- THEN the score SHALL be displayed as a string via `str()`
- AND the display SHALL be `"3"` for integer scores and `"24.5"` for float scores

### Requirement: Winner Cards Ordered by Most Recently Completed

The system MUST order winner cards by `tournament_categories.id DESC`, placing the most recently completed category first.

#### Scenario: Cards ordered newest first

- GIVEN three completed categories with IDs 10, 15, and 20
- WHEN the dashboard loads
- THEN the first card SHALL correspond to category ID 20
- AND the second card SHALL correspond to category ID 15
- AND the third card SHALL correspond to category ID 10

### Requirement: Winner Score Resolution by Modality

The system MUST resolve the winner's score differently depending on the category's modality and format.

#### Scenario: Kata informal score from final_score

- GIVEN a category with modality `KATA_INDIVIDUAL` and format `ROUND_ROBIN`
- AND the first-place winner has a `kata_informal_performances` row for that category
- WHEN the system resolves the score
- THEN the score SHALL be `kata_informal_performances.final_score` for the row with the highest `id` for that `(category_id, athlete_id)` pair

#### Scenario: Kumite and kata elimination score from match

- GIVEN a category with modality `KUMITE` or modality `KATA_INDIVIDUAL` with format other than `ROUND_ROBIN`
- AND the category has a completed match where `winner_id` equals the category's `first_place_id`
- WHEN the system resolves the score
- THEN if the winner was `aka_id` in that match, the score SHALL be `aka_score`
- AND if the winner was `ao_id` in that match, the score SHALL be `ao_score`

#### Scenario: No match found yields score zero

- GIVEN a completed category with a first-place winner
- AND no completed match exists where `winner_id = first_place_id`
- WHEN the system resolves the score
- THEN the displayed score SHALL be `0`

#### Scenario: Team modality yields score zero

- GIVEN a completed category with format `TEAM`
- AND a first-place winner is assigned
- WHEN the system resolves the score
- THEN the displayed score SHALL be `0`

### Requirement: Empty State for No Winners

The system MUST show a single card reading "Sin resultados aún" when there are no completed categories with winners assigned.

#### Scenario: No completed categories

- GIVEN no categories have `status = 'COMPLETED'` and `first_place_id IS NOT NULL`
- WHEN the dashboard loads
- THEN exactly one card SHALL render
- AND that card SHALL display "Sin resultados aún"

#### Scenario: No winners after creating first category

- GIVEN a tournament exists but no category has a `first_place_id` assigned
- WHEN the dashboard loads
- THEN the empty-state card "Sin resultados aún" SHALL render
- AND no winner cards SHALL appear

### Requirement: Auth Guard Fires Before Data Load

The system MUST execute `check_auth_redirect` before `DashboardState.load_recent_winners` in the `/home` route `on_load` chain.

#### Scenario: Unauthenticated user never fetches winners

- GIVEN an unauthenticated user visits `/home`
- WHEN the `on_load` fires
- THEN `check_auth_redirect` SHALL execute first
- AND `load_recent_winners` SHALL NOT execute
- AND the user SHALL be redirected to `/login`

#### Scenario: Authenticated user fetches winners after auth check

- GIVEN an authenticated user visits `/home`
- WHEN the `on_load` fires
- THEN `check_auth_redirect` SHALL execute first
- AND `DashboardState.load_recent_winners` SHALL execute after auth passes
- AND the winner cards SHALL render

## REMOVED Requirements

### Requirement: Placeholder Result Cards on Dashboard

(Reason: replaced by live winner result cards — the 4 static "Resultado N" cards are removed in favor of real data-driven cards)
(Migration: the `rx.foreach(rx.Var.range(4), ...)` template in `dashboard()` is replaced with `rx.foreach(DashboardState.winner_cards, ...)`. No consumer-facing migration needed.)
