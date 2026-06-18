# Landing Page Specification

## Domain

`landing-page`

## Purpose

Define the behavior of the Kakumi App public landing page at the root URL (`/`), the relocated dashboard at `/home`, and all associated redirect updates. This change restructures the application flow so that the root route serves as a public presentation (hero with app name, tagline, and login CTA), while the authenticated dashboard moves to `/home` under the existing auth guard.

## Risk: Inferred Domain

The proposal has no explicit `Capabilities` section. The domain `landing-page` was inferred from the change's four affected areas: (1) the public landing page itself, (2) the dashboard route move, (3) auth redirect target changes, and (4) "Go Home" button updates in the protected layout and admin pages. If the expected domain differs, adjust the path accordingly.

## Requirements

### Requirement: Public Landing Page at Root

The system MUST serve a public landing page at the route `/` that renders the app name ("Kakumi"), a tagline ("Gestión de torneos de Karate-Do"), and a call-to-action button labeled "Iniciar Sesión" that navigates to `/login`.

#### Scenario: Unauthenticated user sees landing page

- GIVEN an unauthenticated user visits the root URL `https://kakumi.app/`
- WHEN the page loads
- THEN the user SHALL see the Kakumi app name displayed prominently
- AND the user SHALL see the tagline "Gestión de torneos de Karate-Do"
- AND the user SHALL see an "Iniciar Sesión" button
- AND the user SHALL NOT be redirected to `/login` or any other route

#### Scenario: CTA navigates to login

- GIVEN an unauthenticated user is viewing the landing page
- WHEN the user clicks the "Iniciar Sesión" button
- THEN the browser SHALL navigate to `/login`
- AND the URL SHALL update to `/login`

#### Scenario: Authenticated user sees landing page

- GIVEN an authenticated user visits the root URL `https://kakumi.app/`
- WHEN the page loads
- THEN the user SHALL see the same public landing page content (app name, tagline, "Iniciar Sesión" button)
- AND the user SHALL NOT be redirected to `/home`, `/login`, or any other route
- AND the landing page SHALL have no auth guard or `on_load` handler

#### Scenario: Landing page has no on_load auth guard

- GIVEN any user (authenticated or unauthenticated) navigates to `/`
- WHEN the route's `on_load` fires
- THEN there SHALL be NO call to any auth check or redirect function
- AND the page SHALL render immediately without waiting for any auth state

---

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

---

### Requirement: Auth Redirect Target

The system MUST redirect all post-authentication flows to `/home` instead of `/`.

#### Scenario: Login redirects to `/home`

- GIVEN an unauthenticated user visits `/login`
- WHEN the user submits valid credentials
- THEN the system SHALL redirect the user to `/home`
- AND the URL SHALL change to `/home`

#### Scenario: Authenticated user visits `/login`

- GIVEN an authenticated user visits `/login`
- WHEN the `on_load` fires the auth check
- THEN the system SHALL redirect the user to `/home`
- AND the URL SHALL change to `/home`

#### Scenario: Password change success redirects to `/home`

- GIVEN any user completes a password change via `/change-password`
- WHEN the password change succeeds
- THEN the system SHALL redirect the user to `/home`
- AND the URL SHALL change to `/home`

#### Scenario: Change-password access check redirects to `/home`

- GIVEN a user who does NOT need to change their password visits `/change-password`
- WHEN the `on_load` fires the access check
- THEN the system SHALL redirect the user to `/home`
- AND the URL SHALL change to `/home`

---

### Requirement: "Go Home" Button Target

All "Go Home" buttons in the protected layout and admin pages MUST navigate to `/home`.

#### Scenario: Protected layout 404/permission-denied — Go Home to `/home`

- GIVEN an authenticated user is on a 404 or permission-denied page rendered within the protected layout
- WHEN the user clicks the "Go Home" button
- THEN the browser SHALL navigate to `/home`
- AND the code `rx.redirect("/home")` SHALL be used (not `rx.redirect("/")`)

#### Scenario: Users page — Go Home to `/home`

- GIVEN an admin user is on the Users page
- WHEN the user clicks the "Go Home" button
- THEN the browser SHALL navigate to `/home`
- AND the `on_click` handler SHALL use `rx.redirect("/home")`

#### Scenario: Export page — Go Home to `/home`

- GIVEN an admin user is on the Export page
- WHEN the user clicks the "Go Home" button
- THEN the browser SHALL navigate to `/home`
- AND the `on_click` handler SHALL use `rx.redirect("/home")`

#### Scenario: Teams page — Go Home to `/home`

- GIVEN an admin user is on the Teams page
- WHEN the user clicks the "Go Home" button
- THEN the browser SHALL navigate to `/home`
- AND the `on_click` handler SHALL use `rx.redirect("/home")`

---

### Requirement: Landing Page Visual Presentation

The landing page MUST use the existing dark + crimson brand tone and Spanish-language UI, consistent with the rest of the application (`rx.theme(appearance="dark")`).

#### Scenario: Landing page matches brand theme

- GIVEN the landing page renders
- WHEN inspecting the page appearance
- THEN the background SHALL use `rx.color("gray", 2)` or equivalent dark background
- AND the "Iniciar Sesión" button SHALL use `color_scheme="crimson"`
- AND all text SHALL be in Spanish

#### Scenario: No auth guard on landing page

- GIVEN the landing page route at `/`
- WHEN inspecting the `app.add_page` registration for `/`
- THEN there SHALL be NO `on_load` parameter
- AND the page SHALL be accessible without authentication

---

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

---

## Non-Functional Requirements

### Requirement: No Breakage of Existing Routes

The restructure MUST NOT alter the behavior, content, or auth protection of any existing route other than `/` and `/home`. Specifically, `/login`, `/change-password`, `/viewer`, `/display/[display_key]`, `/viewer/dashboard/[tournament_id]`, `/competition/category/[id]`, `/competition/match/[id]/kumite`, `/competition/match/[id]/kata`, `/tournaments/[id]/bracket`, `/registries`, `/exhibition`, and all `/admin/*` routes SHALL remain unchanged.

#### Scenario: Existing routes unaffected

- GIVEN any existing route other than `/` and `/home` is visited
- WHEN the page loads
- THEN its behavior, content, and auth protection SHALL be identical to before the change

### Requirement: No `"/"` Redirects in Auth or Navigation

After the change, NO `rx.redirect("/")` or `href="/"` (other than the landing page itself and /login CTA) SHALL remain in `states/auth_state.py`, `components/sidebar.py`, `components/protected_layout.py`, `pages/admin/users_page.py`, `pages/admin/export_page.py`, or `pages/admin/teams_page.py`. The landing page's CTA link to `/login` is the only intentional remaining reference to `/` in navigation context.

#### Scenario: Auth redirects verified clean

- GIVEN the change is applied
- WHEN searching for `redirect("/")` across all Python files in the project (excluding the landing page's CTA and archive files)
- THEN zero results SHALL be found in auth state handlers, sidebar, protected layout, or admin pages

### Requirement: Atomic Change

The entire restructure SHALL be contained in a single atomic commit that can be fully reverted via `git revert` without side effects.

#### Scenario: Clean git revert

- GIVEN the landing-page-flow commit is applied
- WHEN a developer runs `git revert <commit-hash>`
- THEN the revert SHALL complete without merge conflicts
- AND the landing page SHALL be replaced by the original dashboard at `/`
- AND all auth redirects SHALL return to `"/"`
- AND all "Go Home" buttons SHALL return to `"/"`
- AND all tests SHALL continue to pass

### Requirement: Python-Only Implementation

All changes MUST be limited to Python files (`.py`). No CSS, JavaScript, TypeScript, HTML, or other frontend files SHALL be created or modified.

#### Scenario: No non-Python files changed

- GIVEN the change is applied
- WHEN inspecting the diff
- THEN only `.py` files SHALL be added or modified

## Requirements Summary

| Capability | Requirements | Scenarios |
|---|---|---|
| Public Landing Page at Root | 1 | 4 |
| Dashboard Moved to `/home` | 1 | 3 |
| Auth Redirect Target | 1 | 4 |
| "Go Home" Button Target | 1 | 4 |
| Landing Page Visual Presentation | 1 | 2 |
| Winner Cards Capped at Four | 1 | 2 |
| Winner Cards Show Required Data | 1 | 2 |
| Winner Cards Ordered by Most Recently Completed | 1 | 1 |
| Winner Score Resolution by Modality | 1 | 4 |
| Empty State for No Winners | 1 | 2 |
| Auth Guard Fires Before Data Load | 1 | 2 |
| Non-Functional | 4 | 4 |
| **Total** | **15** | **34** |
