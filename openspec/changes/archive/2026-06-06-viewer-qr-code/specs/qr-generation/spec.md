# QR Generation Specification

## Purpose

Define how QR codes are generated from tournament viewer codes, displayed in the operator workspace, and regenerated on demand. QR code encodes a URL that grants one-tap spectator access to the tournament dashboard.

## Requirements

### Requirement: QR MUST Encode Viewer Dashboard URL with Auth Code

Generated QR code MUST encode URL in format:

```
/viewer/dashboard/{tournament_id}?code={8-char-hex-code}
```

URL MUST use relative path (no domain hardcoding). Scheme-relative so QR scan on same origin resolves correctly.

#### Scenario: URL format

- GIVEN Tournament ID 42 with viewer_code "a1b2c3d4"
- WHEN QR generation helper receives tournament data
- THEN URL string MUST be `/viewer/dashboard/42?code=a1b2c3d4`

### Requirement: QR Generation MUST Use qrcode Library with Pillow

QR generation helper `_make_qr_data_url(url: str) -> str` MUST:

1. Import `qrcode` library
2. Call `qrcode.make(url)` to produce a PIL Image
3. Save image to `BytesIO` buffer in PNG format
4. Encode buffer bytes with `base64.b64encode()`
5. Return string `data:image/png;base64,<encoded_data>`

`qrcode[pil]` MUST be added to `requirements.txt`. Pillow is already present.

#### Scenario: Helper returns valid data URI

- GIVEN URL string `/viewer/dashboard/42?code=a1b2c3d4`
- WHEN `_make_qr_data_url(url)` is called
- THEN result MUST start with `data:image/png;base64,`
- AND subsequent portion MUST be valid base64 (decodes to PNG header bytes `\x89PNG`)

#### Scenario: Same URL produces same QR image

- GIVEN same URL input twice
- WHEN `_make_qr_data_url` called both times
- THEN both outputs MUST start with `data:image/png;base64,`
- AND decoded image content MUST be identical (deterministic QR)

### Requirement: QR Generation MUST Be SSR-Safe

Helper MUST NOT perform file I/O or depend on browser DOM. All operations use in-memory `BytesIO` buffer. No temp files, no `canvas`, no DOM API.

#### Scenario: No file I/O on generation

- GIVEN `_make_qr_data_url(url)` executes
- WHEN examined for file writes
- THEN no `open()`, `os.write`, `pathlib.Path.write_bytes`, or similar file I/O calls occur
- AND no files appear in filesystem after call

#### Scenario: Works without browser environment

- GIVEN Reflex SSR context (no DOM, no window object)
- WHEN `_make_qr_data_url(url)` is called
- THEN result MUST be valid data URI
- AND no exception raised related to missing DOM API

### Requirement: TournamentState MUST Have QR Vars and Event Handlers

`TournamentState` MUST add state variables:

- `qr_data_url: str = ""` — base64 data URI of QR image
- `qr_code_text: str = ""` — the 8-char viewer code displayed as text
- `qr_generated_at: str = ""` — ISO-8601 or human-readable UTC timestamp
- `qr_expires_at: str = ""` — ISO-8601 or human-readable expiry timestamp (generation + 5h)

#### Scenario: Default state is empty

- GIVEN `TournamentState` is initialized
- THEN `qr_data_url` MUST be `""`
- AND `qr_code_text` MUST be `""`
- AND `qr_generated_at` MUST be `""`
- AND `qr_expires_at` MUST be `""`

### Requirement: generate_qr() Handler MUST Generate Full QRSession

`TournamentState.generate_qr()` event handler MUST:

1. Get current tournament ID from `self.current_tournament`
2. Call `ViewerService.generate_viewer_code(tournament_id)` to get new code
3. If code is None (tournament not found), show error toast
4. Build URL: `/viewer/dashboard/{tournament_id}?code={code}`
5. Call `_make_qr_data_url(url)` to produce QR data URI
6. Set `self.qr_data_url`, `self.qr_code_text = code`
7. Set `self.qr_generated_at` to current UTC time (ISO format)
8. Set `self.qr_expires_at` to UTC time + 5 hours (ISO format)
9. Show success toast

MUST persist code + timestamp to DB via `ViewerService.generate_viewer_code()`.

#### Scenario: Generate QR from tournament workspace

- GIVEN `TournamentState.current_tournament` = Tournament ID 42 with no current viewer code
- WHEN `generate_qr()` is called
- THEN `ViewerService.generate_viewer_code(42)` MUST be called
- AND `self.qr_data_url` MUST NOT be empty
- AND `self.qr_data_url` MUST start with `data:image/png;base64,`
- AND `self.qr_code_text` MUST match the returned code (8-char hex)
- AND `self.qr_expires_at` MUST be 5 hours after `self.qr_generated_at`
- AND success toast MUST be shown

#### Scenario: Generate QR when tournament missing

- GIVEN `TournamentState.current_tournament` is None
- WHEN `generate_qr()` is called
- THEN error toast MUST be shown ("No tournament selected")
- AND state vars MUST remain empty

### Requirement: regenerate_qr() Handler MUST Invalidate Previous Code

`TournamentState.regenerate_qr()` MUST:

1. Same flow as `generate_qr()` — generates new code + timestamp via `ViewerService.generate_viewer_code()`
2. Overwrites previous `viewer_code` and `viewer_code_generated_at` in DB
3. Updates all QR state vars
4. Old code becomes invalid immediately (no longer in DB)

This is intentional invalidation — active viewer sessions with old code lose access.

#### Scenario: Regenerate gives new code

- GIVEN Tournament has viewer_code "oldcode1" and active QR shown
- WHEN `regenerate_qr()` is called
- THEN `ViewerService.generate_viewer_code(tournament_id)` returns new code (e.g. "newcode1")
- AND `self.qr_code_text` MUST be "newcode1"
- AND `self.qr_generated_at` MUST be updated to current time
- AND old "oldcode1" is no longer valid in DB

#### Scenario: Old code invalid after regeneration

- GIVEN Tournament's `viewer_code` changed from "oldcode1" to "newcode1"
- WHEN `validate_viewer_code("oldcode1")` is called
- THEN result MUST be None (code no longer exists)

### Requirement: Tournament Workspace MUST Display QR Card

Workspace grid (`tournament.py`) MUST include a QR card as 5th card. Grid has `columns="2"` so 5th card wraps to row 3, spanning full width.

Card MUST show (in empty state):

- Heading "QR de Espectadores"
- "Generar QR" button (shown when `qr_data_url` is empty)
- Or: QR image, code text, expiry timestamp, "Regenerar QR" button (shown when `qr_data_url` non-empty)

Card position: after `_tatami_card()` in the grid.

#### Scenario: Empty state before QR generated

- GIVEN tournament workspace renders and `qr_data_url` is `""`
- WHEN QR card is visible
- THEN "Generar QR" button MUST be shown
- AND QR image MUST NOT be shown
- AND code text MUST NOT be shown

#### Scenario: QR generated state

- GIVEN `qr_data_url` is non-empty
- WHEN QR card renders
- THEN QR image (`rx.image(src=qr_data_url)`) MUST be displayed
- AND code text MUST be shown (e.g. "Código: a1b2c3d4")
- AND expiry timestamp MUST be shown (e.g. "Expira: 2026-06-06 15:30 UTC")
- AND "Regenerar QR" button MUST be shown
- AND "Generar QR" button MUST NOT be shown

#### Scenario: Regenerate replaces QR content

- GIVEN QR card showing code "oldcode1"
- WHEN user clicks "Regenerar QR"
- THEN card shows new code "newcode1"
- AND QR image updates to encode new URL
- AND expiry timestamp updates to new 5h window

### Requirement: QR Card MUST Show Expiry Info

Expiry info MUST display as formatted timestamp (human-readable). No real-time countdown timer — static "expires at" is sufficient.

Format: `"Expira: {YYYY-MM-DD HH:MM} UTC"` or similar.

#### Scenario: Expiry timestamp displayed

- GIVEN QR generated with expiry 5 hours from now
- WHEN QR card renders
- THEN expiry text MUST contain "Expira:" or "Expires:"
- AND timestamp MUST be 5 hours after `qr_generated_at`

### Requirement: qrcode[pil] Dependency MUST Be Added

`requirements.txt` MUST include `qrcode[pil]` (or `qrcode` with Pillow). Pillow (`pillow`) already present.

#### Scenario: Dependency present after install

- GIVEN `requirements.txt` contains `qrcode[pil]`
- WHEN `pip install -r requirements.txt` runs
- THEN `import qrcode` succeeds
- AND `qrcode.make("url")` returns a PIL Image without error
