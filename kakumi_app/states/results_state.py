"""Read-only Reflex state for tournament results pages."""

from __future__ import annotations

import logging
from typing import Any

import reflex as rx

from kakumi_app.services.results_service import ResultsService


logger = logging.getLogger(__name__)


class ResultsState(rx.State):
    """State container for results index and tournament hub views."""

    tournaments: list[dict[str, Any]] = []
    current_tournament: dict[str, Any] = {}
    tournament_summary: dict[str, int] = {}
    categories: list[dict[str, Any]] = []
    is_loading: bool = False
    error_message: str = ""
    empty_message: str = ""

    # Category detail
    current_category: dict[str, Any] = {}
    category_data: dict[str, Any] = {}
    category_title: str = ""
    category_standings: list[dict[str, Any]] = []
    category_matches: list[dict[str, Any]] = []

    # Podiums / Statistics (Slice 3)
    selected_tournament_id: int | None = None
    podium_cards: list[dict[str, Any]] = []
    statistics_view: dict[str, Any] = {}
    modality_breakdown: list[dict[str, Any]] = []
    system_breakdown: list[dict[str, Any]] = []
    match_status_breakdown: list[dict[str, Any]] = []

    def _route_params(self) -> dict[str, Any]:
        """Safely resolve route params from router state."""
        try:
            return dict(self.router.page.params)
        except Exception:
            page = getattr(self.router, "_page", None)
            return dict(getattr(page, "params", {}) or {})

    def _parse_route_id(self, key: str = "id") -> int:
        """Parse a route id key or raise ValueError for invalid values."""
        raw_value = self._route_params().get(key)
        if raw_value in (None, ""):
            raise ValueError("ID de torneo inválido")
        try:
            return int(raw_value)
        except (TypeError, ValueError) as error:
            raise ValueError("ID de torneo inválido") from error

    def _reset_tournament_view(self) -> None:
        """Reset tournament-scoped state branches."""
        self.current_tournament = {}
        self.tournament_summary = {}
        self.categories = []

    @rx.event
    async def load_results_index(self) -> None:
        """Load tournament cards for /results index."""
        self.is_loading = True
        self.error_message = ""
        self.empty_message = ""
        self.tournaments = []

        try:
            self.tournaments = ResultsService.list_tournament_cards()
            if not self.tournaments:
                self.empty_message = "No hay torneos con resultados disponibles todavía"
        except Exception:
            logger.exception("Error cargando índice de resultados")
            self.tournaments = []
            self.error_message = "Error cargando resultados"
        finally:
            self.is_loading = False

    @rx.event
    async def load_tournament_view(self) -> None:
        """Load tournament hub summary and categories from route context."""
        self.is_loading = True
        self.error_message = ""
        self.empty_message = ""
        self._reset_tournament_view()

        try:
            tournament_id = self._parse_route_id()
            view = ResultsService.get_tournament_view(tournament_id)
            self.current_tournament = dict(view.get("tournament", {}))
            self.tournament_summary = dict(view.get("summary", {}))
            self.categories = list(view.get("categories", []))
            if not self.categories:
                self.empty_message = "No hay resultados disponibles todavía"
        except ValueError as error:
            self._reset_tournament_view()
            self.error_message = str(error) or "ID de torneo inválido"
        except Exception:
            logger.exception("Error cargando resultados de torneo")
            self._reset_tournament_view()
            self.error_message = "Error cargando resultados"
        finally:
            self.is_loading = False

    def _reset_category_view(self) -> None:
        """Reset category-scoped state branches."""
        self.current_category = {}
        self.category_data = {}
        self.category_title = ""
        self.category_standings = []
        self.category_matches = []

    @rx.event
    async def load_category_view(self) -> None:
        """Load category detail with matches/standings from route."""
        self.is_loading = True
        self.error_message = ""
        self.empty_message = ""
        self._reset_category_view()

        try:
            category_id = self._parse_route_id()
            view = ResultsService.get_category_view(category_id)
            self.current_category = dict(view.get("category", {}))
            self.category_data = dict(view)
            self.category_title = str(view.get("category", {}).get("name", ""))
            self.empty_message = str(view.get("empty_message", ""))
            raw_standings = view.get("standings")
            self.category_standings = list(raw_standings) if raw_standings else []
            self.category_matches = list(view.get("matches", []))
        except ValueError as error:
            self._reset_category_view()
            self.error_message = str(error) or "ID de categoría inválido"
        except Exception:
            logger.exception("Error cargando vista de categoría")
            self._reset_category_view()
            self.error_message = "Error cargando resultados"
        finally:
            self.is_loading = False

    def _parse_context_tournament_id(self) -> int | None:
        """Parse tournament_id from query params; returns None if absent/invalid."""
        raw_value = self._route_params().get("tournament_id")
        if raw_value in (None, ""):
            return None
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    def _reset_podium_view(self) -> None:
        """Reset podium-scoped state."""
        self.podium_cards = []

    def _reset_statistics_view(self) -> None:
        """Reset statistics-scoped state."""
        self.statistics_view = {}
        self.modality_breakdown = []
        self.system_breakdown = []
        self.match_status_breakdown = []

    @rx.event
    async def load_podiums_view(self) -> None:
        """Load podium cards from query param context."""
        self.is_loading = True
        self.error_message = ""
        self._reset_podium_view()
        self._reset_statistics_view()

        try:
            tournament_id = self._parse_context_tournament_id()
            if tournament_id is None:
                self.error_message = "Selecciona un torneo para ver sus podios."
                return
            self.selected_tournament_id = tournament_id
            view = ResultsService.get_podiums_view(tournament_id)
            self.podium_cards = list(view.get("categories", []))
            if not self.podium_cards:
                self.empty_message = "No hay podios disponibles todavía"
        except ValueError as error:
            self._reset_podium_view()
            self.error_message = str(error) or "ID de torneo inválido"
        except Exception:
            logger.exception("Error cargando podios")
            self._reset_podium_view()
            self.error_message = "Error cargando resultados"
        finally:
            self.is_loading = False

    @rx.event
    async def load_statistics_view(self) -> None:
        """Load statistics from query param context."""
        self.is_loading = True
        self.error_message = ""
        self._reset_podium_view()
        self._reset_statistics_view()

        try:
            tournament_id = self._parse_context_tournament_id()
            if tournament_id is None:
                self.error_message = "Selecciona un torneo para ver estadísticas."
                return
            self.selected_tournament_id = tournament_id
            view = ResultsService.get_statistics_view(tournament_id)
            # Flatten dict breakdowns into typed lists for rx.foreach
            by_modality = view.get("by_modality", {})
            self.modality_breakdown = [
                {
                    "modality": mod,
                    "total_categories": data.get("total_categories", 0),
                    "completed_categories": data.get("completed_categories", 0),
                }
                for mod, data in by_modality.items()
            ]
            by_system = view.get("by_system", {})
            self.system_breakdown = [
                {
                    "system": sys,
                    "total_categories": data.get("total_categories", 0),
                }
                for sys, data in by_system.items()
            ]
            by_match_status = view.get("by_match_status", {})
            self.match_status_breakdown = [
                {"status": st, "count": cnt} for st, cnt in by_match_status.items()
            ]
            self.statistics_view = dict(view)
        except ValueError as error:
            self._reset_statistics_view()
            self.error_message = str(error) or "ID de torneo inválido"
        except Exception:
            logger.exception("Error cargando estadísticas")
            self._reset_statistics_view()
            self.error_message = "Error cargando resultados"
        finally:
            self.is_loading = False
