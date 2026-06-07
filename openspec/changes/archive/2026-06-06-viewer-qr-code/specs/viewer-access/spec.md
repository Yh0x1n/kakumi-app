# Viewer Access Specification

## Purpose

Define how viewer codes are generated, validated, and expired for spectator access to tournament dashboards. Covers code lifecycle, rate-limiting, query-param extraction, and the database model fields supporting viewer authentication.

## Requirements

### Requirement: Model Must Have viewer_code and viewer_code_generated_at

Tournament model MUST contain both:

- `viewer_code: Optional[str]` — 8-char hex code (max_length=8). Already exists.
- `viewer_code_generated_at: Optional[datetime]` — UTC timestamp of code generation. Added by this change.

`viewer_code_generated_at` MUST accept NULL. NULL rows MUST be treated as expired by `_is_code_expired()`.

#### Scenario: Existing tournaments without timestamp

- GIVEN a Tournament row with `viewer_code` set to "a1b2c3d4" AND `viewer_code_generated_at` is NULL
- WHEN `_is_code_expired()` evaluates the row
- THEN result MUST be True (expired)

#### Scenario: Migration adds new column

- GIVEN `viewer_code_generated_at` does not exist in `tournaments` table
- WHEN alembic migration `upgrade` runs
- THEN column `viewer_code_generated_at TIMESTAMP NULL` MUST be added
- AND `viewer_code_generated_at` attribute MUST be defined on `Tournament` model with `Optional[datetime]`

### Requirement: ViewerService MUST Generate 8-Char Hex Codes

`ViewerService.generate_viewer_code(tournament_id)` MUST:

1. Open DB session, fetch Tournament by ID
2. Generate 8-char hex string via `secrets.token_hex(4)`
3. Set `tournament.viewer_code = new_code`
4. Set `tournament.viewer_code_generated_at = datetime.datetime.utcnow()`
5. Commit and return the code string
6. Return None if tournament ID not found

MUST NOT call `Tournament.generate_viewer_code()` (method does not exist — bug B1 fix).

#### Scenario: Successful generation

- GIVEN a Tournament with ID 42 exists in database
- WHEN `ViewerService.generate_viewer_code(42)` is called
- THEN result MUST be a non-empty 8-character hex string (e.g. "a1b2c3d4")
- AND `tournament.viewer_code` in DB MUST equal returned code
- AND `tournament.viewer_code_generated_at` in DB MUST be within 5 seconds of UTC now

#### Scenario: Tournament not found

- GIVEN no Tournament with ID 999 exists
- WHEN `ViewerService.generate_viewer_code(999)` is called
- THEN result MUST be None

#### Scenario: Generated code format

- GIVEN `secrets.token_hex(4)` produces string "1a2b3c4d"
- WHEN code is stored as `viewer_code`
- THEN length MUST be 8 characters
- AND string MUST match regex `^[0-9a-f]{8}$`

### Requirement: ViewerService.validate_viewer_code() MUST Check Three Conditions

`validate_viewer_code(code)` MUST return `Optional[Tournament]` after verifying:

1. Code is not locked (rate-limit check)
2. Code exists in `tournaments` table (`viewer_code == code`)
3. Code is not expired (`_is_code_expired()` returns False)

If all pass: reset failed attempts and return Tournament.
If any fail: record failed attempt and return None.

#### Scenario: Valid code returns tournament

- GIVEN Tournament with `viewer_code="a1b2c3d4"` AND `viewer_code_generated_at` = 2 hours ago
- AND code has 0 failed attempts
- WHEN `validate_viewer_code("a1b2c3d4")` is called
- THEN result MUST be the Tournament object
- AND `_failed_attempts` for that code MUST be empty (reset)

#### Scenario: Non-existent code returns None

- GIVEN no Tournament has `viewer_code="zzzzzzzz"`
- WHEN `validate_viewer_code("zzzzzzzz")` is called
- THEN result MUST be None
- AND failed attempt MUST be recorded for "zzzzzzzz"

#### Scenario: Expired code returns None

- GIVEN Tournament with `viewer_code="expired1"` AND `viewer_code_generated_at` = 6 hours ago (>5h)
- WHEN `validate_viewer_code("expired1")` is called
- THEN result MUST be None
- AND failed attempt MUST be recorded

#### Scenario: Locked code returns None

- GIVEN 5 failed attempts recorded for code "locked01" within last 5 minutes
- WHEN `validate_viewer_code("locked01")` is called
- THEN result MUST be None (locked)

### Requirement: Expiration MUST Be 5 Hours from generation

Expiration constant MUST be `EXPIRATION_HOURS = 5` (replaces `EXPIRATION_DAYS = 30` — bug B3 fix).

`_is_code_expired(tournament)` MUST:

- Return True if `viewer_code_generated_at` is None
- Compute `age = datetime.datetime.utcnow() - tournament.viewer_code_generated_at`
- Return True if `age.total_seconds() > EXPIRATION_HOURS * 3600`
- Return False otherwise

MUST NOT use `age.days` comparison (bug B4 fix). MUST treat NULL timestamp as expired (bug B2 fix context).

#### Scenario: Code within 5 hours

- GIVEN `viewer_code_generated_at` = 4 hours 30 minutes ago
- WHEN `_is_code_expired()` evaluates
- THEN result MUST be False

#### Scenario: Code exactly at 5 hours

- GIVEN `viewer_code_generated_at` = 5 hours 0 minutes 1 second ago
- WHEN `_is_code_expired()` evaluates
- THEN result MUST be True

#### Scenario: Code expired past 5 hours

- GIVEN `viewer_code_generated_at` = 10 hours ago
- WHEN `_is_code_expired()` evaluates
- THEN result MUST be True

#### Scenario: NULL timestamp treated as expired

- GIVEN `viewer_code_generated_at` is None
- WHEN `_is_code_expired()` evaluates
- THEN result MUST be True

### Requirement: Rate Limit MUST Lock After 5 Failed Attempts

Rate-limit logic MUST:

- Track per-code failed attempts in memory: `_failed_attempts: dict[str, tuple[int, datetime]]`
- After 5 failed attempts for same code, lock for 5 minutes
- `_is_code_locked(code)` MUST check if 5+ attempts within last 5 minutes
- `_record_failed_attempt(code)` MUST increment attempt count or create entry
- `_reset_attempts(code)` MUST clear entry on successful validation
- After lockout period (5 min), reset attempts and allow retry

Constants: `_MAX_ATTEMPTS = 5`, `_LOCKOUT_MINUTES = 5`.

#### Scenario: First 4 failures do not lock

- GIVEN code "test01" with 4 failed attempts recorded
- WHEN `_is_code_locked("test01")` is called
- THEN result MUST be False

#### Scenario: 5th within lockout window locks

- GIVEN code "test01" with 5 failed attempts, last 2 minutes ago
- WHEN `_is_code_locked("test01")` is called
- THEN result MUST be True

#### Scenario: Lockout expires after 5 minutes

- GIVEN code "test01" with 5 failed attempts, last 6 minutes ago
- WHEN `_is_code_locked("test01")` is called
- THEN result MUST be False
- AND `_failed_attempts` entry for "test01" MUST be removed

#### Scenario: Successful validation resets attempts

- GIVEN code "test01" with 3 failed attempts
- AND `validate_viewer_code("test01")` succeeds
- THEN `"test01"` MUST NOT be in `_failed_attempts`

### Requirement: ViewerState.load_viewer_dashboard() MUST Extract ?code= Query Param

`load_viewer_dashboard()` MUST extract `code` query parameter BEFORE using `self.viewer_code`.

Fix: add `self.viewer_code = self.router.page.params.get("code", "")` or equivalent as first operation in the handler.

This is the critical gap fix — QR scan supplies code via query param, not localStorage.

#### Scenario: Query param code extracted on load

- GIVEN URL is `/viewer/dashboard/42?code=a1b2c3d4`
- WHEN `load_viewer_dashboard()` executes
- THEN `self.viewer_code` MUST be set to "a1b2c3d4"
- AND validation proceeds using that code

#### Scenario: No query param code present

- GIVEN URL is `/viewer/dashboard/42` (no `?code=` param)
- WHEN `load_viewer_dashboard()` executes
- THEN `self.viewer_code` MUST be set to empty string `""`
- AND validation fails, user redirected to `/viewer`

### Requirement: Double @rx.event Decorator MUST Be Removed

`ViewerState.load_viewer_dashboard()` at `viewer_state.py:137-138` has duplicate `@rx.event` decorator (bug B5 fix). MUST remove one, keep single `@rx.event`.

#### Scenario: Only one decorator remains

- GIVEN `viewer_state.py` contains `load_viewer_dashboard` with one `@rx.event` decorator
- WHEN Reflex parses the state class
- THEN method MUST be registered as event handler exactly once
- AND no syntax error or duplicate registration occurs

### Requirement: ViewerService.generate_viewer_code() MUST Use secrets.token_hex(4) Inline

Method at `viewer_service.py:76` calls `Tournament.generate_viewer_code()` which does not exist (bug B1 fix). MUST replace with:

```python
new_code = secrets.token_hex(4)
```

`secrets` MUST be imported at module top.

#### Scenario: Bug B1 code replaces non-existent method call

- GIVEN `viewer_service.py` line 76 calls `Tournament.generate_viewer_code()`
- WHEN fix is applied
- THEN call MUST be replaced with `secrets.token_hex(4)`
- AND module MUST have `import secrets`

### Requirement: CheckViewerAccess and check_viewer_access Consistency

`check_viewer_access(code, tournament_id)` MUST validate code via `validate_viewer_code()` and return True only if returned Tournament ID matches.

#### Scenario: Correct code for correct tournament

- GIVEN valid code "a1b2c3d4" for Tournament ID 42
- WHEN `check_viewer_access("a1b2c3d4", 42)` is called
- THEN result MUST be True

#### Scenario: Valid code for wrong tournament

- GIVEN valid code "a1b2c3d4" for Tournament ID 42
- WHEN `check_viewer_access("a1b2c3d4", 99)` is called
- THEN result MUST be False
