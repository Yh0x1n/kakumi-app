# Pydantic — Reference Documentation

## Official Pydantic v2 Docs

| Resource | URL |
|---|---|
| Main docs | https://docs.pydantic.dev/latest/ |
| v1 → v2 migration guide | https://docs.pydantic.dev/latest/migration/ |
| Validators (`field_validator`, `model_validator`) | https://docs.pydantic.dev/latest/concepts/validators/ |
| `ConfigDict` & model configuration | https://docs.pydantic.dev/latest/concepts/config/ |
| JSON Schema generation | https://docs.pydantic.dev/latest/concepts/json_schema/ |
| `BaseSettings` (pydantic-settings) | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| Serialization (`model_dump`, `field_serializer`) | https://docs.pydantic.dev/latest/concepts/serialization/ |
| Computed fields | https://docs.pydantic.dev/latest/concepts/fields/#computed-fields |
| Generic models | https://docs.pydantic.dev/latest/concepts/postponed_annotations/ |

## SQLModel (SQLAlchemy + Pydantic)

| Resource | URL |
|---|---|
| SQLModel docs | https://sqlmodel.tiangolo.com/ |
| SQLModel + FastAPI tutorial | https://sqlmodel.tiangolo.com/tutorial/fastapi/ |
| SQLModel field options | https://sqlmodel.tiangolo.com/tutorial/create-db-and-table/#field-primary-key |

## Reflex (kakumi-app framework)

| Resource | URL |
|---|---|
| Reflex docs | https://reflex.dev/docs/ |
| Reflex state & database | https://reflex.dev/docs/database/overview/ |
| `rx.Model` (SQLModel wrapper) | https://reflex.dev/docs/database/tables/ |

## Quick Reminders

```
v1 (OLD)              →  v2 (NEW)
─────────────────────────────────────────
class Config:            model_config = ConfigDict(...)
  orm_mode = True          from_attributes=True
.dict()                  .model_dump()
.parse_obj()             .model_validate()
@validator               @field_validator + @classmethod
json_encoders            @field_serializer
```
