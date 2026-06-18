"""Tournament-scoped manual category CRUD state."""

from __future__ import annotations

from typing import Any, Optional

import reflex as rx
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    Modality,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.import_service import ImportService
from kakumi_app.utils import BELT_RANKS


class TournamentCategoryState(rx.State):
    """Manage operator-created categories inside selected tournament workspace."""

    is_editing: bool = False
    show_form: bool = False
    error_message: str = ""
    search_query: str = ""
    current_page: int = 1
    page_size: int = 10

    current_tournament_id: int = 0
    current_tournament_name: str = ""
    _current_tournament_status: str = ""
    categories: list[dict[str, Any]] = []
    current_category: Optional[dict[str, Any]] = None

    name: str = ""
    modality: str = Modality.KATA_INDIVIDUAL.value
    gender: str = "MALE"
    min_age: str = "0"
    max_age: str = "99"
    min_belt_rank: str = ""
    max_belt_rank: str = ""
    competition_system: str = CompetitionSystem.ELIMINATION.value
    bracket_size: str = "8"
    form_judge_panel_size: str = "3"
    form_kata_flow_mode: str = "STANDARD"
    form_scoring_type: str = "average-with-discard"

    # ── Display maps for localized selects ──────────────────────────
    # Internal → Spanish display maps (BIJECTIVE for round-trip safety)
    _GENDER_DISPLAY: dict[str, str] = {
        "MALE": "Masculino",
        "FEMALE": "Femenino",
        "MIXED": "Mixto",
    }
    _MODALITY_DISPLAY: dict[str, str] = {
        Modality.KATA_INDIVIDUAL.value: "Kata Individual",
        Modality.KATA_TEAM.value: "Kata por Equipos",
        Modality.KUMITE_INDIVIDUAL.value: "Kumite Individual",
        Modality.KUMITE_TEAM.value: "Kumite por Equipos",
    }
    _COMPETITION_SYSTEM_DISPLAY: dict[str, str] = {
        CompetitionSystem.ROUND_ROBIN.value: "Liguilla",
        CompetitionSystem.ELIMINATION.value: "Eliminación Directa",
    }

    _SUPPORTED_COMPETITION_SYSTEMS: tuple[str, ...] = (
        CompetitionSystem.ROUND_ROBIN.value,
        CompetitionSystem.ELIMINATION.value,
    )

    # Localized display options for rx.select
    modality_options: list[str] = list(_MODALITY_DISPLAY.values())
    gender_options: list[str] = list(_GENDER_DISPLAY.values())
    competition_system_options: list[str] = list(
        map(_COMPETITION_SYSTEM_DISPLAY.__getitem__, _SUPPORTED_COMPETITION_SYSTEMS)
    )
    bracket_size_options: list[str] = ["4", "8", "16", "32"]

    # Belt rank options
    belt_rank_options: list[str] = [*BELT_RANKS]

    # ── Normalization helpers ───────────────────────────────────────

    def _set_form_open(self, editing: bool) -> None:
        """Open form with desired mode and clean inline errors."""
        self.is_editing = editing
        self.show_form = True
        self.error_message = ""

    def apply_search_query(self, value: str) -> None:
        """Normalize search value and reset pagination cursor."""
        self.search_query = value.strip()
        self.current_page = 1

    def paginate_rows(self, rows: list[dict]) -> list[dict]:
        """Return a deterministic page slice for in-memory rows."""
        if self.page_size <= 0:
            return rows
        start = max(self.current_page - 1, 0) * self.page_size
        end = start + self.page_size
        return rows[start:end]

    def reset_filters(self) -> None:
        """Reset default filter controls used by CRUD pages."""
        self.search_query = ""
        self.current_page = 1

    @staticmethod
    def _normalize_gender(display: str) -> str:
        """Spanish display → internal enum value."""
        rev = {v: k for k, v in TournamentCategoryState._GENDER_DISPLAY.items()}
        return rev.get(display.strip(), display)

    @staticmethod
    def _display_gender(internal: str) -> str:
        """Internal enum value → Spanish display."""
        return TournamentCategoryState._GENDER_DISPLAY.get(internal, internal)

    @staticmethod
    def _normalize_modality(display: str) -> str:
        """Spanish display → internal enum value."""
        rev = {v: k for k, v in TournamentCategoryState._MODALITY_DISPLAY.items()}
        return rev.get(display.strip(), display)

    @staticmethod
    def _display_modality(internal: str) -> str:
        """Internal enum value → Spanish display."""
        return TournamentCategoryState._MODALITY_DISPLAY.get(internal, internal)

    @staticmethod
    def _normalize_competition_system(display: str) -> str:
        """Spanish display → internal enum value."""
        rev = {
            v: k for k, v in TournamentCategoryState._COMPETITION_SYSTEM_DISPLAY.items()
        }
        return rev.get(display.strip(), display)

    @staticmethod
    def _display_competition_system(internal: str) -> str:
        """Internal enum value → Spanish display."""
        return TournamentCategoryState._COMPETITION_SYSTEM_DISPLAY.get(
            internal, internal
        )

    @rx.var
    def has_selected_tournament_context(self) -> bool:
        """Whether category workspace has a selected tournament context."""
        return self.current_tournament_id > 0

    def set_name(self, value: str) -> None:
        """Set category name field."""
        self.name = value

    def set_modality(self, value: str) -> None:
        """Set modality field."""
        self.modality = value

    def set_gender(self, value: str) -> None:
        """Set gender field."""
        self.gender = value

    def set_min_age(self, value: str) -> None:
        """Set minimum age field."""
        self.min_age = value

    def set_max_age(self, value: str) -> None:
        """Set maximum age field."""
        self.max_age = value

    def set_min_belt_rank(self, value: str) -> None:
        """Set minimum belt field."""
        self.min_belt_rank = value

    def set_max_belt_rank(self, value: str) -> None:
        """Set maximum belt field."""
        self.max_belt_rank = value

    def set_competition_system(self, value: str) -> None:
        """Set competition system field."""
        self.competition_system = value

    def set_bracket_size(self, value: str) -> None:
        """Set bracket size field."""
        self.bracket_size = value

    def set_judge_panel_size(self, value: str) -> None:
        """Set judge panel size field."""
        self.form_judge_panel_size = value

    def set_kata_flow_mode(self, value: str) -> None:
        """Set kata flow mode; auto-resets scoring_type on toggle."""
        self.form_kata_flow_mode = value
        if value == "INFORMAL":
            self.form_scoring_type = "INFORMAL"
        else:
            self.form_scoring_type = "average-with-discard"

    def set_scoring_type(self, value: str) -> None:
        """Set scoring type field."""
        self.form_scoring_type = value

    def reset_form(self) -> None:
        """Reset category form to manual defaults."""
        self.name = ""
        self.modality = self._display_modality(Modality.KATA_INDIVIDUAL.value)
        self.gender = self._display_gender("MALE")
        self.min_age = "0"
        self.max_age = "99"
        self.min_belt_rank = ""
        self.max_belt_rank = ""
        self.competition_system = self._display_competition_system(
            CompetitionSystem.ELIMINATION.value
        )
        self.bracket_size = "8"
        self.form_judge_panel_size = "3"
        self.form_kata_flow_mode = "STANDARD"
        self.form_scoring_type = "average-with-discard"
        self.current_category = None

    def _serialize_category(self, category: TournamentCategory) -> dict[str, Any]:
        """Return JSON-safe row for workspace table and edit form."""
        return {
            "id": category.id,
            "name": category.name,
            "modality": self._display_modality(category.modality),
            "gender": self._display_gender(category.gender),
            "min_age": category.min_age,
            "max_age": category.max_age,
            "min_belt_rank": category.min_belt_rank,
            "max_belt_rank": category.max_belt_rank,
            "competition_system": self._display_competition_system(
                category.competition_system
            ),
            "bracket_size": category.bracket_size,
            "judge_panel_size": category.judge_panel_size,
            "kata_flow_mode": category.kata_flow_mode,
            "scoring_type": category.scoring_type,
            "status": category.status,
        }

    def _load_categories(self) -> None:
        """Load only categories belonging to current tournament context."""
        if not self.current_tournament_id:
            self.categories = []
            return

        with rx.session() as session:
            categories = session.exec(
                select(TournamentCategory)
                .where(TournamentCategory.tournament_id == self.current_tournament_id)
                .order_by(TournamentCategory.id)
            ).all()
        self.categories = [
            self._serialize_category(category) for category in categories
        ]

    @rx.event
    async def set_tournament_context(self, tournament_id: int) -> None:
        """Bind manual category workspace to selected tournament."""
        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)

        if tournament is None:
            self.current_tournament_id = 0
            self.current_tournament_name = ""
            self._current_tournament_status = ""
            self.categories = []
            self.error_message = "Torneo no encontrado"
            self.show_form = False
            self.current_category = None
            return

        self.current_tournament_id = tournament.id
        self.current_tournament_name = tournament.name
        self._current_tournament_status = tournament.status
        self.error_message = ""
        self.show_form = False
        self.reset_form()
        self._load_categories()

    def set_form_values(
        self,
        _: Any,
        category: Optional[dict[str, Any]] = None,
    ) -> None:
        """Open form in create or edit mode for selected tournament."""
        if self._current_tournament_status not in {
            TournamentStatus.PLANIFICADO.value,
            TournamentStatus.INSCRIPCION.value,
            TournamentStatus.VERIFICACION.value,
        }:
            self.error_message = (
                "Solo se pueden gestionar categorías en torneos no iniciados"
            )
            return
        if category:
            self.current_category = category
            self._set_form_open(editing=True)
            self.name = category.get("name", "")
            self.modality = self._display_modality(
                category.get("modality", Modality.KATA_INDIVIDUAL.value)
            )
            self.gender = self._display_gender(category.get("gender", "MALE"))
            self.min_age = str(category.get("min_age", 0))
            self.max_age = str(category.get("max_age", 99))
            self.min_belt_rank = category.get("min_belt_rank") or ""
            self.max_belt_rank = category.get("max_belt_rank") or ""
            self.competition_system = self._display_competition_system(
                category.get(
                    "competition_system",
                    CompetitionSystem.ELIMINATION.value,
                )
            )
            self.bracket_size = str(category.get("bracket_size", 8))
            self.form_judge_panel_size = str(category.get("judge_panel_size", 3))
            self.form_kata_flow_mode = category.get("kata_flow_mode", "STANDARD")
            self.form_scoring_type = category.get(
                "scoring_type", "average-with-discard"
            )
            return

        self.reset_form()
        self._set_form_open(editing=False)

    @rx.event
    def cancel_category_form(self) -> None:
        """Close manual category form and clear inline errors."""
        self.show_form = False
        self.error_message = ""

    def _validate_form(self) -> Optional[dict[str, Any]]:
        """Validate manual category input and return normalized payload."""
        if not self.current_tournament_id:
            self.error_message = "Selecciona un torneo primero"
            return None

        if not self.name.strip():
            self.error_message = "Nombre categoría es obligatorio"
            return None

        try:
            min_age = int(self.min_age)
            max_age = int(self.max_age)
        except ValueError:
            self.error_message = "Edad mínima y máxima deben ser numéricas"
            return None

        if min_age < 0 or max_age < 0:
            self.error_message = "Edad mínima y máxima deben ser positivas"
            return None

        if min_age > max_age:
            self.error_message = "Edad mínima no puede ser mayor que edad máxima"
            return None

        min_belt_rank = self.min_belt_rank.strip() or None
        max_belt_rank = self.max_belt_rank.strip() or None
        if min_belt_rank and not ImportService.validate_belt_rank(min_belt_rank):
            self.error_message = "Grado mínimo inválido"
            return None
        if max_belt_rank and not ImportService.validate_belt_rank(max_belt_rank):
            self.error_message = "Grado máximo inválido"
            return None

        if self.modality not in self.modality_options:
            self.error_message = "Modalidad inválida"
            return None
        if self.gender not in self.gender_options:
            self.error_message = "Género inválido"
            return None
        if self.competition_system not in self.competition_system_options:
            self.error_message = "Sistema competitivo inválido"
            return None
        if self.bracket_size not in self.bracket_size_options:
            self.error_message = "Bracket inválido"
            return None

        # Validate kata-specific fields
        if self._normalize_modality(self.modality) in {
            Modality.KATA_INDIVIDUAL.value,
            Modality.KATA_TEAM.value,
        }:
            if self.form_judge_panel_size not in {"3", "5", "7"}:
                self.error_message = "Panel de jueces debe ser 3, 5 o 7"
                return None
            if self.form_kata_flow_mode not in {"STANDARD", "INFORMAL"}:
                self.error_message = "Modo de flujo kata inválido"
                return None
            if self.form_scoring_type not in {
                "average-with-discard",
                "majority-by-judge",
                "INFORMAL",
            }:
                self.error_message = "Tipo de puntuación inválido"
                return None

        self.error_message = ""
        payload: dict[str, Any] = {
            "name": self.name.strip(),
            "modality": self._normalize_modality(self.modality),
            "gender": self._normalize_gender(self.gender),
            "min_age": min_age,
            "max_age": max_age,
            "min_belt_rank": min_belt_rank,
            "max_belt_rank": max_belt_rank,
            "competition_system": self._normalize_competition_system(
                self.competition_system
            ),
            "bracket_size": int(self.bracket_size),
            "tournament_id": self.current_tournament_id,
        }
        # Include kata fields when modality is kata
        if payload["modality"] in {
            Modality.KATA_INDIVIDUAL.value,
            Modality.KATA_TEAM.value,
        }:
            payload["judge_panel_size"] = int(self.form_judge_panel_size)
            payload["kata_flow_mode"] = self.form_kata_flow_mode
            payload["scoring_type"] = self.form_scoring_type
        return payload

    @rx.event
    async def save_category(self) -> Any:
        """Create or update operator-managed category within selected tournament."""
        if self._current_tournament_status not in {
            TournamentStatus.PLANIFICADO.value,
            TournamentStatus.INSCRIPCION.value,
            TournamentStatus.VERIFICACION.value,
        }:
            self.error_message = (
                "Solo se pueden crear categorías en torneos no iniciados"
            )
            return rx.toast.error(self.error_message)
        category_data = self._validate_form()
        if category_data is None:
            return

        with rx.session() as session:
            try:
                if self.is_editing and self.current_category:
                    category_id = self.current_category.get("id")
                    category = (
                        session.get(TournamentCategory, int(category_id))
                        if category_id
                        else None
                    )
                    if category is None:
                        self.error_message = "Categoría no encontrada"
                        return rx.toast.error(self.error_message)

                    for key, value in category_data.items():
                        setattr(category, key, value)

                    session.add(category)
                    session.commit()
                    message = f"Categoría '{category.name}' actualizada"
                else:
                    category = TournamentCategory(**category_data)
                    session.add(category)
                    session.commit()
                    session.refresh(category)
                    message = f"Categoría '{category.name}' creada"
            except SQLAlchemyError:
                session.rollback()
                self.error_message = "Error al guardar categoría"
                return rx.toast.error(self.error_message)

        self.show_form = False
        self.reset_form()
        self._load_categories()
        return rx.toast.success(message)

    @rx.event
    async def delete_category(self, category_id: int) -> Any:
        """Delete manual category only when it has no linked matches."""
        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            if category is None:
                return rx.toast.error("Categoría no encontrada")

            if category.tournament_id != self.current_tournament_id:
                self.error_message = "Categoría fuera del torneo seleccionado"
                return rx.toast.error(self.error_message)

            has_matches = session.exec(
                select(Match.id).where(Match.category_id == category_id)
            ).first()
            if has_matches:
                self.error_message = (
                    "No se puede eliminar categoría con encuentros relacionados"
                )
                return None

            category_name = category.name
            try:
                session.delete(category)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                self.error_message = "Error al eliminar categoría"
                return rx.toast.error(self.error_message)

        self.error_message = ""
        self._load_categories()
        return rx.toast.success(f"Categoría '{category_name}' eliminada")
