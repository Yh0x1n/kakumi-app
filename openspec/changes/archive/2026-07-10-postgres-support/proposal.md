# Proposal: PostgreSQL Database Support

## Intent

SQLite-only locks app to dev use. No env-var config, no PG driver, no pool control. Need production DB path. SQLite stays for dev/test.

## Scope

**In:**
- `DATABASE_URL` env var — `rxconfig.py`, `alembic.ini`, `env.py` read from it
- Thin `rx.session()` wrapper — configurable pool_size, echo, pool_timeout
- `psycopg2-binary` dep, Docker Compose (PG 16 + pgAdmin)
- Alembic works on SQLite + PG
- CI matrix: tests on SQLite + PostgreSQL (service container)
- JSON string fields → JSONB (e.g. `third_place_ids`)
- Fresh DB — no legacy migration

**Out:**
- SQLite→PG data migration (fresh start)
- Async driver swap (Reflex uses sync SQLAlchemy internally)
- PgBouncer, read replicas, TLS

## Capabilities

### New
- `multi-database-config`: Env-var-driven DB URL — SQLite dev, PG prod
- `database-engine-wrapper`: Configurable `rx.session()` + pool settings
- `jsonb-field-support`: JSONB for JSON-string model fields

### Modified
None

## Approach

1. Add `psycopg2-binary` + `python-dotenv`
2. `kakumi_app/db/engine.py` — `get_db_url()`, wrapper
3. `rxconfig.py` → `os.getenv("DATABASE_URL", "sqlite:///kakumi.db")`
4. `alembic.ini` + `env.py` → read `DATABASE_URL`
5. `docker-compose.yml` (PG 16) + `.env.example`
6. Test PG marker, skip-if-no-PG
7. CI matrix: sqlite + postgres
8. String fields → `Column(sa_type=JSON)`, fresh revision

## Affected Areas

| Area | Impact |
|------|--------|
| `rxconfig.py` | Modified |
| `alembic.ini`, `env.py` | Modified |
| `kakumi_app/db/engine.py` | **New** |
| `kakumi_app/models/*.py` | Modified — string→JSONB |
| `requirements.txt` | Modified — +psycopg2-binary |
| `docker-compose.yml`, `.env.example` | **New** |
| `tests/conftest.py` | Modified — PG marker |
| CI config | Modified — matrix |

## Risks

| Risk | Like. | Mitigation |
|------|-------|------------|
| `rx.session()` API changes | Low-Med | Wrapper = single patch point |
| Legacy migrations have PG-incompat SQL | Medium | Fresh head, no history replay |
| JSONB field data loss | Low | Fresh DB, no legacy migration |
| CI slower with PG | Medium | Healthcheck + marker isolation |
| monkeypatch tests break on PG | High | Refactor to real DB sessions |

## Rollback

`git checkout` config + models, `git rm -r kakumi_app/db/ docker-compose.yml .env.example`. `kakumi.db` untouched.

## Success Criteria

- [ ] `reflex run` with `DATABASE_URL=postgresql://...` connects to PG, same UX
- [ ] `DATABASE_URL` unset → SQLite — zero dev regression
- [ ] Engine wrapper exposes pool_size, echo, pool_timeout
- [ ] `alembic upgrade head` succeeds on both SQLite and PG from clean state
- [ ] JSONB fields store/retrieve Python dicts — no manual `json.dumps`
- [ ] CI runs matrix: SQLite + PostgreSQL
- [ ] `docker-compose up -d` → PG reachable, app connects
- [ ] All existing tests pass under both backends
