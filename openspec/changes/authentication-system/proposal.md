# Proposal: Authentication System

## Intent

Implementar las funcionalidades críticas de autenticación faltantes para cumplir con las especificaciones WKF 2026 y mejorar la seguridad del sistema. El sistema actual tiene JWT implementado pero falta tracking de intentos, bloqueo de cuentas, invalidación de tokens, y control de acceso por roles.

## Scope

### In Scope
- LoginAttempt tracking - Tabla/modelo para contar intentos fallidos
- Account lockout logic - Bloqueo 15min después de 5 intentos
- Token blacklist - Invalidar tokens en logout
- Refresh token endpoint - `/api/auth/refresh`
- @require_role decorator funcional
- Inactivity timeout (30 min)
- Login audit logging
- Password strength validation
- Backend route guards

### Out of Scope
- MFA (autenticación multifactor)
- OAuth/SAML integrations
- SSO (Single Sign-On)
- Cambios en el modelo User existente (solo agregar relaciones)

## Capabilities

### New Capabilities
- `login-attempt-tracking`: Sistema para rastrear y limitar intentos de login fallidos
- `account-lockout`: Mecanismo de bloqueo temporal de cuentas tras intentos fallidos
- `token-blacklist`: Sistema para invalidar tokens activos en logout
- `refresh-token-flow`: Endpoint para renovar tokens de acceso
- `role-based-access-control`: Decorador y guards para proteger endpoints por rol
- `session-timeout`: Timeout de inactividad de 30 minutos
- `login-audit-logging`: Registro de eventos de login/logout
- `password-strength-validation`: Validación de fortaleza de contraseñas

### Modified Capabilities
None

## Approach

Implementar cada feature de forma incremental, empezando por las CRITICAL (login tracking, lockout, blacklist, refresh, role decorator) y luego las HIGH (timeout, audit, password validation, guards). Cada feature tendrá tests unitarios y de integración. Usar SQLModel para nuevos modelos y mantener compatibilidad con código existente.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `kakumi_app/services/auth_service.py` | Modified | Agregar lockout, blacklist, refresh, audit |
| `kakumi_app/states/auth_state.py` | Modified | Agregar timeout, role checks |
| `kakumi_app/models/user_model.py` | Modified | Agregar relaciones a LoginAttempt |
| `kakumi_app/models/login_attempt_model.py` | New | Modelo para tracking de intentos |
| `kakumi_app/models/blacklisted_token_model.py` | New | Modelo para tokens invalidados |
| `kakumi_app/api/auth_routes.py` | New | Endpoints de refresh y logout |
| `kakumi_app/decorators/role_decorator.py` | New | Decorador @require_role |
| `kakumi_app/middleware/auth_middleware.py` | New | Middleware para route guards |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Breaking changes en auth existente | Medium | Tests exhaustivos, feature flags |
| Performance impact con blacklist | Low | TTL automático, índices en DB |
| Race conditions en lockout | Low | Transacciones atómicas |
| Timeout no funciona en Reflex | Medium | Usar rx.interval + last_activity timestamp |

## Rollback Plan

Revertir cambios en archivos modificados, eliminar migraciones de Alembic, restaurar versión anterior de auth_service.py y auth_state.py. Los nuevos modelos pueden permanecer en DB sin afectar funcionalidad.

## Dependencies

- Ninguna dependencia externa nueva
- Requiere tests existentes pasando
- Requiere migraciones de Alembic funcionando

## Success Criteria

- [ ] Login fails after 5 consecutive invalid attempts
- [ ] Locked account unlocks automatically after 15 minutes
- [ ] Logout invalidates access token (blacklist check prevents reuse)
- [ ] Refresh endpoint returns new valid access token
- [ ] `@require_role("ADMIN")` blocks non-ADMIN users from protected endpoints
- [ ] Session expires after 30 minutes of inactivity
- [ ] Login/logout events are recorded in audit log
- [ ] Weak passwords (< 8 chars, no complexity) are rejected
- [ ] Backend route guards protect all API endpoints by role