"""
Tie Breaking Service
Business logic for tie-breaking rules according to WKF 2026.
"""

import statistics
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.match_model import Match
from kakumi_app.models.match_score_model import MatchScore
from kakumi_app.models.penalty_model import Penalty
from kakumi_app.services.penalty_service import PenaltyService
from kakumi_app.services.scoring_service import ScoringService


class TieBreakingService:
    """Service for tie-breaking decisions."""

    @staticmethod
    def resolve_kumite_tie(match_id: int) -> Tuple[Optional[int], str]:
        """
        Resolve tie in Kumite match according to WKF 2026 tie-breaking rules.
        Returns (winner_id, method).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return None, "Match not found."
            if match.aka_score != match.ao_score:
                return None, "Scores are not tied."

            # 1. Check Golden Point (if match has been extended)
            # For simplicity, we assume Golden Point is a separate match extension.
            # We'll implement a simplified version: check penalties.

            # 2. Fewer penalties (Hansoku Chui)
            aka_counts = PenaltyService.get_penalty_counts(match_id, "AKA")
            ao_counts = PenaltyService.get_penalty_counts(match_id, "AO")
            aka_hc = aka_counts.get("HANSOKU_CHUI", 0) + aka_counts.get("HANSOKU", 0)
            ao_hc = ao_counts.get("HANSOKU_CHUI", 0) + ao_counts.get("HANSOKU", 0)

            if aka_hc < ao_hc:
                return match.aka_id, "Fewer penalties (Hansoku Chui)"
            elif ao_hc < aka_hc:
                return match.ao_id, "Fewer penalties (Hansoku Chui)"

            # 3. Senshu (first advantage) - first to score
            aka_first_score_time = TieBreakingService._get_first_score_time(
                match_id, "AKA"
            )
            ao_first_score_time = TieBreakingService._get_first_score_time(
                match_id, "AO"
            )
            if aka_first_score_time is not None and ao_first_score_time is None:
                return match.aka_id, "Senshu (first to score)"
            elif ao_first_score_time is not None and aka_first_score_time is None:
                return match.ao_id, "Senshu (first to score)"
            elif aka_first_score_time is not None and ao_first_score_time is not None:
                if aka_first_score_time < ao_first_score_time:
                    return match.aka_id, "Senshu (first to score)"
                elif ao_first_score_time < aka_first_score_time:
                    return match.ao_id, "Senshu (first to score)"

            # 4. Referee decision (random for now)
            # In real system, referee would decide.
            # We'll return None and let UI handle.
            return None, "Referee decision required"

    @staticmethod
    def resolve_kata_tie(match_id: int) -> Tuple[Optional[int], str]:
        """
        Resolve tie in Kata match according to WKF 2026 tie-breaking rules.
        Returns (winner_id, method).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return None, "Match not found."
            if match.aka_score != match.ao_score:
                return None, "Scores are not tied."

            # Get scores for both participants
            stmt = select(MatchScore).where(
                MatchScore.match_id == match_id,
                MatchScore.is_valid == True,
                MatchScore.score_type == "KATA_NUMERIC",
            )
            scores = session.exec(stmt).all()
            aka_scores = []
            ao_scores = []
            for score in scores:
                if score.participant == "AKA":
                    aka_scores.append(score.score_value)
                elif score.participant == "AO":
                    ao_scores.append(score.score_value)

            # 1. Mayor puntuación media (already tied, so average is same)
            # 2. Menor desviación estándar (consistency)
            aka_std = statistics.stdev(aka_scores) if len(aka_scores) > 1 else 0.0
            ao_std = statistics.stdev(ao_scores) if len(ao_scores) > 1 else 0.0

            if aka_std < ao_std:
                return match.aka_id, "Lower standard deviation"
            elif ao_std < aka_std:
                return match.ao_id, "Lower standard deviation"

            # 3. Mayor número de puntuaciones máximas (max score count)
            if aka_scores and ao_scores:
                max_score = max(max(aka_scores), max(ao_scores))
                aka_max_count = aka_scores.count(max_score)
                ao_max_count = ao_scores.count(max_score)
                if aka_max_count > ao_max_count:
                    return match.aka_id, "More maximum scores"
                elif ao_max_count > aka_max_count:
                    return match.ao_id, "More maximum scores"

            # 4. Referee decision
            return None, "Referee decision required"

    @staticmethod
    def _get_first_score_time(match_id: int, participant: str) -> Optional[int]:
        """Get the earliest technique_time for a participant in a match."""
        with rx.session() as session:
            stmt = (
                select(MatchScore)
                .where(
                    MatchScore.match_id == match_id,
                    MatchScore.participant == participant,
                    MatchScore.is_valid == True,
                    MatchScore.technique_time.isnot(None),
                )
                .order_by(MatchScore.technique_time.asc())
                .limit(1)
            )
            score = session.exec(stmt).first()
            if score:
                return score.technique_time
            return None

    @staticmethod
    def start_golden_point(match_id: int) -> Tuple[bool, str]:
        """
        Start Golden Point extension for a Kumite match.
        Returns (success, message).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found."
            if match.status != "IN_PROGRESS":
                return False, "Match must be in progress to start Golden Point."
            # In real system, we would extend match time.
            # For now, just log.
            return True, "Golden Point extension started."

    @staticmethod
    def apply_referee_decision(match_id: int, winner_id: int) -> Tuple[bool, str]:
        """
        Apply referee decision to break tie.
        Returns (success, message).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found."
            if match.aka_score != match.ao_score:
                return False, "Scores are not tied."
            if winner_id not in (match.aka_id, match.ao_id):
                return False, "Winner must be one of the participants."
            match.winner_id = winner_id
            match.status = "COMPLETED"
            match.end_time = rx.datetime.now()
            session.add(match)
            session.commit()
            return True, f"Referee decision applied: winner {winner_id}"
