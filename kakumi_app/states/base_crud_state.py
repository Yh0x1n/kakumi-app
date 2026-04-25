"""Shared CRUD UI-state mixin for admin entity states."""

from __future__ import annotations


class CrudStateMixin:
    """Pure Python mixin with shared CRUD UI flags and handlers."""

    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""

    def cancel_form(self) -> None:
        """Hide form and clear transient inline errors."""
        self.show_form = False
        self.error_message = ""

    def _set_form_open(self, editing: bool) -> None:
        """Open form with desired mode and clean inline errors."""
        self.is_editing = editing
        self.show_form = True
        self.error_message = ""
