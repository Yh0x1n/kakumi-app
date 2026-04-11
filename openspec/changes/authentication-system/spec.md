# Authentication System Spec

## Purpose

Implementar funcionalidades críticas de autenticación y control de acceso según especificaciones WKF 2026. El sistema actual tiene JWT pero carece de tracking de intentos, bloqueo de cuentas, invalidación de tokens, y control de acceso por roles.

---

## ADDED Requirements

### Requirement: Login Attempt Tracking

El sistema DEBE registrar cada intento de login fallido para mitigar ataques de fuerza bruta.

#### Scenario: Registro de intento fallido

- GIVEN un usuario con credenciales inválidas
- WHEN el usuario envía credentials incorrectas al endpoint `/api/auth/login`
- THEN el sistema DEBE crear un registro en LoginAttempt con timestamp, IP, y usuario
- AND incrementar contador de intentos fallidos para ese usuario

#### Scenario: Reset de intentos tras login exitoso

- GIVEN un usuario con intentos fallidos previos (entre 1-4)
- WHEN el usuario envía credenciales válidas
- THEN el sistema DEBE limpiar todos los intentos fallidos registrados para ese usuario
- AND permitir acceso normalmente

---

### Requirement: Account Lockout

El sistema DEBE bloquear temporalmente cuentas tras 5 intentos fallidos consecutivos durante 15 minutos.

#### Scenario: Lockout tras 5 intentos fallidos

- GIVEN un usuario que realizó 5 intentos de login fallidos consecutivos
- WHEN el usuario envía credenciales (válidas o no) al endpoint `/api/auth/login`
- THEN el sistema DEBE rechazar el login con error "ACCOUNT_LOCKED"
- AND incluir timestamp de desbloqueo en la respuesta

#### Scenario: Desbloqueo automático tras 15 minutos

- GIVEN una cuenta bloqueada por intentos fallidos
- WHEN el tiempo transcurrido excede 15 minutos desde el bloqueo
- THEN el sistema DEBE permitir nuevos intentos de login
- AND DEBE permitir login exitoso si las credenciales son válidas

---

### Requirement: Token Blacklist

El sistema DEBE invalidar tokens de acceso durante logout para prevenir reutilización.

#### Scenario: Logout invalida access token

- GIVEN un usuario autenticado con token de acceso válido
- WHEN el usuario ejecuta logout en endpoint `/api/auth/logout`
- THEN el sistema DEBE agregar el token a la blacklist
- AND DEBE retornar éxito indicando token invalidado

#### Scenario: Request con token en blacklist

- GIVEN un usuario que previamente ejecutó logout
- WHEN el usuario envía request con token invalidado
- THEN el sistema DEBE rechazar el request con error "TOKEN_INVALIDATED"
- AND NO DEBE procesar la request

---

### Requirement: Refresh Token Flow

El sistema DEBE permitir renovación de tokens de acceso sin re-autenticación.

#### Scenario: Refresh exitoso

- GIVEN un usuario con refresh token válido (no expirado, no revocado)
- WHEN el usuario envía request a `/api/auth/refresh` con refresh token
- THEN el sistema DEBE retornar nuevo access token válido
- AND DEBE retornar nuevo refresh token (rotation de seguridad)
- AND DEBE invalidar el refresh token antiguo

#### Scenario: Refresh con token expirado

- GIVEN un usuario con refresh token expirado
- WHEN el usuario envía request a `/api/auth/refresh`
- THEN el sistema DEBE rechazar con error "REFRESH_TOKEN_EXPIRED"
- AND DEBE requerir re-autenticación

---

### Requirement: Role-Based Access Control

El sistema DEBE restringir acceso a endpoints según rol del usuario mediante decorador `@require_role`.

#### Scenario: Acceso permitido por rol

- GIVEN un usuario con rol "ADMIN"
- WHEN el usuario envía request a endpoint protegido con `@require_role("ADMIN")`
- THEN el sistema DEBE permitir acceso y procesar la request

#### Scenario: Acceso denegado por rol

- GIVEN un usuario con rol "USER"
- WHEN el usuario envía request a endpoint protegido con `@require_role("ADMIN")`
- THEN el sistema DEBE rechazar con error "FORBIDDEN"
- AND DEBE retornar código HTTP 403

---

### Requirement: Session Timeout

El sistema DEBE cerrar sesiones inactivas después de 30 minutos.

#### Scenario: Timeout por inactividad

- GIVEN un usuario autenticado con última actividad registrada
- WHEN pasan más de 30 minutos sin actividad
- THEN el sistema DEBE considerar la sesión expirada
- AND DEBE requerir re-autenticación para cualquier request

#### Scenario: Refresh extiende sesión

- GIVEN un usuario autenticado con última actividad a 25 minutos
- WHEN el usuario ejecuta refresh token exitosamente
- THEN el sistema DEBE actualizar timestamp de última actividad
- AND reiniciar el contador de 30 minutos

---

### Requirement: Login Audit Logging

El sistema DEBE registrar todos los eventos de autenticación para auditoría.

#### Scenario: Login exitoso registrado

- GIVEN un usuario que inicia sesión exitosamente
- WHEN el login se completa
- THEN el sistema DEBE crear registro en audit_log con evento "LOGIN_SUCCESS", timestamp, usuario, IP

#### Scenario: Login fallido registrado

- GIVEN un usuario que intenta login con credenciales inválidas
- WHEN el login falla
- THEN el sistema DEBE crear registro en audit_log con evento "LOGIN_FAILED", timestamp, usuario, IP, razón

#### Scenario: Logout registrado

- GIVEN un usuario autenticado que ejecuta logout
- WHEN el logout se procesa
- THEN el sistema DEBE crear registro en audit_log con evento "LOGOUT", timestamp, usuario

---

### Requirement: Password Strength Validation

El sistema DEBE rechazar contraseñas que no cumplan requisitos mínimos de seguridad.

#### Scenario: Contraseña débil rechazada

- GIVEN un usuario que intenta registrar o cambiar contraseña
- WHEN la contraseña tiene menos de 8 caracteres O no contiene números O no contiene mayúsculas
- THEN el sistema DEBE rechazar con error "WEAK_PASSWORD"
- AND DEBE indicar requisitos mínimos requeridos

#### Scenario: Contraseña válida aceptada

- GIVEN un usuario que proporciona contraseña válida
- WHEN la contraseña tiene mínimo 8 caracteres, al menos 1 número, 1 mayúscula, 1 carácter especial
- THEN el sistema DEBE aceptar la contraseña
- AND permitir registro o cambio de contraseña

---

## Requirements Summary

| Capability | Requirements | Scenarios |
|------------|-------------|-----------|
| login-attempt-tracking | 1 | 2 |
| account-lockout | 1 | 2 |
| token-blacklist | 1 | 2 |
| refresh-token-flow | 1 | 2 |
| role-based-access-control | 1 | 2 |
| session-timeout | 1 | 2 |
| login-audit-logging | 1 | 3 |
| password-strength-validation | 1 | 2 |
| **Total** | **8** | **17** |

---

## Next Steps

Listo para fase de Design (sdd-design). Cada requirement debe ser desglosado en tareas implementables.
