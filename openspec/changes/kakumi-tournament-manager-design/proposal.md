# Proposal: Kakumi Tournament Manager - Full Application Architecture

## Intent

Design and implement the complete Kakumi Tournament Manager web application based on the comprehensive WKF 2026 specification. This includes building all data models, state management, UI components, and business logic for managing karate tournaments.

## Scope

### In Scope
- Full application architecture design
- All data models from spec Section 2
- Tournament workflow and state management
- Scoring systems (Kata and Kumite)
- Penalty system with WKF 2026 rules
- Bracket generation and match management
- User authentication and authorization
- Import/export functionality
- Real-time scoring display

### Out of Scope
- Production deployment configuration
- Performance optimization (can be addressed later)
- Mobile app development
- Integration with external ranking systems

## Approach

1. **Architecture Design**: Create technical design covering all aspects of the application
2. **Data Modeling**: Implement all SQLModel models based on spec
3. **State Management**: Design Reflex State classes for reactive UI
4. **Service Layer**: Build business logic services for scoring, penalties, brackets
5. **UI Components**: Implement all screens per spec Section 11
6. **Integration**: Connect all layers with proper data flow
7. **Testing**: Unit and integration tests for critical paths

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/models/` | Major | All new models from spec Section 2 |
| `kakumi_app/states/` | Major | New State classes for domain logic |
| `kakumi_app/services/` | Major | New service layer for business logic |
| `kakumi_app/components/` | Major | New UI components for all screens |
| `kakumi_app/pages/` | Major | All pages per spec Section 11 |
| `kakumi_app/auth/` | Major | Authentication and authorization |
| `kakumi_app/utils/` | Minor | Helper functions |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Complex bracket generation algorithms | Medium | Start with simple elimination, add complexity later |
| Real-time scoring concurrency | High | Implement optimistic locking and transaction isolation |
| WKF rule interpretation errors | Medium | Use existing specs.md as source of truth, reference PDFs |
| Reflex learning curve for team | Medium | Focus on core patterns, document decisions |

## Dependencies

- `specs.md` — Complete technical specifications
- `docs/WKF 2026 *.pdf` — Official rule documents
- `kakumi.db` — Existing SQLite database (will be migrated)

## Success Criteria

- [ ] All data models implemented and migrated
- [ ] Tournament workflow from planning to archival works
- [ ] Scoring systems for Kata and Kumite functional
- [ ] Penalty system correctly implements WKF 2026 rules
- [ ] Bracket generation creates valid tournaments
- [ ] Real-time scoring display works
- [ ] Import/export handles CSV/JSON correctly
- [ ] User authentication with role-based permissions