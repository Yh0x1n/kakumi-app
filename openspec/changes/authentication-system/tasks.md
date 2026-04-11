# Tasks: Authentication System Implementation

## Phase 1: Models and Migrations (Foundation)

- [x] 1.1 Create `kakumi_app/models/login_attempt.py` with tracking fields (IP, username, success, failure_reason)
- [x] 1.2 Create `kakumi_app/models/token_blacklist.py` with JTI, user_id, expiry, and reason tracking
- [x] 1.3 Create `kakumi_app/models/audit_log.py` for authentication event logging
- [x] 1.4 Update `kakumi_app/models/user_model.py` adding `failed_attempts`, `locked_until`, and `last_activity` columns
- [x] 1.5 Update `kakumi_app/models/__init__.py` to export new models
- [x] 1.6 Generate and apply Alembic migration for new models and columns: `alembic revision --autogenerate -m "add_auth_tracking_and_logging"`

## Phase 2: AuthService Logic (Core)

- [x] 2.1 Implement `record_login_attempt()` in `AuthService` to persist attempts and trigger lockout check
- [x] 2.2 Implement `is_account_locked()` and `lock_account()` in `AuthService` using 15min/5attempts rules
- [x] 2.3 Implement `reset_failed_attempts()` in `AuthService` to clear counter on success
- [x] 2.4 Update `AuthService.authenticate_user()` to integrate lockout checks and attempt recording
- [x] 2.5 Implement `blacklist_token()` and `is_token_blacklisted()` in `AuthService`
- [x] 2.6 Implement `refresh_tokens()` with rotation logic (invalidate old, issue new access+refresh)
- [x] 2.7 Implement `validate_password_strength()` with WKF 2026 security requirements (8+ chars, upper, number, special)
- [x] 2.8 Update `AuthService.create_user()` to enforce password strength validation

## Phase 3: AuthState and RBAC (Integration)

- [x] 3.1 Update `AuthState` in `kakumi_app/states/auth_state.py` to track `last_activity` timestamp
- [x] 3.2 Implement `check_session_timeout()` in `AuthState` with 30-minute inactivity threshold
- [x] 3.3 Create middleware/decorator-compatible `require_role()` in `AuthState` for Reflex handlers
- [x] 3.4 Wire `record_login_attempt` into audit log for success/fail/logout events
- [x] 3.5 Update UI login/registration handlers to show descriptive errors for lockout and weak passwords

## Phase 4: Testing (Verification)

- [x] 4.1 Create `tests/test_auth_models.py` for LoginAttempt and TokenBlacklist CRUD operations
- [x] 4.2 Create `tests/test_lockout_logic.py` covering 5-fail lockout and 15-min auto-unlock scenarios
- [x] 4.3 Create `tests/test_token_rotation.py` verifying refresh token rotation and blacklisting
- [x] 4.4 Create `tests/test_password_validation.py` with parametrized cases for weak/strong passwords
- [x] 4.5 Create `tests/test_rbac_integration.py` for `require_role` and session timeout scenarios
- [x] 4.6 Verify full integration: Login -> Activity -> Refresh -> Logout -> Blacklist check
