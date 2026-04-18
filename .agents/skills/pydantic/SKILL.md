---
name: pydantic
description: >
  Pydantic v2 data validation, settings management, and SQLModel integration patterns.
  Trigger: When writing Pydantic models, validators, BaseSettings, or SQLModel schemas.
license: Apache-2.0
metadata:
  author: gentleman-programming
  version: "1.0"
---

## When to Use

- Writing or reviewing Pydantic `BaseModel` classes
- Settings management via `BaseSettings`
- Validating input data at service/state boundaries
- Writing SQLModel-compatible schemas (`from_attributes=True`)
- Migrating v1 → v2 patterns

---

## Critical Patterns

1. **Always use `ConfigDict`** — never inner `class Config` (Pydantic v2 only).
2. **Use `model_dump()` / `model_validate()`** — NOT `.dict()` / `.parse_obj()` (v1 relics).
3. **`from_attributes=True`** is required when validating SQLModel ORM objects into a Pydantic schema.
4. **`@field_validator` must be `@classmethod`**; use `@model_validator(mode='after')` for cross-field validation.
5. **SQLModel + constraints**: use `Field(..., sa_column=Column(...))` when you need DB-level constraints alongside Pydantic constraints.
6. **Never use `json_encoders` in v2** — replace with `@field_serializer`.
7. **`BaseSettings`**: use `model_config = SettingsConfigDict(env_file='.env')` to read `.env` files automatically.
8. **Async tests**: use `@pytest.mark.anyio` (not `@pytest.mark.asyncio`) — matches kakumi-app test setup.

---

## Code Examples

### 1 — SQLModel-compatible Pydantic schema

```python
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

class AthleteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # ORM → Pydantic

    id: int
    name: str
    weight_kg: float
    category_id: int

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()

    @model_validator(mode="after")
    def check_weight_positive(self) -> "AthleteRead":
        if self.weight_kg <= 0:
            raise ValueError("weight_kg must be positive")
        return self


# Usage — from ORM object:
# athlete_read = AthleteRead.model_validate(orm_athlete)
```

### 2 — BaseSettings for env config

```python
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "kakumi-app"
    debug: bool = False
    database_url: str = "sqlite:///kakumi.db"
    secret_key: str = "change-me-in-production"


@lru_cache
def get_settings() -> Settings:
    return Settings()

# Usage:
# from kakumi_app.config import get_settings
# settings = get_settings()
```

### 3 — v1 → v2 migration cheatsheet

```python
# ── v1 (OLD) ─────────────────────────────────────────
from pydantic import BaseModel, validator

class OldModel(BaseModel):
    name: str

    class Config:
        orm_mode = True

    @validator("name")
    def check_name(cls, v):
        return v.strip()

obj = OldModel.parse_obj({"name": "  ana  "})
data = obj.dict()

# ── v2 (NEW) ─────────────────────────────────────────
from pydantic import BaseModel, ConfigDict, field_validator

class NewModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)  # orm_mode → from_attributes
    name: str

    @field_validator("name")          # @validator → @field_validator
    @classmethod                      # must be classmethod
    def check_name(cls, v: str) -> str:
        return v.strip()

obj = NewModel.model_validate({"name": "  ana  "})  # parse_obj → model_validate
data = obj.model_dump()                              # .dict() → .model_dump()
```

---

## Commands

```bash
# Install Pydantic v2 + settings support
pip install "pydantic>=2.0" pydantic-settings

# Run tests (kakumi-app uses anyio)
python -m pytest tests/ -v

# Check a model's JSON schema
python -c "from my_module import MyModel; import json; print(json.dumps(MyModel.model_json_schema(), indent=2))"
```

---

## Resources

- **Templates**: See [assets/sqlmodel_pattern.py](assets/sqlmodel_pattern.py) for SQLModel+Pydantic integration
- **Templates**: See [assets/settings_pattern.py](assets/settings_pattern.py) for BaseSettings singleton
- **Documentation**: See [references/docs.md](references/docs.md) for official links
