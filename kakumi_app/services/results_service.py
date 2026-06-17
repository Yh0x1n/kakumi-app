"""Read-only aggregation service for tournament results pages."""

from __future__ import annotations

import json
from typing import Any

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.tournament_model import (
    CategoryStatus,
    Match,
    MatchStatus,
    Modality,
    Tournament,
    TournamentCategory,
)
from kakumi_app.services.kata_informal_service import KataInformalService


class ResultsService:
    """Load results-oriented summaries from persisted tournaments/categories."""

    @staticmethod
    def list_tournament_cards() -> list[dict[str, Any]]:
        """Return tournament cards with basic category and match counters."""
        with rx.session() as session:
            tournaments = session.exec(
                select(Tournament).order_by(Tournament.start_date, Tournament.id)
            ).all()

            cards: list[dict[str, Any]] = []
            for tournament in tournaments:
                categories = session.exec(
                    select(TournamentCategory).where(
                        TournamentCategory.tournament_id == tournament.id
                    )
                ).all()
                category_ids = [
                    int(category.id)
                    for category in categories
                    if category.id is not None
                ]
                matches = (
                    session.exec(
                        select(Match).where(Match.category_id.in_(category_ids))
                    ).all()
                    if category_ids
                    else []
                )

                completed_categories = sum(
                    1
                    for category in categories
                    if category.status == CategoryStatus.COMPLETED.value
                )
                completed_matches = sum(
                    1
                    for match in matches
                    if match.status == MatchStatus.COMPLETED.value
                )

                cards.append(
                    {
                        "id": tournament.id,
                        "name": tournament.name,
                        "venue": tournament.venue,
                        "start_date": str(tournament.start_date),
                        "end_date": str(tournament.end_date),
                        "status": tournament.status,
                        "category_count": len(categories),
                        "completed_category_count": completed_categories,
                        "total_match_count": len(matches),
                        "completed_match_count": completed_matches,
                    }
                )

        return cards

    @staticmethod
    def get_tournament_view(tournament_id: int) -> dict[str, Any]:
        """Return tournament summary and per-category progress rows."""
        if tournament_id <= 0:
            raise ValueError("ID de torneo inválido")

        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if tournament is None:
                raise ValueError("Torneo no encontrado")

            categories = session.exec(
                select(TournamentCategory)
                .where(TournamentCategory.tournament_id == tournament_id)
                .order_by(TournamentCategory.id)
            ).all()
            category_ids = [
                int(category.id) for category in categories if category.id is not None
            ]
            matches = (
                session.exec(
                    select(Match)
                    .where(Match.category_id.in_(category_ids))
                    .order_by(Match.category_id, Match.round, Match.position, Match.id)
                ).all()
                if category_ids
                else []
            )

        matches_by_category: dict[int, list[Match]] = {}
        for match in matches:
            matches_by_category.setdefault(match.category_id, []).append(match)

        category_rows: list[dict[str, Any]] = []
        for category in categories:
            category_matches = matches_by_category.get(category.id, [])
            completed_match_count = sum(
                1
                for match in category_matches
                if match.status == MatchStatus.COMPLETED.value
            )
            podium_status = "not_completed"
            is_team_modality = category.modality in {
                Modality.KATA_TEAM.value,
                Modality.KUMITE_TEAM.value,
            }
            is_informal = (
                getattr(category, "kata_flow_mode", "STANDARD") == "INFORMAL"
            )
            if category.status == CategoryStatus.COMPLETED.value:
                if is_team_modality:
                    podium_status = "unsupported_team"
                elif category.first_place_id and category.second_place_id:
                    podium_status = "available"
                else:
                    podium_status = "incomplete"

            category_rows.append(
                {
                    "id": category.id,
                    "tournament_id": tournament.id,
                    "name": category.name,
                    "modality": category.modality,
                    "competition_system": category.competition_system,
                    "status": category.status,
                    "total_match_count": (
                        0 if is_informal else len(category_matches)
                    ),
                    "completed_match_count": (
                        0 if is_informal else completed_match_count
                    ),
                    "podium_status": podium_status,
                    "is_informal": is_informal,
                    "category_results_href": f"/results/category/{category.id}",
                    "bracket_href": f"/tournaments/{tournament.id}/bracket",
                }
            )

        # Second pass: enrich completed categories with podium names
        athlete_ids_for_podium: set[int] = set()
        for cat in categories:
            if cat.status == CategoryStatus.COMPLETED.value:
                if cat.first_place_id:
                    athlete_ids_for_podium.add(cat.first_place_id)
                if cat.second_place_id:
                    athlete_ids_for_podium.add(cat.second_place_id)
                if cat.third_place_ids:
                    try:
                        parsed = json.loads(cat.third_place_ids)
                        if isinstance(parsed, list):
                            athlete_ids_for_podium.update(
                                int(pid) for pid in parsed if pid is not None
                            )
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

        athletes_by_id: dict[int, str] = {}
        if athlete_ids_for_podium:
            with rx.session() as session:
                athlete_rows = session.exec(
                    select(Athlete).where(Athlete.id.in_(sorted(athlete_ids_for_podium)))
                ).all()
                for a in athlete_rows:
                    athletes_by_id[a.id] = a.name

        # Add podium names to category rows
        for row in category_rows:
            cat_id = int(row["id"])
            matching_cat = next((c for c in categories if c.id == cat_id), None)
            if (
                matching_cat
                and matching_cat.status == CategoryStatus.COMPLETED.value
            ):
                row["first_place_name"] = (
                    athletes_by_id.get(matching_cat.first_place_id)
                    if matching_cat.first_place_id
                    else None
                )
                row["second_place_name"] = (
                    athletes_by_id.get(matching_cat.second_place_id)
                    if matching_cat.second_place_id
                    else None
                )
                third_names: list[str] = []
                if matching_cat.third_place_ids:
                    try:
                        parsed = json.loads(matching_cat.third_place_ids)
                        if isinstance(parsed, list):
                            third_names = [
                                athletes_by_id.get(int(pid), "") or ""
                                for pid in parsed
                                if pid is not None
                                and int(pid) in athletes_by_id
                            ]
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass
                row["third_place_display"] = (
                    ", ".join(third_names) if third_names else ""
                )
            else:
                row["first_place_name"] = None
                row["second_place_name"] = None
                row["third_place_display"] = ""

        completed_categories = sum(
            1
            for category in categories
            if category.status == CategoryStatus.COMPLETED.value
        )
        completed_matches = sum(
            1 for match in matches if match.status == MatchStatus.COMPLETED.value
        )

        return {
            "tournament": {
                "id": tournament.id,
                "name": tournament.name,
                "status": tournament.status,
                "venue": tournament.venue,
                "start_date": str(tournament.start_date),
                "end_date": str(tournament.end_date),
            },
            "summary": {
                "total_categories": len(categories),
                "completed_categories": completed_categories,
                "total_matches": len(matches),
                "completed_matches": completed_matches,
            },
            "categories": category_rows,
        }

    @staticmethod
    def get_category_view(category_id: int) -> dict[str, Any]:
        """Return category detail with matches or kata standings."""
        if category_id <= 0:
            raise ValueError("ID de categoría inválido")

        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            if category is None:
                raise ValueError("Categoría no encontrada")

            category_info: dict[str, Any] = {
                "id": category.id,
                "name": category.name,
                "modality": category.modality,
                "competition_system": category.competition_system,
                "status": category.status,
                "gender": category.gender,
                "kata_flow_mode": getattr(category, "kata_flow_mode", "STANDARD"),
            }

            is_kata_informal = (
                getattr(category, "kata_flow_mode", "STANDARD") == "INFORMAL"
            )

            if is_kata_informal:
                standings = KataInformalService.rank_category(category_id)
                athlete_ids = {
                    int(s["athlete_id"])
                    for s in standings
                    if "athlete_id" in s
                }
                athlete_names: dict[int, str] = {}
                if athlete_ids:
                    athletes = session.exec(
                        select(Athlete).where(Athlete.id.in_(athlete_ids))
                    ).all()
                    athlete_names = {a.id: a.name for a in athletes}
                enriched_standings = []
                for s in standings:
                    athlete_id = int(s.get("athlete_id", 0))
                    enriched_standings.append(
                        {
                            "name": athlete_names.get(athlete_id, "—"),
                            "total_score": f"{float(s['final_score']):.3f}",
                            "athlete_id": athlete_id,
                            "rank": int(s.get("rank", 0)),
                            "victory_points": int(s.get("victory_points", 0)),
                            "needs_extra_kata": bool(
                                s.get("needs_extra_kata", False)
                            ),
                        }
                    )
                return {
                    "category": category_info,
                    "standings": enriched_standings,
                    "matches": [],
                }

            matches = session.exec(
                select(Match)
                .where(Match.category_id == category_id)
                .order_by(Match.round, Match.position, Match.id)
            ).all()

            match_summaries = [
                {
                    "id": match.id,
                    "round": match.round,
                    "match_number": match.match_number,
                    "position": match.position,
                    "status": match.status,
                }
                for match in matches
            ]

            result: dict[str, Any] = {
                "category": category_info,
                "matches": match_summaries,
                "standings": None,
            }

            if not match_summaries:
                result["empty_message"] = (
                    "No hay encuentros registrados en esta categoría"
                )

            return result

    @staticmethod
    def get_podiums_view(tournament_id: int) -> dict[str, Any]:
        """Return podium cards for each category in a tournament."""
        if tournament_id <= 0:
            raise ValueError("ID de torneo inválido")

        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if tournament is None:
                raise ValueError("Torneo no encontrado")

            categories = session.exec(
                select(TournamentCategory)
                .where(TournamentCategory.tournament_id == tournament_id)
                .order_by(TournamentCategory.id)
            ).all()

            # Collect athlete IDs to resolve names
            athlete_ids: set[int] = set()
            for cat in categories:
                if cat.first_place_id:
                    athlete_ids.add(cat.first_place_id)
                if cat.second_place_id:
                    athlete_ids.add(cat.second_place_id)
                if cat.third_place_ids:
                    try:
                        parsed = json.loads(cat.third_place_ids)
                        if isinstance(parsed, list):
                            athlete_ids.update(
                                int(pid) for pid in parsed if pid is not None
                            )
                    except (json.JSONDecodeError, TypeError, ValueError):
                        pass

            # Bulk-load athletes
            athletes_by_id: dict[int, str] = {}
            if athlete_ids:
                athlete_rows = session.exec(
                    select(Athlete).where(Athlete.id.in_(athlete_ids))
                ).all()
                for a in athlete_rows:
                    athletes_by_id[a.id] = a.name

        cards: list[dict[str, Any]] = []
        for category in categories:
            is_team_modality = category.modality in {
                Modality.KATA_TEAM.value,
                Modality.KUMITE_TEAM.value,
            }

            if category.status != CategoryStatus.COMPLETED.value:
                podium_status = "not_completed"
            elif is_team_modality:
                podium_status = "unsupported_team"
            elif category.first_place_id and category.second_place_id:
                podium_status = "available"
            else:
                podium_status = "incomplete"

            first_place_name = athletes_by_id.get(category.first_place_id) if category.first_place_id else None  # type: ignore[arg-type]
            second_place_name = athletes_by_id.get(category.second_place_id) if category.second_place_id else None  # type: ignore[arg-type]
            third_place_names: list[str] = []
            if category.third_place_ids:
                try:
                    parsed = json.loads(category.third_place_ids)
                    if isinstance(parsed, list):
                        third_place_names = [
                            athletes_by_id.get(int(pid), "") or ""
                            for pid in parsed
                            if pid is not None and int(pid) in athletes_by_id
                        ]
                except (json.JSONDecodeError, TypeError, ValueError):
                    pass

            third_place_display = ", ".join(
                third_place_names
            ) if third_place_names else ""

            cards.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "modality": category.modality,
                    "competition_system": category.competition_system,
                    "status": category.status,
                    "podium_status": podium_status,
                    "first_place_name": first_place_name,
                    "second_place_name": second_place_name,
                    "third_place_names": third_place_names,
                    "third_place_display": third_place_display,
                }
            )

        return {"categories": cards}

    @staticmethod
    def get_statistics_view(tournament_id: int) -> dict[str, Any]:
        """Return aggregate statistics for a tournament."""
        if tournament_id <= 0:
            raise ValueError("ID de torneo inválido")

        with rx.session() as session:
            tournament = session.get(Tournament, tournament_id)
            if tournament is None:
                raise ValueError("Torneo no encontrado")

            categories = session.exec(
                select(TournamentCategory)
                .where(TournamentCategory.tournament_id == tournament_id)
            ).all()

            category_ids = [c.id for c in categories if c.id is not None]

            matches = (
                session.exec(
                    select(Match).where(Match.category_id.in_(category_ids))
                ).all()
                if category_ids
                else []
            )

        total_categories = len(categories)
        completed_categories = sum(
            1 for c in categories if c.status == CategoryStatus.COMPLETED.value
        )
        total_matches = len(matches)
        completed_matches = sum(
            1 for m in matches if m.status == MatchStatus.COMPLETED.value
        )

        # Breakdown by modality
        by_modality: dict[str, dict[str, int]] = {}
        for c in categories:
            mod = c.modality
            if mod not in by_modality:
                by_modality[mod] = {"total_categories": 0, "completed_categories": 0}
            by_modality[mod]["total_categories"] += 1
            if c.status == CategoryStatus.COMPLETED.value:
                by_modality[mod]["completed_categories"] += 1

        # Breakdown by competition system
        by_system: dict[str, dict[str, int]] = {}
        for c in categories:
            sys = c.competition_system
            if sys not in by_system:
                by_system[sys] = {"total_categories": 0}
            by_system[sys]["total_categories"] += 1

        # Breakdown by match status
        by_match_status: dict[str, int] = {}
        for m in matches:
            ms = m.status
            by_match_status[ms] = by_match_status.get(ms, 0) + 1

        return {
            "total_categories": total_categories,
            "completed_categories": completed_categories,
            "total_matches": total_matches,
            "completed_matches": completed_matches,
            "by_modality": by_modality,
            "by_system": by_system,
            "by_match_status": by_match_status,
        }
