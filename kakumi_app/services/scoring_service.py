"""
Scoring Service
Business logic for scoring in Kumite and Kata according to WKF 2026 rules.
"""

import statistics
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.match_model import Match
from kakumi_app.models.match_score_model import MatchScore
from kakumi_app.models.tournament_model import KataCategory, KumiteCategory


class ScoringService:
    """Service for scoring calculations and validation."""

    # Kumite point values
    KUMITE_POINTS = {
        "IPPON": 3,
        "WAZA_ARI": 2,
        "YUKO": 1,
    }

    @staticmethod
    def get_category(match_id: int) -> Optional[KataCategory | KumiteCategory]:
        """Retrieve category for a match (Kata or Kumite)."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return None
            if match.kata_category_id:
                return session.get(KataCategory, match.kata_category_id)
            elif match.kumite_category_id:
                return session.get(KumiteCategory, match.kumite_category_id)
            return None

    @staticmethod
    def calculate_kumite_score(match_id: int) -> Tuple[int, int]:
        """
        Calculate total scores for AKA and AO in a Kumite match.
        Sums points from valid MatchScore entries (IPPON, WAZA_ARI, YUKO).
        Returns (aka_score, ao_score).
        """
        with rx.session() as session:
            stmt = select(MatchScore).where(
                MatchScore.match_id == match_id,
                MatchScore.is_valid == True,
                MatchScore.score_type.in_(["IPPON", "WAZA_ARI", "YUKO"]),
            )
            scores = session.exec(stmt).all()
            aka_score = 0
            ao_score = 0
            for score in scores:
                points = ScoringService.KUMITE_POINTS.get(score.score_type, 0)
                if score.participant == "AKA":
                    aka_score += points
                elif score.participant == "AO":
                    ao_score += points
            return aka_score, ao_score

    @staticmethod
    def calculate_kata_score(match_id: int) -> Tuple[float, float]:
        """
        Calculate final scores for AKA and AO in a Kata match.
        Uses 5-judge panel: remove highest and lowest, average remaining 3.
        If panel size is 3, average all.
        Returns (aka_score, ao_score) as floats.
        """
        with rx.session() as session:
            # Get all valid scores for this match (assuming score_type is "KATA_NUMERIC")
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

            aka_final = ScoringService._trim_and_average(aka_scores)
            ao_final = ScoringService._trim_and_average(ao_scores)
            return aka_final, ao_final

    @staticmethod
    def _trim_and_average(scores: List[float]) -> float:
        """Remove highest and lowest scores, return average of remaining."""
        if not scores:
            return 0.0
        if len(scores) <= 2:
            # Not enough to trim, just average all
            return sum(scores) / len(scores)
        # Remove max and min
        sorted_scores = sorted(scores)
        trimmed = sorted_scores[1:-1]  # remove first and last
        return sum(trimmed) / len(trimmed)

    @staticmethod
    def calculate_kata_flag_score(match_id: int) -> Tuple[int, int]:
        """
        Calculate flag scores for AKA and AO in a Kata match.
        Each judge raises a flag for one athlete.
        Returns (aka_flags, ao_flags).
        """
        with rx.session() as session:
            # Assuming score_type "FLAG" with score_value 1 for each flag
            stmt = select(MatchScore).where(
                MatchScore.match_id == match_id,
                MatchScore.is_valid == True,
                MatchScore.score_type == "FLAG",
            )
            scores = session.exec(stmt).all()
            aka_flags = 0
            ao_flags = 0
            for score in scores:
                if score.participant == "AKA":
                    aka_flags += 1
                elif score.participant == "AO":
                    ao_flags += 1
            return aka_flags, ao_flags

    @staticmethod
    def add_score(
        match_id: int,
        participant: str,
        score_type: str,
        score_value: float,
        judge_id: int,
        technique_time: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[MatchScore]]:
        """
        Add a score entry for a match.
        Returns (success, message, match_score).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found.", None
            if match.status not in ("READY", "IN_PROGRESS"):
                return False, "Match is not in a state to accept scores.", None
            if participant not in ("AKA", "AO"):
                return False, "Participant must be AKA or AO.", None

            # Validate score_type based on category modality
            category = ScoringService.get_category(match_id)
            if isinstance(category, KumiteCategory):
                if score_type not in ("IPPON", "WAZA_ARI", "YUKO"):
                    return False, f"Invalid score type for Kumite: {score_type}", None
            elif isinstance(category, KataCategory):
                if score_type not in ("KATA_NUMERIC", "FLAG"):
                    return False, f"Invalid score type for Kata: {score_type}", None
            else:
                return False, "Category not found.", None

            # Create score entry
            match_score = MatchScore(
                match_id=match_id,
                participant=participant,
                judge_id=judge_id,
                score_value=score_value,
                score_type=score_type,
                technique_time=technique_time,
                is_valid=False,  # Needs validation by referee
            )
            session.add(match_score)
            session.commit()
            session.refresh(match_score)
            return True, "Score added successfully.", match_score

    @staticmethod
    def validate_score(score_id: int) -> Tuple[bool, str]:
        """
        Validate a score entry (referee approval).
        """
        with rx.session() as session:
            score = session.get(MatchScore, score_id)
            if not score:
                return False, "Score not found."
            score.is_valid = True
            session.add(score)
            session.commit()
            return True, "Score validated."

    @staticmethod
    def update_match_total_scores(match_id: int) -> Tuple[bool, str]:
        """
        Recalculate and update match total scores based on validated scores.
        Returns (success, message).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found."

            category = ScoringService.get_category(match_id)
            if isinstance(category, KumiteCategory):
                aka_score, ao_score = ScoringService.calculate_kumite_score(match_id)
            elif isinstance(category, KataCategory):
                # Determine scoring type from category
                if category.scoring_type == "FLAG":
                    aka_flags, ao_flags = ScoringService.calculate_kata_flag_score(
                        match_id
                    )
                    # Convert flags to points? Actually flags are just counts, but we need a numeric score.
                    # For simplicity, treat flags as score_value (maybe sum of scores?)
                    # We'll just store flag counts as score for now.
                    aka_score = aka_flags
                    ao_score = ao_flags
                else:
                    aka_score, ao_score = ScoringService.calculate_kata_score(match_id)
            else:
                return False, "Category type unknown."

            match.aka_score = (
                int(aka_score) if isinstance(aka_score, (int, float)) else 0
            )
            match.ao_score = int(ao_score) if isinstance(ao_score, (int, float)) else 0
            session.add(match)
            session.commit()
            return (
                True,
                f"Match scores updated: AKA={match.aka_score}, AO={match.ao_score}",
            )

    @staticmethod
    def determine_winner(match_id: int) -> Optional[int]:
        """
        Determine winner based on current scores.
        Returns winner athlete id or None if tie.
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return None
            if match.aka_score > match.ao_score:
                return match.aka_id
            elif match.ao_score > match.aka_score:
                return match.ao_id
            else:
                return None  # Tie, needs tie-breaking
