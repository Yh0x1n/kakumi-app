# Design: Authentication System

## Technical Approach

Implementar las funcionalidades críticas de seguridad faltantes en el sistema actual: tracking de intentos de login, lockout de cuentas, blacklist de tokens, refresh tokens, control de acceso por roles, timeout de sesiones, logging de auditoría, y validación de contraseñas. El enfoque es extender los modelos y servicios existentes siguiendo las convenciones del proyecto (Reflex + SQLModel).

---

## Architecture Decisions

### Decision: Tabla separada vs campos en User para LoginAttempt

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Campos en User | Simpler, menos joins, pero solo guarda último intento | Rejected |
| **Tabla LoginAttempt** | Audit trail completo, permite análisis de patrones, cumple requisitos de specs | **Accepted** |

**Rationale**: Las specs requieren tracking completo (IP, timestamp, etc.) para análisis de fuerza bruta y auditoría. Campos en User no permiten historial.

### Decision: Token Blacklist storage

| Option | Tradeoff | Decision |
|--------|----------|----------|
| En memoria (set) | Rápido, pero se pierde al reiniciar servidor | Rejected |
| **Tabla TokenBlacklist** | Persistente, permite limpieza automática, audit trail | **Accepted** |
| Redis | Más performante, pero añade dependencia externa | Rejected (por ahora) |

**Rationale**: SQLite ya está en uso. Tabla permite expiry automático y es simple de implementar. Se puede migrar a Redis si escala.

### Decision: Implementación de @require_role en Reflex

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Decorator tradicional (como existe) | No funciona con event handlers de Reflex State | Rejected |
| **Método de estado `can_access()`** | Compatible con Reflex, puede usarse en `on_mount` y event handlers | **Accepted** |
| Decorator en backend API | Para endpoints REST separados | Future consideration |

**Rationale**: Reflex States usan métodos de instancia. El decorador actual en `rbac.py` requiere token como parámetro, incompatible con `self`. Solución: método `require_role(role)` en AuthState que devuelve bool o raise, usado en handlers.

---

## Data Flow

### Login con Tracking + Lockout

```
┌──────────┐     ┌──────────────┐     ┌─────────────────┐
│  User    │───▶│ /api/login   │───▶│ Check Lockout?    │
└──────────┘     └──────────────┘     └─────────────────┘
                                              │
                    YES                       ▼
               ┌────────────────────┐    ┌─────────┐
               │ Reject: LOCKED     │◀───│ Locked? │
               └────────────────────┘    └─────────┘
                                                NO
                                                  ▼
┌──────────────────┐    ┌─────────────┐    ┌─────────────┐
│ AuditLog         │◀───│ Log result  │◀───│ Verify pass │
│ (success/fail)   │    │             │    │             │
└──────────────────┘    └─────────────┘    └──────┬──────┘
                                                 │
                                   ┌─────────────┴──────────┐
                                   │                      │
                                   ▼                      ▼
                            ┌──────────┐            ┌──────────────┐
                            │ Success  │            │ Fail         │
                            │ Clear    │            │ Increment    │
                            │ attempts │            │ LoginAttempt │
                            │ Tokens   │            └──────────────┘
                            └──────────┘                   │
                                                            ▼
                            ┌────────────┐         ┌──────────────┐
                            │ >= 5 fails │◀────────│ Check count  │
                            │ Lock User  │         └──────────────┘
                            └────────────┘
```

### Refresh Token Flow

```
┌──────────┐     ┌─────────────────┐     ┌────────────────────┐
│ Client   │───▶│ /api/refresh    │───▶│ Validate refresh   │
└──────────┘     └─────────────────┘     └────────────────────┘
                                                │
                            ┌───────────────────┴───────────────────┐
                            │ Valid                                 │ Invalid
                            ▼                                       ▼
              ┌─────────────────────────┐               ┌─────────────────┐
              │ Blacklist old token     │               │ Reject: EXPIRED │
              │ Create new access+refresh│              └─────────────────┘
              │ Return tokens           │
              └─────────────────────────┘
```

---

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `kakumi_app/models/login_attempt.py` | Create | Modelo para tracking de intentos fallidos |
| `kakumi_app/models/token_blacklist.py` | Create | Modelo para tokens invalidados |
| `kakumi_app/models/audit_log.py` | Create | Modelo para logging de auditoría |
| `kakumi_app/models/user_model.py` | Modify | Agregar campos: `failed_attempts`, `locked_until`, `last_activity` |
| `kakumi_app/services/auth_service.py` | Modify | Extender con: login con lockout, logout con blacklist, refresh, password validation |
| `kakumi_app/states/auth_state.py` | Modify | Agregar: timeout tracking, métodos de acceso por rol |
| `kakumi_app/auth/rbac.py` | Modify | Mejorar require_role para compatibilidad con Reflex |
| `alembic/versions/` | Create | Migraciones para nuevos modelos y columnas |

---

## Interfaces / Contracts

### Models

```python
# login_attempt.py
class LoginAttempt(rx.Model, table=True):
    __tablename__ = "login_attempts"
    
    id: int = Field(primary_key=True)
    username: str = Field(max_length=50, index=True)  # Usuario intentado
    ip_address: Optional[str] = Field(max_length=45)   # IPv4/IPv6
    user_agent: Optional[str] = Field(max_length=255)  # Browser info
    was_successful: bool = Field(default=False)
    failure_reason: Optional[str] = Field(max_length=50)  # INVALID_PASS, LOCKED, etc.
    created_at: datetime = Field(default_factory=datetime.utcnow)

# token_blacklist.py
class TokenBlacklist(rx.Model, table=True):
    __tablename__ = "token_blacklist"
    
    id: int = Field(primary_key=True)
    token_jti: str = Field(max_length=255, index=True, unique=True)  # JWT ID
    user_id: int = Field(foreign_key="users.id")
    token_type: str = Field(max_length=20)  # "access" o "refresh"
    expires_at: datetime
    blacklisted_at: datetime = Field(default_factory=datetime.utcnow)
    reason: Optional[str] = Field(max_length=50)  # LOGOUT, REFRESH_ROTATION, etc.

# audit_log.py
class AuditLog(rx.Model, table=True):
    __tablename__ = "audit_logs"
    
    id: int = Field(primary_key=True)
    event_type: str = Field(max_length=50, index=True)  # LOGIN_SUCCESS, LOGIN_FAILED, LOGOUT
    user_id: Optional[int] = Field(foreign_key="users.id", index=True)
    username: Optional[str] = Field(max_length=50)  # Para casos donde user no existe
    ip_address: Optional[str] = Field(max_length=45)
    user_agent: Optional[str] = Field(max_length=255)
    details: Optional[str] = Field(max_length=1000)  # JSON con datos adicionales
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
```

### User Model Extensions

```python
# Campos agregados a User model
class User(rx.Model, table=True):
    # ... campos existentes ...
    
    # Security tracking
    failed_attempts: int = Field(default=0)
    locked_until: Optional[datetime] = Field(default=None)
    last_activity: Optional[datetime] = Field(default=None)
```

### AuthService Extensions

```python
class AuthService:
    # ... métodos existentes ...
    
    @staticmethod
    def record_login_attempt(username: str, ip: str, user_agent: str, 
                             success: bool, reason: str = None) -> None:
        """Registra intento de login en LoginAttempt."""
    
    @staticmethod
    def is_account_locked(user: User) -> Tuple[bool, Optional[datetime]]:
        """Verifica si cuenta está bloqueada y retorna estado + unlock_time."""
    
    @staticmethod
    def lock_account(user: User) -> None:
        """Bloquea cuenta por LOCKOUT_MINUTES."""
    
    @staticmethod
    def reset_failed_attempts(user: User) -> None:
        """Resetea contador de intentos tras login exitoso."""
    
    @staticmethod
    def blacklist_token(token: str, user_id: int, reason: str = "LOGOUT") -> bool:
        """Agrega token a blacklist."""
    
    @staticmethod
    def is_token_blacklisted(token: str) -> bool:
        """Verifica si token está en blacklist."""
    
    @staticmethod
    def refresh_tokens(refresh_token: str) -> Tuple[Optional[str], Optional[str], str]:
        """Rota tokens: valida refresh, blacklist old, genera nuevos."""
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, str]:
        """Valida complejidad: min 8 chars, mayúscula, número, especial."""
    
    @staticmethod
    def create_user(..., password: str) -> Tuple[Optional[User], str]:
        """Extender para validar password antes de crear."""
```

### AuthState Extensions

```python
class AuthState(rx.State):
    # ... existentes ...
    
    # Session timeout tracking
    SESSION_TIMEOUT_MINUTES = 30
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    
    def check_session_timeout(self) -> bool:
        """Verifica si sesión expiró por inactividad."""
    
    def update_last_activity(self):
        """Actualiza timestamp de actividad."""
    
    def require_role(self, required_role: str) -> bool:
        """Verifica si usuario tiene rol requerido. Lanza/retorna según uso."""
    
    def can_access(self, permission: str) -> bool:
        """Verifica permiso específico usando RBAC."""
```

---

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `AuthService.validate_password_strength()` | Parametrized pytest: weak/strong passwords |
| Unit | `AuthService.is_account_locked()` | Mock datetime, test edge cases |
| Unit | `AuthService.record_login_attempt()` | Verify DB inserts with mocked session |
| Integration | Login flow con lockout | Simular 5 intentos fallidos, verificar bloqueo, esperar 15min |
| Integration | Token refresh rotation | Crear refresh, llamar refresh, verificar old en blacklist |
| Integration | Session timeout | Simular inactividad de 31 min, verificar rechazo |
| E2E | Password validation en UI | Form con contraseña débil muestra error |
| E2E | RBAC en páginas | Acceso a `/admin` como VIEWER debe redirigir |

### Casos de Test Específicos

```python
# Test: Lockout después de 5 intentos
def test_lockout_after_five_failed_attempts(db_session, sample_user):
    for i in range(5):
        success, _ = AuthService.authenticate_user(sample_user.username, "wrong")
        assert not success
    
    locked, unlock_time = AuthService.is_account_locked(sample_user)
    assert locked
    assert unlock_time > datetime.utcnow()

# Test: Password strength validation
def test_password_validation():
    assert AuthService.validate_password_strength("weak")[0] == False
    assert AuthService.validate_password_strength("Strong123!")[0] == True

# Test: Token blacklist
@pytest.mark.parametrize("token_type", ["access", "refresh"])
def test_token_blacklist(token_type):
    token = create_token(type=token_type)
    AuthService.blacklist_token(token, user_id=1)
    assert AuthService.is_token_blacklisted(token)
```

---

## Migration / Rollout

1. **Database Migration** (Alembic):
   ```python
   # Agregar columnas a users: failed_attempts, locked_until, last_activity
   # Crear tablas: login_attempts, token_blacklist, audit_logs
   ```

2. **Zero-downtime deployment**:
   - Columnas nuevas tienen defaults, no afectan usuarios existentes
   - Tablas nuevas no afectan operaciones existentes
   - AuthService actualizado mantiene backward compatibility

3. **Cleanup tasks** (future):
   - Cron job para limpiar tokens expirados de blacklist
   - Archivar logs de auditoría antiguos (> 1 año)

---

## Open Questions

- [ ] ¿Qué hacer con tokens en blacklist al reiniciar servidor? (TTL basado en expiración del token)
- [ ] ¿Se necesita rate limiting por IP además de por usuario? (recomendado para producción)
- [ ] ¿Dónde almacenar `last_activity` - en User o sesión del cliente? (en User para persistencia)
