# Proposal: Excel-only Registry Import/Export

## Intent
Replace existing JSON-based import/export for athletes and referees with `.xlsx` (Excel) format to improve user experience. Remove JSON support entirely.

## Scope

### In Scope
- `.xlsx` import/export for Athletes.
- `.xlsx` import/export for Referees.
- Complete removal of JSON registry import/export code.
- Prepare architecture contract for future import/export extensions (Teams/Matches/Penalties).

### Out of Scope
- `.xls` (legacy Excel) format.
- Tournament results import/export.
- Team, Match, or Penalty import/export implementations.

## Capabilities

### New Capabilities
- `registry-excel-import-export`: Handles `.xlsx` parsing and generation for athletes and referees.

### Modified Capabilities
- `athlete-registry`: Removes JSON support, integrates `.xlsx`.
- `referee-registry`: Removes JSON support, integrates `.xlsx`.

## Approach
- Delete JSON endpoints/state logic.
- Use `openpyxl` and `pandas` (already in repo) to generate and parse `.xlsx` files.
- Define a base class/interface for `.xlsx` import/export to allow easy extension for Teams/Matches in the future.
- Update UI to only accept/offer `.xlsx` files.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/states/` | Modified | Update import/export event handlers |
| `kakumi_app/pages/` | Modified | Update upload components & download buttons |
| `kakumi_app/services/` | Modified | Swap JSON serialization for `pandas`/`openpyxl` logic |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Invalid `.xlsx` structure | High | Strict schema validation during upload |
| Memory limits on large files | Low | Stream parsing or file size limits |

## Rollback Plan
Revert commit removing JSON support; keep `openpyxl`/`pandas` logic unlinked until stable.

## Dependencies
- `openpyxl` and `pandas` (already installed).

## Success Criteria
- [ ] Athletes and Referees can be exported to `.xlsx`.
- [ ] Valid `.xlsx` uploads successfully create Athletes/Referees.
- [ ] No JSON import/export traces remain.