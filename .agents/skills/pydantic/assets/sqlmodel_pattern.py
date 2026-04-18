"""
SQLModel + Pydantic v2 — ready-to-use integration pattern for kakumi-app.

Pattern:
  - rx.Model  →  database table (SQLModel under the hood)
  - Pydantic BaseModel schema  →  API/service boundary validation
  - model_validate(orm_obj)  →  ORM → schema conversion

Usage:
  athlete = session.get(Athlete, athlete_id)
  schema = AthleteSchema.model_validate(athlete)
  payload = schema.model_dump()
"""

from __future__ import annotations

from typing import Optional

import reflex as rx
from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from sqlmodel import Field


# ── Database model (SQLModel via rx.Model) ────────────────────────────────────


class Athlete(rx.Model, table=True):
    """Represents a karate competitor stored in the DB."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    weight_kg: float
    category_id: int = Field(foreign_key="category.id")
    is_active: bool = Field(default=True)


# ── Pydantic schema (read / API boundary) ────────────────────────────────────


class AthleteSchema(BaseModel):
    """
    Pydantic v2 schema for validating and serialising Athlete ORM objects.

    Key points:
    - `from_attributes=True` enables ORM → Pydantic conversion.
    - field_validator must be @classmethod.
    - model_validator(mode='after') runs after all fields are populated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    weight_kg: float
    category_id: int
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("weight_kg")
    @classmethod
    def weight_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("weight_kg must be a positive number")
        return v

    @model_validator(mode="after")
    def active_athlete_needs_category(self) -> "AthleteSchema":
        """Cross-field: active athletes must have a valid category."""
        if self.is_active and self.category_id <= 0:
            raise ValueError("active athlete must have a valid category_id (> 0)")
        return self


# ── Write schema (creation payload, no id yet) ───────────────────────────────


class AthleteCreate(BaseModel):
    """Schema for creating a new Athlete — id is assigned by the DB."""

    name: str
    weight_kg: float
    category_id: int
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


# ── Usage examples ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Simulate reading from DB and converting to schema
    fake_orm_obj = Athlete(
        id=1,
        name="  Ana García  ",
        weight_kg=60.5,
        category_id=2,
        is_active=True,
    )

    schema = AthleteSchema.model_validate(fake_orm_obj)
    print(schema.model_dump())
    # {'id': 1, 'name': 'Ana García', 'weight_kg': 60.5, 'category_id': 2, 'is_active': True}

    print(schema.model_dump_json())
    # JSON string equivalent
