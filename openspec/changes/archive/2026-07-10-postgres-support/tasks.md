# Tasks: PostgreSQL Database Support

## Execution Order

```
T1 (psycopg2) ──────┬──────────────┬──────────────┐
                     │              │              │
T2 (engine.py) ──────┴──┐           │              │
                        │           │              │
T3 (rxconfig.py) ───────┤           │              │
T4 (alembic wiring) ────┤           │              │
T5 (JSONB models) ──────┤           │              │
T6 (docker-compose) ────┤           │              │
T7 (.env.example) ──────┤           │              │
                        │           │              │
T8 (conftest.py) ───────┴───────────┤              │
                                    │              │
T9 (CI matrix) ─────────────────────┤              │
T10 (alembic revision) ─────────────┘              │
                                                   │
T11 (rollback verify) ─────────────────────────────┘
```

---

## T1 — Add psycopg2-binary to requirements.txt

**Description**: Add `psycopg2-binary>=2.9.9` as a production dependency. This is the PostgreSQL adapter SQLAlchemy uses when connecting to a `postgresql://` URL. Reflex/SQLAlchemy auto-discovers the driver — no explicit import needed.

**Files**: `requirements.txt` (modified)

**Dependencies**: None

**Acceptance criteria**:
- `pip install -r requirements.txt` installs psycopg2-binary without error
- `python -c "import psycopg2; print(psycopg2.__version__)"` prints version ≥ 2.9.9

**Estimated effort**: small (1 line)

---

## T2 — Create engine.py with DatabaseEngine wrapper

**Description**: Create `kakumi_app/db/` package with `engine.py` containing:
- `get_db_url()`: reads `DATABASE_URL` env var, returns it or `"sqlite:///kakumi.db"` default
- `DatabaseEngine` class: thin wrapper over `sqlalchemy.create_engine` with `pool_size`, `echo`, `pool_timeout`, `is_postgres` property
- `get_global_engine()`: singleton accessor (process-wide)
- `reset_engine()`: dispose + null for test isolation

Design decisions per spec:
- SQLite → `NullPool` (ignores pool params)
- PostgreSQL → `QueuePool` with configurable pool settings
- Empty DATABASE_URL → treated as unset → SQLite fallback
- Lazy engine creation (first call to `get_engine()`)
- Singleton engine per process; `reset_engine()` for test lifecycle

**Files**:
- `kakumi_app/db/__init__.py` (new, empty)
- `kakumi_app/db/engine.py` (new, ~70 lines)

**Dependencies**: T1 (psycopg2 installed for testing)

**Acceptance criteria**:
- `python -c "from kakumi_app.db.engine import get_db_url, DatabaseEngine; print(get_db_url())"` prints `sqlite:///kakumi.db`
- `DATABASE_URL=postgresql://u:p@localhost:5432/db python -c "from kakumi_app.db.engine import get_db_url; print(get_db_url())"` prints the PG URL
- `DatabaseEngine().is_postgres` returns False for SQLite, True for PG URL
- `get_global_engine()` returns same engine on repeated calls
- `reset_engine()` disposes and clears singleton
- `DatabaseEngine(pool_size=0)` creates engine with `NullPool` (SA behavior)

**Estimated effort**: medium (~75 lines)

---

## T3 — Wire DATABASE_URL in rxconfig.py

**Description**: Change `rxconfig.py` `db_url` from hardcoded `"sqlite:///kakumi.db"` to `os.getenv("DATABASE_URL", "sqlite:///kakumi.db")`. This ensures Reflex's internal `rx.session()` uses the same DB URL as the application, avoiding split-brain between Reflex internal engine and the app engine.

**Files**: `rxconfig.py` (modified, 1 line changed)

**Dependencies**: None (pure `os.getenv`, no imports from engine.py)

**Acceptance criteria**:
- `reflex run` without `DATABASE_URL` uses SQLite (same as before)
- `DATABASE_URL=postgresql://... reflex run` makes Reflex internal session point to PG
- `rx.config.db_url` matches expected URL in both cases

**Estimated effort**: small (1 line)

---

## T4 — Wire DATABASE_URL in alembic.ini + env.py

**Description**: Modify `alembic/env.py` to read `DATABASE_URL` from environment with `get_db_url()` as fallback. `alembic.ini` keeps `sqlite:///kakumi.db` as static fallback — `env.py` overrides at runtime.

Changes:
- `alembic/env.py`: import `get_db_url()` from engine, override `sqlalchemy.url` in both `run_migrations_offline()` and `run_migrations_online()` if `DATABASE_URL` is set
- `alembic.ini`: add comment that `sqlalchemy.url` is overridden by env var

**Files**:
- `alembic.ini` (modified, comment added)
- `alembic/env.py` (modified, ~15 lines)

**Dependencies**: T2 (imports `get_db_url` from engine.py)

**Acceptance criteria**:
- `alembic upgrade head` without env var uses SQLite (same as before)
- `DATABASE_URL=postgresql://... alembic upgrade head` uses PG
- `DATABASE_URL="" alembic upgrade head` falls back to SQLite
- `DATABASE_URL=postgresql://... alembic history` shows revision chain

**Estimated effort**: small (~20 lines)

---

## T5 — Migrate string JSON fields to JSONB + update service callers

**Description**: Change 4 model fields from `Optional[str]` (JSON-as-string) to `Optional[dict]` with `sa.Column(sa.JSON, nullable=True)`. Then update all service/state/page code that reads/writes these fields.

**Backward compat note**: SQLAlchemy `sa.JSON` column accepts both `str` and `dict` values. Strings serialize as JSON strings and deserialize to Python strings. This means existing tests that pass strings continue to work. Services that do `json.loads()` must check type first — only call `json.loads` if value is still a `str` (old path), use directly if already a `dict` (new path).

### Part A — Model changes

| Model | Column | Current | New |
|-------|--------|---------|-----|
| `TournamentCategory` | `third_place_ids` | `Optional[str]` | `Optional[dict]` + `sa.JSON` |
| `Referee` | `tatami_certified` | `Optional[str]` | `Optional[dict]` + `sa.JSON` |
| `AuditLog` | `details` | `Optional[str]` (max_length=1000) | `Optional[dict]` + `sa.JSON` |
| `TournamentEventLog` | `details` | `Optional[str]` | `Optional[dict]` + `sa.JSON` |

Per-field changes:
1. Type hint `Optional[str]` → `Optional[dict]`
2. Add `sa_column=sa.Column(sa.JSON, nullable=True)` to `Field()`
3. Remove `max_length` (irrelevant for `sa.JSON`)
4. Add `import sqlalchemy as sa` if missing

### Part B — Service/state/page updates (must audit + fix)

Current code uses `json.loads(value)` and `json.dumps(value)` on these fields. After JSON column migration:
- `json.dumps(x)` before assign → **remove** `json.dumps`, assign `x` directly
- `json.loads(value)` on read → guard with `isinstance(value, str)` check

**Files to update** (all modified):

| File | Changes needed | Lines |
|------|---------------|-------|
| `kakumi_app/models/tournament_model.py` | `third_place_ids` → `dict` + `sa.JSON` | ~3 |
| `kakumi_app/models/referee_model.py` | `tatami_certified` → `dict` + `sa.JSON` | ~3 |
| `kakumi_app/models/audit_log.py` | `details` → `dict` + `sa.JSON` | ~3 |
| `kakumi_app/models/tournament_event_log.py` | `details` → `dict` + `sa.JSON` | ~3 |
| `kakumi_app/services/results_service.py` | Guard 4 `json.loads()` calls with `isinstance` check | ~15 |
| `kakumi_app/services/kata_informal_service.py` | Remove `json.dumps()`, assign list/dict directly | ~3 |
| `kakumi_app/services/tournament_service.py` | `third_place_ids` truthiness check (still works) | ~1 |
| `kakumi_app/states/referee_state.py` | `tatami_certified: str = ""` → needs type handling | ~10 |
| `kakumi_app/pages/registries.py` | `tatami_certified` binding (state var → str, fine) | ~1 |

**Dependencies**: T2 (engine wrapper for testing)

**Acceptance criteria**:
- `cat.third_place_ids = {"ids": [1,2,3]}` persists, reads back as `dict` — no `json.dumps`/`json.loads`
- `cat.third_place_ids = None` → reads as `None`
- Existing tests pass unchanged (strings via `third_place_ids="[3]"` still round-trip correctly — `sa.JSON` serializes strings as JSON strings, returns Python strings)
- Services with `json.loads`: guard with `isinstance(val, str)` — only parse if string, use directly if dict
- `kata_informal_service.py`: `category.third_place_ids = json.dumps(...)` → `category.third_place_ids = [...]`
- `referee_state.py`: `tatami_certified` state var must handle `dict | str` from DB
- All 34 reference sites audited and handled

**Estimated effort**: large (~50 lines across 8 files)

**⚠️ Known call sites (34 total)**:
- `test_results_service.py` (4): pass strings — fine, `sa.JSON` round-trips strings
- `test_crud_state_mixin.py` (4): `tatami_certified='["A", "B"]'` — fine
- `test_kata_informal_service.py` (1): `third_place_ids` string comparision — fine
- `test_tournament_state_flows.py` (1): `third_place_ids="[3]"` — fine
- `results_service.py` (8): must add `isinstance` guards before `json.loads`
- `kata_informal_service.py` (1): remove `json.dumps`, assign list directly
- `tournament_service.py` (1): truthiness check OK for both str/dict
- `referee_state.py` (6): `tatami_certified` as `str` var + `json.loads` — must handle dict
- `registries.py` (2): reads from state var — fine if state handles conversion

---

## T6 — Create docker-compose.yml

**Description**: Create `docker-compose.yml` with PostgreSQL 16 (Alpine) and pgAdmin 4 for local development. PG service includes:
- Persistent volume for data
- Healthcheck with `pg_isready`
- Port 5432 exposed
- Credentials: `kakumi`/`kakumi`, database `kakumi`

pgAdmin service:
- Port 5050:80
- Depends on postgres healthcheck
- Credentials: `admin@kakumi.app`/`admin`

**Files**: `docker-compose.yml` (new)

**Dependencies**: None

**Acceptance criteria**:
- `docker-compose up -d` starts both containers
- `docker-compose ps` shows both services as `Up`
- `pg_isready -h localhost -U kakumi` returns `accepting connections`
- `docker-compose down -v` cleans up without errors

**Estimated effort**: medium (~45 lines)

---

## T7 — Create .env.example

**Description**: Create `.env.example` with `DATABASE_URL` template pointing to Docker Compose PostgreSQL. Single line, documented with comment.

**Files**: `.env.example` (new)

**Dependencies**: None

**Acceptance criteria**:
- File exists with `DATABASE_URL=postgresql://kakumi:kakumi@localhost:5432/kakumi`
- Copy to `.env` → `reflex run` connects to PG

**Estimated effort**: small (1 line)

---

## T8 — Modify conftest.py for dual SQLite + PostgreSQL support

**Description**: Refactor `tests/conftest.py` `db_session` fixture to detect `DATABASE_URL` from env and create the appropriate engine:

- `DATABASE_URL` set + not sqlite → PostgreSQL engine with `poolclass=NullPool`
- No `DATABASE_URL` or sqlite → SQLite tempfile (current behavior)
- `in_memory_session` fixture stays SQLite-only (used by complex multi-fixture tests like `rr_pool_fixture`, `team_match_fixture`, `tatami_fixture`)
- `reset_engine()` called in fixture teardown for PG mode
- Monkeypatch pattern unchanged (`rx.model.session` callable override)

Design per spec:
- PG mode uses `NullPool` (test isolation over speed)
- Tempfile cleanup only for SQLite path
- Existing `in_memory_session`, `rr_pool_fixture`, `team_match_fixture`, `tatami_fixture` fixtures unchanged (always SQLite)

**Files**: `tests/conftest.py` (modified, ~30 lines)

**Dependencies**: T2 (imports `get_db_url`, `reset_engine`), T5 (JSONB models must be in place for test data)

**Acceptance criteria**:
- `pytest tests/ -v` without `DATABASE_URL` → all tests pass (SQLite, same as before)
- `DATABASE_URL=postgresql://postgres:postgres@localhost:5432/kakumi_test pytest tests/ -v` → all tests pass (PG)
- `in_memory_session` fixture still works (SQLite in-memory)
- `rr_pool_fixture`, `team_match_fixture`, `tatami_fixture` still work
- Zero test logic changes (only fixture layer changed)

**Estimated effort**: medium (~35 lines)

---

## T9 — CI matrix in GitHub Actions

**Description**: Create `.github/workflows/tests.yml` with matrix strategy `db: [sqlite, postgres]`. For `db: postgres`, include PostgreSQL 16 service container with healthcheck and pass `DATABASE_URL` env var.

Structure:
- Single job `test` with matrix
- Python 3.12
- Install from `requirements.txt`
- `DATABASE_URL` set for postgres job, empty for sqlite job
- PostgreSQL service container with `pg_isready` healthcheck
- Run `pytest tests/ -v`

**Files**: `.github/workflows/tests.yml` (new)

**Dependencies**: T1 (psycopg2 in reqs), T8 (conftest handles both backends)

**Acceptance criteria**:
- CI workflow runs both SQLite and PostgreSQL jobs
- SQLite job passes without any PG container
- PostgreSQL job connects to service container and passes
- Matrix variable `DATABASE_URL` is empty for sqlite → uses SQLite default
- All tests pass in both jobs

**Estimated effort**: medium (~50 lines)

---

## T10 — Create Alembic revision for PostgreSQL compatibility

**Description**: Create new Alembic revision that:
- Chains from current head (`52613ac909db`)
- Uses `alembic.op.alter_column` to mark JSON column type changes
- For SQLite: alter_column is a no-op (same column in `create_all`)
- For PG: sets `postgresql_using` for safe JSONB cast
- Exists as a migration marker for alembic chain integrity

The revision content:
```python
revision = "<generated>"
down_revision = "52613ac909db"

def upgrade():
    op.alter_column("tournament_categories", "third_place_ids",
                    existing_type=sa.String(), type_=sa.JSON(),
                    postgresql_using="third_place_ids::jsonb")
    op.alter_column("referees", "tatami_certified",
                    existing_type=sa.String(), type_=sa.JSON(),
                    postgresql_using="tatami_certified::jsonb")
    op.alter_column("audit_logs", "details",
                    existing_type=sa.String(), type_=sa.JSON(),
                    postgresql_using="details::jsonb")
    op.alter_column("tournament_event_logs", "details",
                    existing_type=sa.String(), type_=sa.JSON(),
                    postgresql_using="details::jsonb")
```

For clean DB (fresh start): `alembic stamp head` marks all revisions as applied.
For existing SQLite DB: `alembic upgrade head` applies this as a no-op alter.

**Files**:
- `alembic/versions/xxx_postgres_json_support.py` (new, ~55 lines)

**Dependencies**: T4 (alembic env.py wiring), T5 (JSONB model changes)

**Acceptance criteria**:
- `alembic upgrade head` succeeds on SQLite from existing DB (no-op alter)
- `DATABASE_URL=postgresql://... alembic upgrade head` succeeds on fresh PG
- `alembic heads` shows new revision as head
- `alembic history` shows correct chain
- `python -c "from alembic.config import Config; from alembic import command; c = Config('alembic.ini'); command.upgrade(c, 'head')"` works

**Estimated effort**: medium (~55 lines)

---

## T11 — Rollback verification

**Description**: Verify the full rollback plan works per spec S7. Create a small verification script / document the steps. This is a procedural task — no code changes.

Rollback steps to verify:
```bash
git checkout HEAD -- rxconfig.py alembic.ini alembic/env.py
git checkout HEAD -- kakumi_app/models/tournament_model.py
git checkout HEAD -- kakumi_app/models/referee_model.py
git checkout HEAD -- kakumi_app/models/audit_log.py
git checkout HEAD -- kakumi_app/models/tournament_event_log.py
git checkout HEAD -- requirements.txt
git checkout HEAD -- tests/conftest.py
git rm -r kakumi_app/db/
git rm docker-compose.yml
git rm .env.example
git checkout HEAD -- .github/workflows/tests.yml
git rm alembic/versions/xxx_postgres_json_support.py
git diff --stat  # expect 0 changes
reflex run        # works with SQLite
```

**Files**: None (git operations only)

**Dependencies**: T10 (all changes in place)

**Acceptance criteria**:
- After rollback, `git diff --stat` shows 0 changes (committed state)
- `reflex run` starts with SQLite as before
- `kakumi.db` untouched
- All tests pass without PG

**Estimated effort**: small (verification only)
