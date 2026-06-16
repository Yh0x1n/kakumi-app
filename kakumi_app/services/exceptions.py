"""Custom exceptions for the penalty and scheduling system."""

from dataclasses import dataclass
from typing import Any


class AppError(Exception):
    """General application error."""


@dataclass
class ValidationError(Exception):
    """
    Error de validación de pre-condición.

    Incluye código de error, mensaje legible y contexto específico
    de categoría cuando aplica.
    """

    code: str
    message: str
    category_name: str | None = None
    current_value: Any = None
    required_value: Any = None

    def __str__(self) -> str:
        """Return the human-readable validation message."""
        return self.message
