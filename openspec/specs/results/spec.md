# Feature Specification: Tournament-Centered Results Pages

## 1. Overview

This specification details the behavior and technical requirements for the tournament results and statistics views in Kakumi App. The goal is to fully flesh out the placeholder pages currently found in `kakumi_app/pages/results.py`.

## 2. Requirements (RFC 2119)

- The system MUST provide a main `/results` index that lists available tournaments or general result categories.
- The system MUST provide a route `/results/tournament/[id]` to show results specific to a tournament.
- The system MUST provide a route `/results/category/[id]` to show results specific to a category.
- The system MUST provide a `/results/podiums` view showing 1st, 2nd, and 3rd place winners per category.
- The system MUST provide a `/results/statistics` view showing summary data (e.g., total matches, points scored).
- The implementation MUST use strictly Python and Reflex components, adhering to the "Pure Python" constraint.
- The implementation MUST handle edge cases where no data exists for a selected tournament or category.

## 3. Scenarios (Given/When/Then)

**Scenario 1: Viewing Tournament Results**

- **Given** a user navigates to `/results/tournament/[id]`
- **When** the tournament ID is valid
- **Then** the page displays a list of categories and final standings for that tournament.

**Scenario 2: Viewing Podiums**

- **Given** a tournament has completed categories
- **When** a user visits `/results/podiums`
- **Then** the page displays the top 3 athletes (1st, 2nd, 3rd) for each completed category.

**Scenario 3: Empty Results Graceful Handling**

- **Given** a user navigates to a newly created tournament
- **When** there are no matches or scores
- **Then** the `/results/tournament/[id]` page shows a clear "No results available yet" message.

## 4. Technical Constraints

- The UI MUST be built exclusively using `rx.Component` within `kakumi_app/pages/results.py`.
- Any required state variables MUST be added to a Reflex `State` class in `kakumi_app/states.py` or a dedicated state module.
- All code must comply with PEP-8 guidelines (max 88 characters, formatted with Black).

## 5. Review Budget Strategy

The changes will be staged to stay under the 400-line review limit.

- **Slice 1:** Implementation of basic routing and state for `/results` and `/results/tournament/[id]`.
- **Slice 2:** Implementation of the `/results/category/[id]` and `/results/podiums` views.
- **Slice 3:** Implementation of `/results/statistics` view.
