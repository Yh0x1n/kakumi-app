# Explore: QR Code para Espectadores

## skill_resolution

- status: paths-injected
- skills_loaded: caveman, reflex-dev, python-pro

## Bugs Confirmed (5 pre-existing, block QR feature)

| # | Bug | File | Severity |
|---|-----|------|----------|
| 1 | `Tournament.generate_viewer_code()` called but doesn't exist | `viewer_service.py:76` | CRITICAL |
| 2 | `viewer_code_generated_at` referenced but missing from model | `viewer_service.py:27,30,78` | CRITICAL |
| 3 | `EXPIRATION_DAYS = 30` should be 5h | `viewer_service.py:17` | HIGH |
| 4 | `_is_code_expired()` uses `.days` not `timedelta(hours=)` | `viewer_service.py:31` | HIGH (expiration non-functional) |
| 5 | Double `@rx.event` decorator | `viewer_state.py:137-138` | MEDIUM |

## Critical Gap Found (QR-specific)

**Dashboard doesn't read `?code=` query param.** `ViewerState.load_viewer_dashboard()` uses `self.router.page.params.get("tournament_id")` for route param but does NOT extract `?code=` from query. QR scan lands on dashboard with empty `viewer_code` → redirect to `/viewer`.

Fix: `code = self.router.page.params.get("code")` → `self.viewer_code = code`.

In Reflex 0.8.x, `router.page.params` includes both route params and query params.

## Architecture Summary

### Viewer Flow

```
Tournament.viewer_code (DB, 8 chars)
  → ViewerService.generate_viewer_code(id) ← BROKEN
  → ViewerService.validate_viewer_code(code) ← BROKEN expiration
  → ViewerState.set_viewer_code() → validate_and_load_tournament()
  → load_categories() → dashboard
```

### Routes

| Route | Page | on_load |
|-------|------|---------|
| `/viewer` | `viewer_login_page` | — |
| `/viewer/dashboard/[tournament_id]` | `viewer_dashboard_page` | `ViewerState.load_viewer_dashboard` |

### Workspace Layout

`tournament.py` → `registry_page_shell(body=...)` → `rx.grid(columns="2")`:

```
┌─────────────────────┬─────────────────────┐
│ _selector_card()    │ _lifecycle_card()   │
├─────────────────────┼─────────────────────┤
│ _categories_card()  │ _tatami_card()      │
└─────────────────────┴─────────────────────┘
```

QR card would go as 5th card (grid wraps to next row).

## QR Integration Points

### State

Add to `TournamentState` (not new file). Pattern simpler than SecondaryDisplayState.

New vars: `qr_data_url`, `qr_code_text`, `qr_generated_at`, `qr_expires_at`.

Handlers: `generate_qr()`, `regenerate_qr()`.

### QR Generation (SSR-safe)

```python
import qrcode
from io import BytesIO
import base64

def _make_qr_data_url(url: str) -> str:
    qr = qrcode.make(url)
    buf = BytesIO()
    qr.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode()
    return f"data:image/png;base64,{b64}"
```

Data URI — no file I/O, SSR-compatible.

### URL Format

`/viewer/dashboard/{tournament_id}?code={8-char-code}`

## Pattern Reference

public_display feature uses complex polling state. QR feature is simpler CRUD-style. Don't copy that pattern.

## Dependencies

- `qrcode[pil]` — QR generation (Pillow already in requirements)
- No other deps needed

## Migration

New column: `viewer_code_generated_at: Optional[datetime]` on `tournaments` table.
Existing rows NULL → treated as expired, force regeneration. No retroactive migration.

## Recommended Phase Plan

1. Fix phase: bugs 1-5 (all 1-line changes + model field)
2. Infrastructure: `qrcode[pil]` dep, Alembic migration
3. QR gap: `?code=` extraction in `load_viewer_dashboard()`
4. QR feature: state handlers + UI card in workspace
5. Verify: scan QR → dashboard loads with all categories
