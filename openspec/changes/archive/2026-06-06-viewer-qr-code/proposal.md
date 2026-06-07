# Proposal: QR Code para Espectadores (Viewer QR)

## skill_resolution

- status: paths-injected
- skills_loaded: caveman, reflex-dev, python-pro

## Intent

Admin/operator generate QR code from tournament workspace. QR encodes viewer dashboard URL with auth code. Scan → dashboard loads all categories live.

## Scope

### In scope

1. **5 pre-existing bug fixes** (blockers):
   - B1: `Tournament.generate_viewer_code()` call → replace with `secrets.token_hex(4)` inline. `viewer_service.py:76`
   - B2: Missing `viewer_code_generated_at` field → add to `Tournament` model. `tournament_model.py`
   - B3: `EXPIRATION_DAYS = 30` → `EXPIRATION_HOURS = 5`. `viewer_service.py:17`
   - B4: `_is_code_expired()` uses `.days` → use `timedelta(hours=)`. `viewer_service.py:31`
   - B5: Double `@rx.event` → remove duplicate. `viewer_state.py:137-138`

2. **Critical query-param gap fix**:
   - `ViewerState.load_viewer_dashboard()` doesn't extract `?code=` param. Add `self.viewer_code = self.router.page.params.get("code")` at top. `viewer_state.py`

3. **Model migration**:
   - Add `viewer_code_generated_at: Optional[datetime]` to `Tournament` table.
   - Alembic migration. Existing rows NULL → treated as expired (force regenerate).

4. **Dependency**:
   - Add `qrcode[pil]` to `requirements.txt` (Pillow already present).

5. **QR generation (SSR-safe)**:
   - `_make_qr_data_url(url: str) -> str` helper using `qrcode` + `BytesIO` + `base64`. No file I/O. Returns `data:image/png;base64,...`.

6. **State handlers** in `TournamentState`:
   - `generate_qr()` — generate new viewer code + timestamp, persist, produce QR data URL.
   - `regenerate_qr()` — same as generate but invalidates previous code (updates `viewer_code` + `viewer_code_generated_at`).
   - New vars: `qr_data_url`, `qr_code_text`, `qr_generated_at`, `qr_expires_at`.

7. **UI card** in tournament workspace:
   - 5th card in `rx.grid(columns="2")`. Auto-wraps to row 3.
   - Shows: QR image (when generated), code text, expiry countdown.
   - Buttons: "Generar QR" / "Regenerar QR".

8. **QR URL format**:
   - `/viewer/dashboard/{tournament_id}?code={8-char-hex}`

### Out of scope

- No viewer dashboard enhancements (categories already show all, not just active).
- No print/PDF export of QR.
- No email/SMS share.
- No QR scanner on auth page (manual code entry stays as fallback).
- No real-time countdown timer (static "expires at" timestamp enough).
- No public display integration.

## Affected modules

| Module | Change type |
|--------|------------|
| `kakumi_app/models/tournament_model.py` | Add field `viewer_code_generated_at` |
| `kakumi_app/services/viewer_service.py` | Fix bugs B1-B4, rename `EXPIRATION_DAYS` → `EXPIRATION_HOURS` |
| `kakumi_app/states/viewer_state.py` | Fix B5, add `?code=` extraction |
| `kakumi_app/states/tournament_state.py` | Add QR handlers + vars |
| `kakumi_app/pages/tournament.py` | Add QR card to workspace grid |
| `alembic/versions/` | New migration |
| `requirements.txt` | Add `qrcode[pil]` |

## Risks

| Risk | Impact | Mitigation |
|------|--------|-----------|
| QR code generation blocks SSR if Pillow not loaded | Crash on QR page | `qrcode[pil]` in reqs + try/import in helper |
| Regeneration breaks active viewer sessions | Viewer redirected | Expected behavior — code invalidated. Documented. |
| Clock skew on 5h expiry | Early/late expiration | Use UTC server time. Tolerance acceptable. |
| Existing tournaments with `viewer_code` set but no `viewer_code_generated_at` | Treated as expired | Call `generate_qr()` to set both fields. |

## Rollback

1. `git revert` commit.
2. If migration applied: `alembic downgrade -1` to drop `viewer_code_generated_at` column.
3. Remove `qrcode[pil]` from requirements.
4. Existing QR codes in DB become dead data — no impact.

## Success criteria

1. Admin opens tournament workspace → sees QR card (empty state).
2. Clicks "Generar QR" → QR image appears with expiry info.
3. QR scan → navigates to `/viewer/dashboard/{id}?code=XXXXXX` → dashboard loads with all categories.
4. After 5h, QR scan → redirect to `/viewer` (code expired).
5. "Regenerar QR" → new code + timestamp, old code invalid.
6. `python -m pytest` passes.
7. `ruff check` passes.

## Bugs fix summary (prerequisite)

```yaml
B1: viewer_service.py:76 — Tournament.generate_viewer_code() no existe
    Fix: reemplazar llamada con secrets.token_hex(4)

B2: viewer_service.py:27,30,78 — viewer_code_generated_at no está en el modelo
    Fix: agregar campo Optional[datetime] a Tournament model

B3: viewer_service.py:17 — EXPIRATION_DAYS = 30 debe ser 5 horas
    Fix: EXPIRATION_HOURS = 5, actualizar constant name everywhere

B4: viewer_service.py:31 — age.days compara días, no horas
    Fix: age.total_seconds() > EXPIRATION_HOURS * 3600

B5: viewer_state.py:137-138 — doble @rx.event decorator
    Fix: eliminar uno, mantener solo @rx.event
```

## Critical gap fix

`ViewerState.load_viewer_dashboard()` at `viewer_state.py`:
- No extrae `?code=` de query params.
- Fix: `self.viewer_code = self.router.page.params.get("code", "")` antes de usar `self.viewer_code`.

## Migration detail

```sql
ALTER TABLE tournaments ADD COLUMN viewer_code_generated_at TIMESTAMP NULL;
```

Existing rows: `NULL`. `_is_code_expired()` treats `None` as expired → prompts regeneration. No data migration needed.
