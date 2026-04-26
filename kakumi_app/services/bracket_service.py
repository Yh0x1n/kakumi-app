"""
Bracket Service
Generates brackets for categories based on competition system.
"""

import math
import random
from typing import Dict, List, Optional, Tuple

import reflex as rx
from sqlmodel import select

from kakumi_app.models.match_model import Match
from kakumi_app.models.tournament_model import (
    KataCategory,
    KumiteCategory,
)


class BracketService:
    """Service for bracket generation and management."""

    @staticmethod
    def get_category(category_id: int) -> Optional[KataCategory | KumiteCategory]:
        """Retrieve category by ID (could be Kata or Kumite)."""
        with rx.session() as session:
            kata = session.get(KataCategory, category_id)
            if kata:
                return kata
            kumite = session.get(KumiteCategory, category_id)
            return kumite

    @staticmethod
    def get_participants(category_id: int) -> List[int]:
        """
        Retrieve participant IDs (athletes) for a category.
        For team categories, we would need team IDs.
        """
        with rx.session() as session:
            from kakumi_app.models.athlete_model import Athlete

            stmt = select(Athlete.id).where(
                (Athlete.kata_category_id == category_id)
                | (Athlete.kumite_category_id == category_id)
            )
            participants = session.exec(stmt).all()
            return list(participants)

    @staticmethod
    def seed_participants(participants: List[int]) -> List[int]:
        """Seed participants randomly (no ranking)."""
        seeded = participants.copy()
        random.shuffle(seeded)
        return seeded

    @staticmethod
    def calculate_bracket_size(num_participants: int) -> int:
        """Return the nearest power of two >= num_participants."""
        if num_participants <= 0:
            return 0
        return 2 ** math.ceil(math.log2(num_participants))

    @staticmethod
    def generate_bracket(category_id: int) -> Tuple[bool, str, List[Match]]:
        """
        Generate bracket for a category.
        Only supports elimination with power-of-two participants (no byes).
        Returns (success, message, matches).
        """
        category = BracketService.get_category(category_id)
        if not category:
            return False, "Category not found.", []

        participants = BracketService.get_participants(category_id)
        if len(participants) < 2:
            return False, "Need at least 2 participants.", []

        # Check if bracket already exists
        with rx.session() as session:
            existing = session.exec(
                select(Match).where(
                    (Match.kata_category_id == category_id)
                    | (Match.kumite_category_id == category_id)
                )
            ).first()
            if existing:
                return False, "Bracket already generated for this category.", []

        # Ensure power of two
        bracket_size = BracketService.calculate_bracket_size(len(participants))
        if bracket_size != len(participants):
            return (
                False,
                f"Bracket generation only supports power-of-two participants. Current: {len(participants)}",
                [],
            )

        seeded = BracketService.seed_participants(participants)
        matches = BracketService._create_elimination_bracket(category_id, seeded)

        # Save matches to database
        with rx.session() as session:
            for match in matches:
                session.add(match)
            session.commit()
            for match in matches:
                session.refresh(match)

        return True, f"Bracket generated with {len(matches)} matches.", matches

    @staticmethod
    def _create_elimination_bracket(
        category_id: int, participants: List[int]
    ) -> List[Match]:
        """Create matches for a single elimination bracket (power of two)."""
        matches = []
        num_rounds = int(math.log2(len(participants)))
        # Determine if kata or kumite
        kata_category_id = None
        kumite_category_id = None
        # We'll need to know which type. For simplicity, we'll assume kata if KataCategory exists.
        # But we don't have that info. We'll pass both as None and later fill based on category_id.
        # Actually match expects either kata_category_id or kumite_category_id.
        # We'll fetch category type from database. Let's do a quick query.
        with rx.session() as session:
            kata = session.get(KataCategory, category_id)
            if kata:
                kata_category_id = category_id
            else:
                kumite_category_id = category_id

        # First round matches
        for i in range(0, len(participants), 2):
            match_num = i // 2 + 1
            match = Match(
                kata_category_id=kata_category_id,
                kumite_category_id=kumite_category_id,
                round=1,
                match_number=match_num,
                position=match_num,
                match_type="ELIMINATION",
                aka_id=participants[i],
                ao_id=participants[i + 1],
                status="PENDING",
            )
            matches.append(match)

        # For simplicity, we won't create further rounds now.
        # They will be created as winners advance.
        return matches

    @staticmethod
    def advance_winner(match_id: int, winner_id: int) -> Tuple[bool, str]:
        """
        Advance winner to next round.
        Creates or updates the appropriate match in the next round.
        """
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return False, "Match not found."
            if match.status != "COMPLETED":
                return False, "Match not completed."

            category_id = match.kata_category_id or match.kumite_category_id
            if not category_id:
                return False, "Match has no category."

            current_round = match.round
            current_position = match.position
            participants = BracketService.get_participants(category_id)
            bracket_size = BracketService.calculate_bracket_size(len(participants))
            total_rounds = int(math.log2(bracket_size))

            if current_round >= total_rounds:
                return True, "Winner advanced to final (no next round)."

            next_round = current_round + 1
            next_position = (current_position + 1) // 2

            # Find existing match for next round
            stmt = select(Match).where(
                (Match.kata_category_id == category_id)
                | (Match.kumite_category_id == category_id),
                Match.round == next_round,
                Match.position == next_position,
            )
            next_match = session.exec(stmt).first()

            if not next_match:
                # Create new match
                if current_position % 2 == 1:
                    aka_id = winner_id
                    ao_id = None
                else:
                    aka_id = None
                    ao_id = winner_id

                # Determine category ids
                kata_category_id = match.kata_category_id
                kumite_category_id = match.kumite_category_id

                next_match = Match(
                    kata_category_id=kata_category_id,
                    kumite_category_id=kumite_category_id,
                    round=next_round,
                    match_number=0,
                    position=next_position,
                    match_type="ELIMINATION",
                    aka_id=aka_id if aka_id else 0,
                    ao_id=ao_id if ao_id else 0,
                    status="PENDING",
                )
                session.add(next_match)
                session.commit()
                session.refresh(next_match)
                return True, "Created next round match with winner."
            else:
                # Update slot
                if current_position % 2 == 1:
                    if next_match.aka_id is None:
                        next_match.aka_id = winner_id
                    else:
                        return False, "Next match already has aka participant."
                else:
                    if next_match.ao_id is None:
                        next_match.ao_id = winner_id
                    else:
                        return False, "Next match already has ao participant."
                session.add(next_match)
                session.commit()
                return True, "Winner advanced to next match."

    @staticmethod
    def get_bracket(category_id: int) -> List[Match]:
        """Retrieve all matches for a category."""
        with rx.session() as session:
            stmt = (
                select(Match)
                .where(
                    (Match.kata_category_id == category_id)
                    | (Match.kumite_category_id == category_id)
                )
                .order_by(Match.round, Match.match_number)
            )
            return session.exec(stmt).all()
