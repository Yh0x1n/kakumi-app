"""
Penalty Service
Business logic for penalty accumulation and disqualification according to WKF 2026 rules.
"""

from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.match_model import Match
from kakumi_app.models.penalty_model import Penalty
from kakumi_app.models.referee_model import Referee


class PenaltyService:
    """Service for penalty management and disqualification checks."""

    @staticmethod
    def apply_penalty(
        match_id: int,
        participant: str,
        penalty_type: str,
        reason: str,
        given_by: int,
        rule_reference: Optional[str] = None,
        match_time_seconds: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[Penalty]]:
        """
        Apply a penalty to a participant in a match.
        Returns (success, message, penalty).
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found.", None
            if match.status not in ("READY", "IN_PROGRESS"):
                return False, "Match is not in a state to accept penalties.", None
            if participant not in ("AKA", "AO"):
                return False, "Participant must be AKA or AO.", None
            referee = session.get(Referee, given_by)
            if not referee:
                return False, "Referee not found.", None

            # Create penalty
            penalty = Penalty(
                match_id=match_id,
                participant=participant,
                penalty_type=penalty_type,
                reason=reason,
                rule_reference=rule_reference,
                is_accumulated=False,  # We'll compute accumulation based on count
                given_by=given_by,
                match_time_seconds=match_time_seconds,
            )
            session.add(penalty)
            session.commit()
            session.refresh(penalty)

            # Check if this penalty triggers disqualification
            disqualification = PenaltyService.check_disqualification(
                match_id, participant
            )
            if disqualification:
                # Update match status to DISQUALIFIED and set winner
                match.status = "DISQUALIFIED"
                # Determine opponent
                if participant == "AKA":
                    match.winner_id = match.ao_id
                else:
                    match.winner_id = match.aka_id
                match.end_time = rx.datetime.now()
                session.add(match)
                session.commit()
                return (
                    True,
                    f"Penalty applied and participant {participant} disqualified.",
                    penalty,
                )

            return True, "Penalty applied successfully.", penalty

    @staticmethod
    def get_penalty_counts(match_id: int, participant: str) -> Dict[str, int]:
        """
        Get count of each penalty type for a participant in a match.
        Returns dictionary with keys: CHUI, KEIKOKU, HANSOKU_CHUI, HANSOKU, SHIKKAKU.
        """
        with rx.session() as session:
            stmt = select(Penalty).where(
                Penalty.match_id == match_id,
                Penalty.participant == participant,
            )
            penalties = session.exec(stmt).all()
            counts = {
                "CHUI": 0,
                "KEIKOKU": 0,
                "HANSOKU_CHUI": 0,
                "HANSOKU": 0,
                "SHIKKAKU": 0,
            }
            for p in penalties:
                if p.penalty_type in counts:
                    counts[p.penalty_type] += 1
            return counts

    @staticmethod
    def check_disqualification(match_id: int, participant: str) -> bool:
        """
        Check if a participant should be disqualified based on penalty accumulation.
        According to WKF 2026 Art. 10:
        - 4 CHUI -> HANSOKU CHUI (warning, no points)
        - 5 CHUI -> HANSOKU (disqualification)
        - HANSOKU or SHIKKAKU penalty directly triggers disqualification.
        """
        with rx.session() as session:
            # Get latest penalty for this participant
            stmt = (
                select(Penalty)
                .where(
                    Penalty.match_id == match_id,
                    Penalty.participant == participant,
                )
                .order_by(Penalty.created_at.desc())
                .limit(1)
            )
            latest_penalty = session.exec(stmt).first()
            if not latest_penalty:
                return False

            # Direct disqualification penalties
            if latest_penalty.penalty_type in ("HANSOKU", "SHIKKAKU"):
                return True

            # Accumulation logic: count CHUI penalties
            counts = PenaltyService.get_penalty_counts(match_id, participant)
            chui_count = counts.get("CHUI", 0)

            # 4 CHUI -> HANSOKU CHUI (warning) - not disqualification yet
            # 5 CHUI -> HANSOKU (disqualification)
            if chui_count >= 5:
                return True

            return False

    @staticmethod
    def get_penalty_summary(match_id: int) -> Dict[str, Dict[str, int]]:
        """
        Get penalty summary for both participants.
        Returns {"AKA": {...}, "AO": {...}}.
        """
        summary = {}
        for participant in ("AKA", "AO"):
            summary[participant] = PenaltyService.get_penalty_counts(
                match_id, participant
            )
        return summary

    @staticmethod
    def should_award_points_for_penalty(penalty_type: str) -> bool:
        """
        Determine if penalty awards points to opponent.
        According to WKF 2026, HANSOKU CHUI does NOT award points.
        """
        # HANSOKU CHUI is a warning, no points awarded
        if penalty_type == "HANSOKU_CHUI":
            return False
        # Other penalties may award points? According to spec, only HANSOKU (disqualification) awards win to opponent.
        # Actually, only HANSOKU results in opponent win. CHUI and KEIKOKU are just warnings.
        # We'll return False for all except HANSOKU (which triggers disqualification).
        return False
