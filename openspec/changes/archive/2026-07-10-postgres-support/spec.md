# Spec: PostgreSQL Database Support

## 1. Requirements

### Functional

| ID | Req | Prio |
|----|-----|------|
| R1 | `DATABASE_URL` env var overridea `rxconfig.py`, `alembic.ini`, `env.py` — app usa URL de env si presente | P0 |
| R2 | Engine wrapper (`kakumi_app/db/engine.py`) expone `pool_size`, `echo`, `pool_timeout` configurables | P0 |
| R3 | Sin `DATABASE_URL` → SQLite default (`sqlite:///kakumi.db`). Dev workflow zero-breakage | P0 |
| R4 | `rx.session()` wrapper en `kakumi_app/db/engine.py` — reemplaza engine usado por `rx.model.session` y tests | P0 |
| R5 | `alembic upgrade head` funciona en SQLite Y PostgreSQL desde DB limpia. Sin revisiones legacy | P0 |
| R6 | JSON-string fields (`third_place_ids`, `tatami_certified`, `audit_log.details`) → columna `JSON`/`JSONB` (SQLAlchemy `sa.JSON`). Sin migrations heredadas | P1 |
| R7 | `docker-compose.yml` con PostgreSQL 16 lista para dev local | P1 |
| R8 | `.env.example` con `DATABASE_URL=postgresql://kakumi:kakumi@localhost:5432/kakumi` | P1 |
| R9 | `psycopg2-binary` en `requirements.txt` | P0 |
| R10 | CI matrix: tests corren en SQLite + PostgreSQL (service container) | P1 |
| R11 | Tests existentes (50+) pasan SIN cambios en SQLite Y PostgreSQL | P0 |
| R12 | Rollback: `git checkout` archivos modificados + `git rm` archivos nuevos alcanza | P0 |

### Non-Functional

| # | Req |
|---|-----|
| NF1 | Monkeypatch de `rx.model.session` en `conftest.py` debe seguir funcionando en ambos backends |
| NF2 | `kakumi.db` (SQLite legacy) nunca se toca — coexistencia pacífica |
| NF3 | Engine wrapper acepta `DATABASE_URL` con o sin driver prefix (ej `postgresql://` vs `postgresql+psycopg2://`) |
| NF4 | Pool config solo aplica a PostgreSQL. SQLite ignora pool params internamente |
| NF5 | JSONB columnas deben almacenar `dict` Python y recuperar `dict` Python sin serialización manual |

---

## 2. Scenarios

### S1: Dev default (sin DATABASE_URL)

**Input**: `reflex run` sin `DATABASE_URL` en entorno

**Expected:**
- `rxconfig.py` evalúa `os.getenv("DATABASE_URL", "sqlite:///kakumi.db")`
- Engine wrapper crea engine SQLite
- App arranca, UX idéntica
- `kakumi.db` se crea/usa en project root

### S2: PG startup (DATABASE_URL set)

**Input:** `DATABASE_URL=postgresql://kakumi:kakumi@localhost:5432/kakumi reflex run`

**Expected:**
- `rxconfig.py` usa env var
- `alembic.ini` no se toca (engine se configura en `env.py` desde env)
- Engine wrapper crea pool PG con `pool_size=5, echo=False, pool_timeout=30`
- `alembic upgrade head` contra PG desde 0 → tablas creadas
- App arranca, misma UX

### S3: Docker Compose PG dev

**Input:** `docker-compose up -d`

**Output:**
- PG 16 container corre en puerto 5432
- `.env.example` → copiar a `.env`
- `DATABASE_URL` apunta a PG
- App conecta y funciona

### S4: CI matrix — SQLite

**Input:** `CI_MATRIX_DB=sqlite && pytest tests/`

**Output:**
- `conftest.py` detecta sin PG → usa fixture in-memory SQLite
- 41+ tests pasan sin cambio

### S5: CI matrix — PostgreSQL

**Input:** `CI_MATRIX_DB=postgres && pytest tests/`

**Output:**
- GitHub Actions service container PG 16
- `DATABASE_URL` apunta a servicio CI
- `conftest.py` crea engine PG en vez de SQLite
- 41+ tests pasan sin cambio

### S6: JSONB read/write

**Input:** Guardar dict `{"ids": [1,2,3]}` en `TournamentCategory.third_`

**Output:**
```python
cat.third_place_ids = {"ids": [1,2,3]}  # dict directo, sin json.dumps
session.add(cat); session.commit()
session.refresh(cat)
assert cat.third_place_ids == {"ids": [1,2,3]}
```

### S7: Rollback

**Input:** `git checkout HEAD -- rxconfig.py alembic.ini alembic/env.py kakumi_app/models/*.py requirements.txt && git rm -r kakumi_app/db/ docker-compose.yml .env.example`

**Output:**
- Proyecto vuelve a estado pre-PG
- `kakumi.db` intacto
- `reflex run` funciona como antes

---

## 3. Acceptance Criteria

| Req | Criterio | Escenario |
|-----|----------|-----------|
| R1 | `os.getenv("DATABASE_URL", "sqlite:///kakumi.db")` se evalúa en tiempo de import de engine wrapper. App arranca con PG si env var set, SQLite si no | S1, S2 |
| R2 | Wrapper expone función `create_engine_url()` + clase `DatabaseEngine` con kwargs `pool_size:int=5, echo:bool=False, pool_timeout:int=30`. PG engine usa esos params vía `sqlalchemy.create_engine` | S2 |
| R3 | Sin env var → URL default SQLite. `reflex run` funciona sin `.env` | S1 |
| R4 | Tests monkeypatchean `rx.model.session` >= wrapper. Wrapper lee `DATABASE_URL` de env, pero test overridea vía monkeypatch como hoy | S1, S4, S5 |
| R5 | `alembic upgrade head` desde proyecto limpio pasa en SQLite y PG. Migraciones no contienen SQL dialect-específico | S2 |
| R6 | `third_place_ids`, `tatami_certified`, `details` cambian de `str` a `sa.Column(sa.JSON, default=None)`. `TournamentCategory.third_place_ids: dict | None` en type hint. En SQLite se almacena como JSON string; en PG como JSONB | S6 |
| R7 | `docker-compose up -d` → PG 16 container healthy. `docker-compose ps` muestra estado Up | S3 |
| R8 | `.env.example` existe con `DATABASE_URL=postgresql://kakumi:kakumi@localhost:5432/kakumi` | S3 |
| R9 | `psycopg2-binary` en `requirements.txt`. `pip install` no falla | S2 |
| R10 | `.github/workflows/tests.yml` tiene matrix `db: [sqlite, postgres]`. Job postgres incluye service `postgres:16` + env var `DATABASE_URL` | S4, S5 |
| R11 | Todos los tests existentes pasan en ambos backends, sin cambiar lógica de tests | S4, S5 |
| R12 | `git diff --stat` post-rollback muestra 0 cambios. `reflex run` funciona | S7 |

---

## 4. Edge Cases

| # | Caso | Comportamiento esperado |
|---|------|------------------------|
| EC1 | `DATABASE_URL` vacío (`""`) | Tratar como no-set → SQLite default |
| EC2 | `DATABASE_URL` set pero PG caído | `sqlalchemy.exc.OperationalError` en startup. App no arranca. Error claro |
| EC3 | Conexión lenta / pool timeout | Engine wrapper `pool_timeout=30` → SQLAlchemy lanza `TimeoutError` después de 30s |
| EC4 | Pool_size=0 | Wrapper ignora `pool_size=0` (pool_class=NullPool). SQLite siempre NullPool |
| EC5 | URL con driver explícito (`postgresql+psycopg2://...`) | Pasar directo a `create_engine`. Sin validación extra |
| EC6 | JSON field guarda `None` | `sa.JSON` con `nullable=True` → NULL en DB. Devuelve `None` |
| EC7 | JSON field guarda lista | `sa.JSON` acepta `list`. Devuelve `list` |
| EC8 | Alembic migration existente intenta ejecutar en PG con dialect SQLite-only | Fresh DB sin history previo. Solo 1 nueva revision con tablas + JSON fields. Sin riesgo |
| EC9 | `conftest.py` usa `monkeypatch.setattr(rx.model, "session", _test_session)` en PG | Funciona igual. No depende de engine interno de Reflex |
| EC10 | `pool_pre_ping=True` en wrapper | No en esta iteración. PG caído se detecta en connect, no pre-ping |

---

## 5. Non-Requirements

- **SQLite → PG data migration** — fresh DB start. No migración de datos legacy
- **Async driver** — Reflex usa sync SQLAlchemy internamente. Async es out-of-scope
- **PgBouncer / connection pooling externo** — SQLAlchemy pool interno suficiente
- **TLS / SSL** — `sslmode` no configurable en esta iteración
- **Read replicas / multi-DB routing** — Única DB
- **Alembic downgrade path** — fresh DB, no necesario
- **Modificar tests existentes** — Solo tocar `conftest.py` para soportar PG fixture. Tests no se editan
- **Soporte MySQL / otros backends** — Exclusivo SQLite + PostgreSQL
- **`DATABASE_URL` en runtime (state)** — Solo se lee en startup
- **`dotenv`/`.env` auto-carga** — Quien deploye carga env vars. Sin `python-dotenv` dependency

---

## 6. Data Contracts

### 6.1 DATABASE_URL

```
Formato: postgresql://<user>:<password>@<host>:<port>/<dbname>
Default: sqlite:///kakumi.db
Driver:  psycopg2 (internamente, usuario puede pasar postgresql+psycopg2://)
```

Ejemplos:

| Context | URL |
|---------|-----|
| Dev default | (no set) → `sqlite:///kakumi.db` |
| Docker Compose | `postgresql://kakumi:kakumi@localhost:5432/kakumi` |
| CI (service container) | `postgresql://postgres:postgres@localhost:5432/kakumi_test` |

### 6.2 Engine wrapper shape

```python
# kakumi_app/db/engine.py

def get_db_url() -> str:
    """Return DATABASE_URL from env, or SQLite default."""
    url = os.getenv("DATABASE_URL", "").strip()
    return url or "sqlite:///kakumi.db"

class DatabaseEngine:
    """Thin wrapper over sqlalchemy.create_engine with pool config."""

    def __init__(
        self,
        url: str | None = None,
        pool_size: int = 5,
        echo: bool = False,
        pool_timeout: int = 30,
    ):
        self.url = url or get_db_url()
        self.pool_size = pool_size
        self.echo = echo
        self.pool_timeout = pool_timeout
        self._engine: sa.Engine | None = None

    def get_engine(self) -> sa.Engine:
        if self._engine is None:
            self._engine = sa.create_engine(
                self.url,
                pool_size=self.pool_size,
                echo=self.echo,
                pool_timeout=self.pool_timeout,
            )
        return self._engine
```

### 6.3 JSON field migration

```python
# ANTES
third_place_ids: Optional[str] = Field(default=None)  # "JSON array de IDs"

# DESPUÉS (TournamentCategory)
third_place_ids: Optional[dict] = Field(
    default=None,
    sa_column=sa.Column(sa.JSON, nullable=True),
)
```

Mismos patrón para:
- `Referee.tatami_certified: Optional[str]` → `Optional[dict]`
- `AuditLog.details: Optional[str]` → `Optional[dict]`

### 6.4 alembic env.py contract

```python
# alembic/env.py
import os
from kakumi_app.db.engine import get_db_url

# En run_migrations_offline y run_migrations_online:
sqlalchemy_url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
# usar sqlalchemy_url para configure() / engine creation
```

`alembic.ini` mantiene `sqlalchemy.url = sqlite:///kakumi.db` como fallback.
`env.py` overridea con `DATABASE_URL` si presente.

### 6.5 CI matrix contract

```yaml
# .github/workflows/tests.yml (section)
strategy:
  matrix:
    db: [sqlite, postgres]
steps:
  - ...
  - name: Run tests
    env:
      DATABASE_URL: ${{ matrix.db == 'postgres' && 'postgresql://postgres:postgres@localhost:5432/kakumi_test' || '' }}
    run: pytest tests/ -v
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: postgres
        POSTGRES_DB: kakumi_test
      ports:
        - 5432:5432
      options: >-
        --health-cmd pg_isready
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
```

---

## 7. Risks (updated from proposal)

| Risk | Like. | Mitigation |
|------|------|------------|
| `rx.model.session` monkeypatch patrón legacy incompatible con PG | Low | `conftest.py` ya parchea `rx.model.session` por un callable que toma `url`. No usa engine interno de Reflex |
| Tests con `sqlite://` en string de conexión hardcodeado | Med | Audit rápido de tests revela 0 hardcodeos de `sqlite:///kakumi.db` en lógica de tests. `monkeypatch` lo abstrae |
| JSONB field guarda `None` y SQLite no puede leerlo | Low | `sa.JSON` con `nullable=True`. SQLite almacena `NULL` como `None`. Compatible |
| Migración `alembic upgrade head` en PG falla por dialect SQLAlchemy no encontrado | Low | `psycopg2-binary` instalado antes de migrar. CI lo testea |
| Tests que usan `rx.session()` dentro de states (no monkeypatch) | High | `rx.session()` interno de Reflex crea engine propio desde `rx.config.db_url`. Si config tiene `sqlite:///kakumi.db` pero env tiene PG, hay split-brain. Mitigar: tests nunca invocan `rx.session()` fuera de monkeypatch. Toda sesión de test pasa por fixture. |
| `rx.config.db_url` no refleja env var en runtime | Low | `rxconfig.py` se ejecuta una vez en import. Si `DATABASE_URL` se setea después, no se propaga. Solución: engine wrapper lee env var en runtime, NO en rxconfig |

---

## 8. Affected files (delta)

| File | Action | Notes |
|------|--------|-------|
| `kakumi_app/db/__init__.py` | **New** | Empty |
| `kakumi_app/db/engine.py` | **New** | `get_db_url()`, `DatabaseEngine` |
| `rxconfig.py` | Modified | `os.getenv("DATABASE_URL", ...)` en `db_url` |
| `alembic.ini` | Modified | `sqlalchemy.url` como fallback SQLite |
| `alembic/env.py` | Modified | Leer `DATABASE_URL` de env, overridear config |
| `kakumi_app/models/tournament_model.py` | Modified | `third_place_ids: str` → `dict` with `sa.JSON` |
| `kakumi_app/models/referee_model.py` | Modified | `tatami_certified: str` → `dict` with `sa.JSON` |
| `kakumi_app/models/audit_log.py` | Modified | `details: str` → `dict` with `sa.JSON` |
| `alembic/versions/` | **New** | 1 revision: create tables + JSON columns |
| `docker-compose.yml` | **New** | PG 16 service |
| `.env.example` | **New** | Template |
| `requirements.txt` | Modified | +`psycopg2-binary` |
| `.github/workflows/tests.yml` | Modified | Matrix sqlite + postgres |
| `tests/conftest.py` | Modified | Soporte para crear engine PG si `DATABASE_URL` set |

---

## 9. Success Criteria (checklist)

- [ ] `reflex run` sin `DATABASE_URL` → SQLite, same UX
- [ ] `DATABASE_URL=postgresql://user:pass@host:5432/db reflex run` → PG
- [ ] Engine wrapper acepta `pool_size`, `echo`, `pool_timeout`
- [ ] `alembic upgrade head` en SQLite y PG desde DB limpia
- [ ] JSONB fields guardan/recuperan Python dict sin `json.dumps`
- [ ] `docker-compose up -d` → PG reachable
- [ ] CI matrix: SQLite + PostgreSQL, todos los tests pasan
- [ ] `git checkout` rollback → proyecto pre-PG, `kakumi.db` intacto