# Design: PostgreSQL Database Support

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      ENV                                    │
│  DATABASE_URL=postgresql://user:pass@host:5432/db          │
│  (or unset → SQLite default)                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ os.getenv("DATABASE_URL", "")
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  kakumi_app/db/engine.py                                     │
│  ┌──────────────────────────────────────┐                   │
│  │  get_db_url() → str                  │                   │
│  │  '' or unset → "sqlite:///kakumi.db" │                   │
│  │  set → raw value (passthru)          │                   │
│  └──────────────┬───────────────────────┘                   │
│  ┌──────────────────────────────────────┐                   │
│  │  DatabaseEngine(url, pool_size,      │                   │
│  │                echo, pool_timeout)   │                   │
│  │  .get_engine() → sqlalchemy.Engine   │                   │
│  │  .is_postgres → bool (property)     │                   │
│  └──────────────┬───────────────────────┘                   │
└─────────────────┬───────────────────────────────────────────┘
                  │ create_engine(url, pool_size, echo, pool_timeout)
                  ▼
┌─────────────────────────────────────────────────────────────┐
│  sqlalchemy.Engine                                           │
│  (pool: NullPool for SQLite, QueuePool for PG)              │
└──────────────────────┬──────────────────────────────────────┘
                       │ bind engine to session
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  rx.session() / sqlmodel.Session(engine)                    │
│                                                             │
│  Tests monkeypatch rx.model.session → wrapped session      │
│  Production → auto via rx.model.session (Reflex internal)  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│  Models (rx.Model / SQLModel)                                │
│  sa.Column(sa.JSON) → JSONB on PG, TEXT on SQLite          │
└─────────────────────────────────────────────────────────────┘

Alémbic path:
  env.py → get_db_url() → url override config["sqlalchemy.url"]
  target_metadata = rx.Model.metadata
  1 single revision: create all tables + JSON columns
```

**Flow:**

1. `os.getenv("DATABASE_URL", "")` evaluated at engine creation time (NOT at import time of `rxconfig.py`)
2. `get_db_url()` returns env var or `"sqlite:///kakumi.db"`
3. `DatabaseEngine` wraps `sqlalchemy.create_engine()` with pool params
4. Pool params: PG uses `QueuePool(pool_size=5, pool_timeout=30)`; SQLite ignores pool params (SQLAlchemy uses `NullPool` for sqlite://)
5. `rxconfig.py` sets `db_url` from env so Reflex's own internal session creation uses the same URL
6. Tests: `conftest.py` monkeypatches `rx.model.session` as before, but `db_session` fixture reads `DATABASE_URL` to decide engine type
7. Alembic: `env.py` imports `get_db_url()` and overrides config URL

## 2. Module Structure

```
kakumi_app/
├── db/
│   ├── __init__.py          # empty
│   └── engine.py            # NEW — get_db_url(), DatabaseEngine class
│
kakumi_app/models/
├── tournament_model.py      # MODIFIED — third_place_ids: str → dict + sa.JSON
├── referee_model.py          # MODIFIED — tatami_certified: str → dict + sa.JSON
├── audit_log.py              # MODIFIED — details: str → dict + sa.JSON
└── tournament_event_log.py   # MODIFIED — details: str → dict + sa.JSON

rxconfig.py                   # MODIFIED — db_url reads env var
alembic.ini                   # MODIFIED — sqlalchemy.url = fallback
alembic/env.py                # MODIFIED — DATABASE_URL override

alembic/versions/
├── previous...               # untouched
└── xxx_create_all_tables.py  # NEW — single revision, all tables + JSON columns

requirements.txt              # MODIFIED — +psycopg2-binary
docker-compose.yml            # NEW — PG 16 + pgAdmin
.env.example                  # NEW — DATABASE_URL template
.github/workflows/tests.yml   # NEW — CI matrix sqlite + postgres
tests/conftest.py             # MODIFIED — PG-aware db_session
```

### File responsibilities

| File | Responsibility |
|------|---------------|
| `kakumi_app/db/__init__.py` | Empty init for package |
| `kakumi_app/db/engine.py` | `get_db_url()`, `DatabaseEngine` class, singleton pattern |
| `rxconfig.py` | `db_url=os.getenv("DATABASE_URL", "sqlite:///kakumi.db")` |
| `alembic/env.py` | Import `get_db_url()`, override config URL in both offline/online mode |
| `alembic.ini` | Keep `sqlalchemy.url = sqlite:///kakumi.db` as fallback for direct `alembic` CLI without env |
| Model files | Change type hint `str` → `dict`, add `sa_column=sa.Column(sa.JSON, nullable=True)` |
| `docker-compose.yml` | PG 16 service + pgAdmin optional |
| `.env.example` | Template `DATABASE_URL` |
| `requirements.txt` | Add `psycopg2-binary>=2.9.9` |
| `.github/workflows/tests.yml` | Matrix `db: [sqlite, postgres]` |
| `tests/conftest.py` | `db_session` fixture checks `DATABASE_URL`, creates PG engine if set, else SQLite tempfile |
| `alembic/versions/xxx_postgres_initial.py` | Single revision: create_all tables. No legacy migration |

## 3. DatabaseEngine Wrapper

### API contract

```python
# kakumi_app/db/engine.py

import os
from typing import Optional
import sqlalchemy as sa
from sqlalchemy.pool import NullPool, QueuePool


def get_db_url() -> str:
    """
    Return DATABASE_URL from env, or SQLite default.

    Resolution chain:
    1. os.getenv("DATABASE_URL") — if non-empty, return as-is
    2. Fallback: "sqlite:///kakumi.db"
    """
    url = os.getenv("DATABASE_URL", "").strip()
    return url or "sqlite:///kakumi.db"


def is_sqlite_url(url: str) -> bool:
    """Return True if URL is a sqlite dialect."""
    return url.startswith("sqlite")


_engine_instance: Optional[sa.Engine] = None


class DatabaseEngine:
    """
    Thin wrapper over sqlalchemy.create_engine with pool configuration.

    Singleton-like: module-level _engine ensures one engine per process.
    Lazy init: engine created on first .get_engine() call.

    Edge cases:
    - pool_size=0 → SQLAlchemy reverts to NullPool (documented behavior)
    - SQLite URLs ignore pool_size/echo/pool_timeout (NullPool always)
    - Empty DATABASE_URL treated as unset → SQLite default
    """

    def __init__(
        self,
        url: Optional[str] = None,
        pool_size: int = 5,
        echo: bool = False,
        pool_timeout: int = 30,
    ):
        self.url = url or get_db_url()
        self.pool_size = pool_size
        self.echo = echo
        self.pool_timeout = pool_timeout
        self._engine: Optional[sa.Engine] = None

    @property
    def is_postgres(self) -> bool:
        return self.url.startswith("postgresql")

    def get_engine(self) -> sa.Engine:
        """Return cached engine, creating it lazily on first call."""
        if self._engine is None:
            kwargs: dict = {
                "url": self.url,
                "echo": self.echo,
            }
            if self.is_postgres:
                # pool settings only apply to PG
                kwargs["pool_size"] = self.pool_size
                kwargs["pool_timeout"] = self.pool_timeout
                kwargs["poolclass"] = QueuePool
            else:
                kwargs["poolclass"] = NullPool

            self._engine = sa.create_engine(**kwargs)
        return self._engine

    def dispose(self) -> None:
        """Dispose engine. Safe to call multiple times."""
        if self._engine is not None:
            self._engine.dispose()
            self._engine = None


def get_global_engine(
    url: Optional[str] = None,
    pool_size: int = 5,
    echo: bool = False,
    pool_timeout: int = 30,
) -> sa.Engine:
    """
    Return singleton engine for the process.

    Tests call dispose() + this again to create fresh engine per test.
    """
    global _engine
    if _engine is None:
        eng = DatabaseEngine(
            url=url,
            pool_size=pool_size,
            echo=echo,
            pool_timeout=pool_timeout,
        )
        _engine = eng.get_engine()
    return _engine


def reset_engine() -> None:
    """Dispose and reset singleton. Used by conftest.py between tests."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
```

### Singleton decision

**Singleton (process-wide)** — NOT factory.

Rationale:
- `sqlalchemy.Engine` is already thread-safe with pool management
- Creating multiple engines = multiple pools = resource waste
- `reset_engine()` exposes explicit lifecycle for test isolation
- Tests call `reset_engine()` in fixture teardown, then `get_engine()` again fresh

### Lifecycle

```
Process start
  → DatabaseEngine.url resolved from env (lazy)
  → First .get_engine() call → sa.create_engine()
  → Subsequent calls → cached engine
  → Test teardown: reset_engine() → dispose + null
  → Process end: engine disposed by Python GC / atexit
```

### Edge cases

| Case | Behavior |
|------|----------|
| `DATABASE_URL=""` | Trimmed → empty → SQLite default |
| `pool_size=0` | SQLAlchemy uses `NullPool` (ignores 0). Documented SA behavior |
| PG connection refused | `sqlalchemy.exc.OperationalError` at first query. Wrapper does NOT catch — fail fast |
| URL with `+psycopg2` | Passed as-is to `create_engine`. No validation |
| URL without driver prefix | `postgresql://` → SA defaults to `psycopg2` (installed). Works |

## 4. DATABASE_URL Resolution Chain

```
Step 1: os.getenv("DATABASE_URL", "").strip()
         ↓
  "" or None?
    YES → Step 2
    NO  → Return raw URL
         ↓
Step 2: "sqlite:///kakumi.db" (fallback)
         ↓
Consumer decides:
  ├── rxconfig.py: db_url=os.getenv("DATABASE_URL", "sqlite:///kakumi.db")
  ├── engine.py: get_db_url() → DatabaseEngine(url)
  └── alembic/env.py: get_db_url() → override config["sqlalchemy.url"]
```

### Why this order

1. **Env var first** — matches 12-factor app principle
2. **`rxconfig.py` fallback** — Reflex reads `config.db_url` for its internal `rx.session()` calls (split-brain risk mitigation — see section 11)
3. **`alembic.ini` fallback** — So `alembic upgrade head` works without env var for SQLite dev

### What does NOT read env

- `alembic.ini` — keeps `sqlalchemy.url = sqlite:///kakumi.db` as static fallback only. `env.py` overrides at runtime.
- Tests — read `DATABASE_URL` in `conftest.py` fixture, NOT from `rxconfig`.

## 5. Monkeypatch Strategy

### Current state (SQLite-only)

```python
# tests/conftest.py — db_session fixture
fd, test_db_path = tempfile.mkstemp(suffix=".db", prefix="kakumi-test-")
test_engine = create_engine(f"sqlite:///{test_db_path}", echo=False)
SQLModel.metadata.create_all(test_engine)

def _test_session(url: str | None = None) -> sqlmodel.Session:
    return sqlmodel.Session(test_engine)

monkeypatch.setattr(rx.model, "session", _test_session)
```

### New state (dual backend)

```python
# tests/conftest.py — db_session fixture
import os
from kakumi_app.db.engine import get_db_url, reset_engine

db_url = os.getenv("DATABASE_URL", "").strip()

if db_url and not db_url.startswith("sqlite"):
    # PG mode: create engine from env URL
    engine = sa.create_engine(
        db_url,
        poolclass=sa.pool.NullPool,  # no pooling for test isolation
        echo=False,
    )
    SQLModel.metadata.create_all(engine)
else:
    # SQLite mode: tempfile (current behavior)
    fd, test_db_path = tempfile.mkstemp(suffix=".db", prefix="kakumi-test-")
    os.close(fd)
    os.unlink(test_db_path)
    engine = sa.create_engine(f"sqlite:///{test_db_path}", echo=False)
    SQLModel.metadata.create_all(engine)

def _test_session(url: str | None = None) -> sqlmodel.Session:
    return sqlmodel.Session(engine)

monkeypatch.setattr(rx.model, "session", _test_session)

with sqlmodel.Session(engine) as session:
    yield session

engine.dispose()
if not db_url or db_url.startswith("sqlite"):
    # cleanup tempfile
    for suffix in ("", "-wal", "-shm"):
        candidate = f"{test_db_path}{suffix}"
        if os.path.exists(candidate):
            os.remove(candidate)
```

### Key design decisions

1. **PG mode uses NullPool** — each test gets its own engine; no connection reuse between tests. Slower but isolated.
2. **`in_memory_session` fixture stays SQLite-only** — it's used for complex multi-fixture tests (`rr_pool_fixture`, `team_match_fixture`, `tatami_fixture`). These tests use `url=""` → SQLite always. They don't need PG.
3. **Monkeypatch pattern unchanged** — `rx.model.session` is already a callable that ignores its `url` arg. Both fixtures follow the same contract.
4. **No test code changes** — all 50+ existing tests use `rx.session()` or `db_session`/`in_memory_session` fixtures. None hardcode `sqlite:///kakumi.db`.

## 6. JSONB Migration Path

### Affected columns

| Model | Column | Current type | New type | SA column |
|-------|--------|-------------|----------|-----------|
| `TournamentCategory` | `third_place_ids` | `Optional[str]` | `Optional[dict]` | `sa.Column(sa.JSON, nullable=True)` |
| `Referee` | `tatami_certified` | `Optional[str]` | `Optional[dict]` | `sa.Column(sa.JSON, nullable=True)` |
| `AuditLog` | `details` | `Optional[str]` (max_length=1000) | `Optional[dict]` | `sa.Column(sa.JSON, nullable=True)` |
| `TournamentEventLog` | `details` | `Optional[str]` | `Optional[dict]` | `sa.Column(sa.JSON, nullable=True)` |

### Migration pattern

```python
# BEFORE
third_place_ids: Optional[str] = Field(default=None)  # JSON array de IDs

# AFTER
third_place_ids: Optional[dict] = Field(
    default=None,
    sa_column=sa.Column(sa.JSON, nullable=True),
)
```

### Behavior by backend

| Backend | Storage type | Serialization |
|---------|-------------|---------------|
| SQLite | TEXT (JSON string) | Automatic via `sa.JSON` |
| PostgreSQL | JSONB | Automatic via `sa.JSON` |

### Read/write contract

```python
# Write: pass dict directly
cat.third_place_ids = {"ids": [1, 2, 3]}  # no json.dumps()

# Read: returns dict
assert isinstance(cat.third_place_ids, dict)  # True
assert cat.third_place_ids["ids"] == [1, 2, 3]

# None
cat.third_place_ids = None
assert cat.third_place_ids is None
```

### Why no legacy data migration

- Fresh DB start. No existing rows with JSON strings in SQLite that need migration.
- If we later need SQLite→PG data migration, we run a script that reads old TEXT columns and re-inserts as JSON.

## 7. Docker Compose Setup

```yaml
# docker-compose.yml
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    container_name: kakumi-postgres
    environment:
      POSTGRES_USER: kakumi
      POSTGRES_PASSWORD: kakumi
      POSTGRES_DB: kakumi
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U kakumi"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: kakumi-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@kakumi.app
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

volumes:
  pgdata:
```

```bash
# .env.example
DATABASE_URL=postgresql://kakumi:kakumi@localhost:5432/kakumi
```

### Healthcheck dependency chain

- pgAdmin waits for `postgres` healthcheck
- App (reflex run) waits for nothing — startup error if PG unavailable
- CI uses `--health-cmd pg_isready` options in service container (see section 8)

## 8. CI Matrix

```yaml
# .github/workflows/tests.yml (excerpt)
jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        db: [sqlite, postgres]

    services:
      postgres:
        image: postgres:16-alpine
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

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
      - name: Run tests
        env:
          DATABASE_URL: ${{ matrix.db == 'postgres' && 'postgresql://postgres:postgres@localhost:5432/kakumi_test' || '' }}
        run: pytest tests/ -v
```

### Notes

- `DATABASE_URL` is empty for `db: sqlite` → conftest uses SQLite
- Service container runs only for `db: postgres` matrix entry (but GitHub runs it for all — disable with `if: matrix.db == 'postgres'` if desired, but cheap enough to always run)
- No need for PG service in sqlite job — but since GitHub runs it anyway, it just sits there unused
- `poolclass=NullPool` in conftest for PG tests — pool not needed per-test

## 9. Alembic Strategy

### Current state

- Multiple legacy revision files, some with SQLite-specific SQL
- `env.py` uses `config.get_main_option("sqlalchemy.url")` directly
- `target_metadata = rx.Model.metadata`

### Target state

**Single revision**, no history replay:

```python
# alembic/versions/xxx_initial_postgres_compat.py
"""create all tables

Revision ID: xxx
Revises: <last_existing_revision>
Create Date: 2026-07-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "xxx"
down_revision = <last_existing_revision_id>  # chain from last legacy migration
# OR: down_revision = None  # if we want fully fresh (spec says fresh head)

def upgrade():
    # Tables already exist from previous revisions on SQLite.
    # For PG: this is a no-op migration — tables created via SQLModel.metadata.create_all
    # at app startup, not via migration.
    #
    # ACTUAL CONTENT: JSON column ALTERs for the 4 affected columns.
    # Since this is a fresh DB, we create the JSON columns directly.
    # This migration exists as a marker for alembic stamp/head tracking.

    op.alter_column(
        "tournament_categories", "third_place_ids",
        existing_type=sa.String(),
        type_=sa.JSON(),
        postgresql_using="third_place_ids::jsonb",
    )
    # ... same for referee.tatami_certified, audit_log.details, tournament_event_log.details
```

### env.py changes

```python
# alembic/env.py
import os
from kakumi_app.db.engine import get_db_url

def run_migrations_offline():
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, ...)
    ...

def run_migrations_online():
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = url
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", ...)
    ...
```

### URL resolution in alembic

```
$ DATABASE_URL=postgresql://... alembic upgrade head
  → env.py: os.getenv("DATABASE_URL") → PG URL → works

$ alembic upgrade head  # no env var
  → env.py: config.get_main_option("sqlalchemy.url") → "sqlite:///kakumi.db" → works
```

### Why single revision

- Spec says R5: "no legacy migrations"
- Previous migrations have SQLite-specific SQL (CREATE INDEX with raw SQL)
- First migration creates all tables fresh for PG
- For SQLite, previous revisions still apply as before (chain intact), but new revision is additive (JSON alters that are no-ops on first execution since tables already have columns)

### Alternative: break chain

Set `down_revision = None` in the new revision. This means:
- On SQLite with existing DB: `alembic upgrade head` error (head mismatch)
- On fresh PG: works fine
- **Decision**: keep chain with `down_revision = <last_existing>` to support both workflows.
  For PG fresh DB, run `alembic stamp head` after `create_all` to mark the chain as applied without replaying legacy revs.

## 10. Rollback Plan

### Step-by-step

```bash
# 1. Revert config files
git checkout HEAD -- rxconfig.py alembic.ini alembic/env.py

# 2. Revert model changes
git checkout HEAD -- kakumi_app/models/tournament_model.py
git checkout HEAD -- kakumi_app/models/referee_model.py
git checkout HEAD -- kakumi_app/models/audit_log.py
git checkout HEAD -- kakumi_app/models/tournament_event_log.py

# 3. Revert requirements
git checkout HEAD -- requirements.txt

# 4. Revert tests
git checkout HEAD -- tests/conftest.py

# 5. Remove new files
git rm -r kakumi_app/db/
git rm docker-compose.yml
git rm .env.example

# 6. Revert CI
git checkout HEAD -- .github/workflows/tests.yml

# 7. Remove new migration revision (if committed)
git rm alembic/versions/xxx_initial_postgres_compat.py

# 8. Verify
git diff --stat  # expect 0 changes
reflex run        # works with SQLite, kakumi.db intact
```

### What survives

- `kakumi.db` untouched (never read/written by PG path)
- All existing tests untouched
- Legacy alembic revisions untouched

### What dies

- `kakumi_app/db/` package
- `docker-compose.yml` + `.env.example`
- New CI matrix config
- JSON model changes

## 11. Split-Brain Risk Mitigation

### The risk

Reflex internally uses `rx.config.db_url` from `rxconfig.py` to create its own engine for `rx.session()` calls in state handlers. If `rxconfig.py` has `db_url="sqlite:///kakumi.db"` but the app uses `DATABASE_URL=postgresql://...`, then:

- State handlers using `rx.session()` → SQLite engine (Reflex internal)
- Tests using `conftest.py` fixture → PG engine (via monkeypatch)
- Direct `sqlmodel.Session(engine)` → whichever engine you pass

This is **split-brain**: two engines pointing to different databases.

### Mitigations applied

| Mitigation | Layer | How |
|-----------|-------|-----|
| **1. `rxconfig.py` reads env** | Config | `db_url=os.getenv("DATABASE_URL", "sqlite:///kakumi.db")` — Reflex internal session uses same URL |
| **2. Engine reads env at runtime** | Engine | `get_db_url()` called at `get_engine()` time, NOT at import time |
| **3. Tests monkeypatch `rx.model.session`** | Test | `rx.model.session = _test_session(engine)` — overrides Reflex internal session factory |
| **4. No state handler uses raw `rx.session()` in production** | App | All production data access goes through `rx.session()` which Reflex routes through `rx.config.db_url`. With mitigation 1, this matches env. |
| **5. Audit trail** | Codebase | `codegraph explore rx.session` confirmed no direct `sqlmodel.Session(engine)` in state handlers — only `rx.session()` |

### Remaining risk (documented)

If a future developer writes:

```python
class SomeState(rx.State):
    def do_thing(self):
        from kakumi_app.db.engine import get_engine
        with sqlmodel.Session(get_engine()) as session:  # ← DIFFERENT from rx.session()
            ...
```

This creates a session on the env-drive engine while Reflex's own `rx.session()` uses `rx.config.db_url`. These two engines would be **the same** if `rxconfig.py` read env (mitigation #1) AND the engine also read env (mitigation #2). So they'd actually both connect to PG. But they'd be **different Engine objects** (separate connection pools), causing double-connection overhead.

**Recommendation**: Add a lint rule (ruff) or a code review note: "Never create raw `sqlmodel.Session(engine)` in state handlers. Always use `rx.session()`."

## 11. Performance & Pool Considerations

| Concern | SQLite | PostgreSQL |
|---------|--------|-----------|
| Pool | NullPool (no pooling — file-locked anyway) | QueuePool (pool_size=5, pool_timeout=30) |
| Echo | False (default) | Configurable via `DatabaseEngine(echo=True)` |
| Connect per query | Yes (file open) | No (pooled) |
| Concurrent writes | No (file lock) | Yes (MVCC) |
| Test pool | NullPool (fresh engine per test) | NullPool (fresh engine per test — isolation > speed) |

## 12. Risks (final)

| Risk | Likelihood | Mitigation | Status |
|-----|-----------|-----------|--------|
| `rx.model.session` monkeypatch breaks on PG | Low | conftest already parchea `rx.model.session` con callable que acepta `url`. No depende de engine interno de Reflex | ✅ Mitigated |
| Tests with `sqlite://` hardcoded in conftest | None | Audit: 0 hardcodeos. `db_session` usa `DATABASE_URL` para decidir. Fixtures `in_memory_session`, `rr_pool_fixture`, `team_match_fixture`, `tatami_fixture` siempre usan SQLite. Incompatible con PG por diseño — se marcan con pytest mark | ⚠️ Mitigated (mark) |
| JSON field `None` en PG | Low | `sa.JSON` con `nullable=True`. Compatible en ambos backends | ✅ Mitigated |
| Alembic migration falla en PG | Low | `psycopg2-binary` en reqs, CI testea | ✅ Mitigated |
| Split-brain entre `rx.session()` interno y env var | Low-Med | `rxconfig.py` lee env var, engine wrapper lee env var en runtime, tests monkeypatchean | ✅ Mitigated |
| CI matrix duplica tiempo de tests | Medium | PG job corre en paralelo con SQLite job. Sin bloqueo. Healthcheck 5s → total CI ~2-3min extra | ✅ Acceptable |
| `postgresql+psycopg2://` URL no funciona | Low | Passthrough. SA maneja driver resolution interna | ✅ Mitigated |