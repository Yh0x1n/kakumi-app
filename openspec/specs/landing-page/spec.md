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

The system MUST serve the existing authenticated dashboard (sidebar + placeholder result cards) at the route `/home` instead of `/`. The `/home` route MUST be protected by the same `check_auth_redirect` guard that previously protected `/`.

#### Scenario: Unauthenticated access to dashboard is blocked

- GIVEN an unauthenticated user visits `/home`
- WHEN the page loads
- THEN the `check_auth_redirect` guard SHALL fire
- AND the user SHALL be redirected to `/login`

#### Scenario: Authenticated user sees dashboard

- GIVEN an authenticated user visits `/home`
- WHEN the page loads
- THEN the user SHALL see the existing dashboard content: sidebar navigation and placeholder result cards
- AND the user SHALL NOT see the landing page hero content

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
| Non-Functional | 4 | 4 |
| **Total** | **9** | **21** |
