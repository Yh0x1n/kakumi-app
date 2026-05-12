"""Service layer for informal Kata round-robin ranking flow."""

from __future__ import annotations

import json
from dataclasses import dataclass

import reflex as rx
from sqlmodel import select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.kata_model import (
    KataInformalJudgeScore,
    KataInformalPerformance,
    KataInformalPerformanceStatus,
    KataRoundStanding,
)
from kakumi_app.models.tournament_model import Match
from kakumi_app.models.tournament_model import CategoryStatus, TournamentCategory


@dataclass
class InformalScoreComputation:
    """Computed fields derived from one athlete panel run."""

    final_score: float
    kept_score_sum: float
    highest_score: float
    lowest_score: float
    max_judge_score: float


class KataInformalService:
    """Persistence and ranking helpers for informal Kata mode."""

    @staticmethod
    def _victory_points_by_athlete(category_id: int) -> dict[int, int]:
        """Aggregate criterion-1 victory points from category encounters."""
        with rx.session() as session:
            matches = session.exec(
                select(Match.id).where(Match.category_id == category_id)
            ).all()
            match_ids = [
                int(row[0]) if isinstance(row, tuple) else int(row) for row in matches
            ]
            if not match_ids:
                return {}

            rows = session.exec(
                select(KataRoundStanding).where(
                    KataRoundStanding.match_id.in_(match_ids)
                )
            ).all()

        points: dict[int, int] = {}
        for row in rows:
            if row.athlete_id is None:
                continue
            athlete_id = int(row.athlete_id)
            points[athlete_id] = points.get(athlete_id, 0) + int(row.victory_points)
        return points

    @staticmethod
    def _head_to_head_winner(
        category_id: int,
        athlete_a_id: int,
        athlete_b_id: int,
    ) -> int | None:
        """Resolve criterion-2 encounter winner for two athletes."""
        with rx.session() as session:
            matches = session.exec(
                select(Match).where(Match.category_id == category_id)
            ).all()
            for match in matches:
                pair = {match.aka_id, match.ao_id}
                if pair != {athlete_a_id, athlete_b_id}:
                    continue

                standing_rows = session.exec(
                    select(KataRoundStanding).where(
                        KataRoundStanding.match_id == match.id
                    )
                ).all()
                athlete_points: dict[int, int] = {}
                for standing in standing_rows:
                    if standing.athlete_id is None:
                        continue
                    athlete_points[int(standing.athlete_id)] = int(
                        standing.victory_points
                    )

                a_points = athlete_points.get(athlete_a_id)
                b_points = athlete_points.get(athlete_b_id)
                if a_points is None or b_points is None:
                    continue
                if a_points > b_points:
                    return athlete_a_id
                if b_points > a_points:
                    return athlete_b_id
        return None

    @staticmethod
    def _resolve_same_points_group(
        category_id: int,
        group: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Apply criterion-2 then criterion-3 inside same VP group."""
        if len(group) == 2:
            first = int(group[0]["athlete_id"])
            second = int(group[1]["athlete_id"])
            winner = KataInformalService._head_to_head_winner(
                category_id, first, second
            )
            if winner is not None:
                if winner != first:
                    return [group[1], group[0]]
                return group

        group.sort(key=lambda item: float(item["max_judge_score"]), reverse=True)
        if len(group) > 1:
            top_score = float(group[0]["max_judge_score"])
            tied = [
                item for item in group if float(item["max_judge_score"]) == top_score
            ]
            if len(tied) > 1:
                for row in tied:
                    row["needs_extra_kata"] = True
        return group

    @staticmethod
    def _compute_score(judge_scores: list[float]) -> InformalScoreComputation:
        """Compute final score using WKF panel average logic."""
        if len(judge_scores) != 5:
            raise ValueError("Panel informal requiere exactamente 5 jueces")

        ordered = sorted(float(score) for score in judge_scores)
        lowest = ordered[0]
        highest = ordered[-1]
        kept = ordered[1:-1]
        kept_sum = float(sum(kept))
        final_score = kept_sum / 3.0
        max_judge_score = max(judge_scores)
        return InformalScoreComputation(
            final_score=final_score,
            kept_score_sum=kept_sum,
            highest_score=highest,
            lowest_score=lowest,
            max_judge_score=float(max_judge_score),
        )

    @staticmethod
    def _next_sequence_number(category_id: int) -> int:
        """Return next sequence number in category flow."""
        with rx.session() as session:
            latest = session.exec(
                select(KataInformalPerformance)
                .where(KataInformalPerformance.category_id == category_id)
                .order_by(KataInformalPerformance.sequence_number.desc())
            ).first()
            if latest is None:
                return 1
            return int(latest.sequence_number) + 1

    @staticmethod
    def save_performance(
        category_id: int,
        athlete_id: int,
        judge_scores: list[float],
        performance_round: int = 1,
    ) -> KataInformalPerformance:
        """Save one athlete performance and all judge rows."""
        computed = KataInformalService._compute_score(judge_scores)
        sequence_number = KataInformalService._next_sequence_number(category_id)

        with rx.session() as session:
            performance = KataInformalPerformance(
                category_id=category_id,
                athlete_id=athlete_id,
                sequence_number=sequence_number,
                performance_round=performance_round,
                status=KataInformalPerformanceStatus.SCORED.value,
                final_score=computed.final_score,
                kept_score_sum=computed.kept_score_sum,
                highest_score=computed.highest_score,
                lowest_score=computed.lowest_score,
                max_judge_score=computed.max_judge_score,
                is_extra_kata=performance_round > 1,
            )
            session.add(performance)
            session.commit()
            session.refresh(performance)

            for index, score in enumerate(judge_scores, start=1):
                judge_row = KataInformalJudgeScore(
                    performance_id=performance.id,
                    judge_id=index,
                    score=float(score),
                    slot_order=index,
                )
                session.add(judge_row)

            session.commit()
            session.refresh(performance)
            return performance

    @staticmethod
    def rank_category(category_id: int) -> list[dict[str, object]]:
        """Return standings sorted by informal ranking rules."""
        victory_points = KataInformalService._victory_points_by_athlete(category_id)
        with rx.session() as session:
            rows = session.exec(
                select(KataInformalPerformance).where(
                    KataInformalPerformance.category_id == category_id,
                )
            ).all()

        standings = [
            {
                "athlete_id": row.athlete_id,
                "performance_id": row.id,
                "final_score": float(row.final_score),
                "lowest_score": float(row.lowest_score),
                "highest_score": float(row.highest_score),
                "max_judge_score": float(row.max_judge_score),
                "victory_points": int(victory_points.get(int(row.athlete_id), 0)),
                "needs_extra_kata": False,
            }
            for row in rows
        ]

        standings.sort(
            key=lambda item: (
                int(item["victory_points"]),
                float(item["final_score"]),
            ),
            reverse=True,
        )

        grouped: dict[int, list[dict[str, object]]] = {}
        for row in standings:
            key = int(row["victory_points"])
            grouped.setdefault(key, []).append(row)

        ordered: list[dict[str, object]] = []
        for points in sorted(grouped.keys(), reverse=True):
            resolved_group = KataInformalService._resolve_same_points_group(
                category_id,
                grouped[points],
            )
            ordered.extend(resolved_group)

        return ordered

    @staticmethod
    def finalize_category(category_id: int) -> TournamentCategory:
        """Finalize informal category and set podium from ranking table."""
        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            if category is None:
                raise ValueError("Categoría no encontrada")

            roster = session.exec(
                select(Athlete.id).where(Athlete.kata_category_id == category_id)
            ).all()
            roster_ids = {
                int(row[0]) if isinstance(row, tuple) else int(row) for row in roster
            }

            performances = session.exec(
                select(KataInformalPerformance).where(
                    KataInformalPerformance.category_id == category_id,
                )
            ).all()
            scored_ids = {int(row.athlete_id) for row in performances}

            missing = roster_ids - scored_ids
            if missing:
                raise ValueError("Hay atletas del roster sin puntuar")

        standings = KataInformalService.rank_category(category_id)
        top = standings[:3]
        if len(top) < 3:
            raise ValueError("Se requieren al menos 3 atletas para podio")

        with rx.session() as session:
            category = session.get(TournamentCategory, category_id)
            category.first_place_id = int(top[0]["athlete_id"])
            category.second_place_id = int(top[1]["athlete_id"])
            category.third_place_ids = json.dumps([int(top[2]["athlete_id"])])
            category.status = CategoryStatus.COMPLETED.value
            session.add(category)
            session.commit()
            session.refresh(category)
            return category
