"""Bracket generation service for tournament categories."""

from __future__ import annotations

import random
from collections.abc import Sequence
from math import log2

import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete, AthleteGender
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import (
    BracketSide,
    CategoryGender,
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    TournamentCategory,
)
from kakumi_app.services.exceptions import ValidationError
from kakumi_app.utils import BELT_RANKS, BELT_RANK_ORDER


BRACKET_ALREADY_EXISTS_MESSAGE = (
    "Bracket already generated for this category. Cannot regenerate."
)


def _next_power_of_two(value: int) -> int:
    power = 1
    while power < value:
        power *= 2
    return power


def _shuffle_participants(participants: list[int]) -> list[int]:
    seeded = participants[:]
    random.shuffle(seeded)
    return seeded


def _build_elimination(
    participants: Sequence[int],
    tournament_id: int,
    category_id: int,
    *,
    is_team: bool,
) -> list[Match]:
    bracket_size = _next_power_of_two(len(participants))
    rounds = int(log2(bracket_size))
    seeded_slots: list[int | None] = list(participants) + [None] * (
        bracket_size - len(participants)
    )
    matches: list[Match] = []

    for index in range(bracket_size // 2):
        first = seeded_slots[index]
        second = seeded_slots[bracket_size - 1 - index]
        match = Match(
            tournament_id=tournament_id,
            category_id=category_id,
            round=1,
            match_number=index + 1,
            position=index + 1,
            match_type=MatchType.ELIMINATION.value,
            bracket_side=BracketSide.WINNERS.value,
        )

        if is_team:
            match.aka_team_id = first
            match.ao_team_id = second
        else:
            match.aka_id = first
            match.ao_id = second

        if first is not None and second is None:
            match.status = MatchStatus.COMPLETED.value
            if not is_team:
                match.winner_id = first

        matches.append(match)

    for round_number in range(2, rounds + 1):
        match_total = bracket_size // (2**round_number)
        for position in range(1, match_total + 1):
            matches.append(
                Match(
                    tournament_id=tournament_id,
                    category_id=category_id,
                    round=round_number,
                    match_number=position,
                    position=position,
                    match_type=(
                        MatchType.FINAL.value
                        if round_number == rounds
                        else MatchType.ELIMINATION.value
                    ),
                    bracket_side=BracketSide.WINNERS.value,
                )
            )

    return matches


def _build_round_robin(
    participants: Sequence[int],
    tournament_id: int,
    category_id: int,
    *,
    is_team: bool,
) -> list[Match]:
    rotation: list[int | None] = list(participants)
    if len(rotation) % 2 == 1:
        rotation.append(None)

    matches: list[Match] = []
    round_count = len(rotation) - 1
    half = len(rotation) // 2

    for round_number in range(1, round_count + 1):
        round_pairs = []
        for index in range(half):
            first = rotation[index]
            second = rotation[-(index + 1)]
            if first is None or second is None:
                continue
            round_pairs.append((first, second))

        for position, (first, second) in enumerate(round_pairs, start=1):
            match = Match(
                tournament_id=tournament_id,
                category_id=category_id,
                round=round_number,
                match_number=position,
                position=position,
                match_type=MatchType.ROUND_ROBIN.value,
            )
            if is_team:
                match.aka_team_id = first
                match.ao_team_id = second
            else:
                match.aka_id = first
                match.ao_id = second
            matches.append(match)

        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

    return matches


def _check_existing_matches(
    tournament_id: int,
    category_id: int,
    session: Session,
) -> bool:
    return (
        session.exec(
            select(Match).where(
                Match.tournament_id == tournament_id,
                Match.category_id == category_id,
            )
        ).first()
        is not None
    )


def _load_category(
    tournament_id: int,
    category_id: int,
    session: Session,
) -> TournamentCategory:
    category = session.get(TournamentCategory, category_id)
    if category is None or category.tournament_id != tournament_id:
        raise ValidationError(
            code="CATEGORY_NOT_FOUND",
            message="Tournament category not found for bracket generation.",
        )
    return category


# ponytail: simple boolean check, no abstraction needed
def _is_team_modality(modality: str) -> bool:
    return modality in {Modality.KATA_TEAM.value, Modality.KUMITE_TEAM.value}


def _matched_athlete_ids(
    category: TournamentCategory,
    session: Session,
) -> list[int]:
    """Return athlete IDs whose age/gender/belt match category criteria."""
    query = select(Athlete).where(
        Athlete.age.between(category.min_age, category.max_age)
    )
    if category.gender == CategoryGender.MALE.value:
        query = query.where(Athlete.gender == AthleteGender.MALE.value)
    elif category.gender == CategoryGender.FEMALE.value:
        query = query.where(Athlete.gender == AthleteGender.FEMALE.value)
    # MIXED = no gender filter

    athletes = session.exec(query).all()

    if category.min_belt_rank or category.max_belt_rank:
        min_idx = BELT_RANK_ORDER.get(category.min_belt_rank, 0)
        max_idx = BELT_RANK_ORDER.get(category.max_belt_rank, len(BELT_RANKS) - 1)
        athletes = [
            a
            for a in athletes
            if a.belt_rank
            and min_idx <= BELT_RANK_ORDER.get(a.belt_rank, -1) <= max_idx
        ]

    return [a.id for a in athletes]


def _participant_ids(
    session: Session,
    category: TournamentCategory,
) -> tuple[list[int], bool]:
    if category.modality in {
        Modality.KATA_INDIVIDUAL.value,
        Modality.KUMITE_INDIVIDUAL.value,
    }:
        return _matched_athlete_ids(category, session), False

    teams = session.exec(select(Team.id).where(Team.category_id == category.id)).all()
    return teams, True


def _build_matches(
    tournament_id: int,
    category_id: int,
    category: TournamentCategory,
    participants: list[int],
    *,
    is_team: bool,
) -> list[Match]:
    seeded = _shuffle_participants(participants)

    if category.competition_system == CompetitionSystem.ELIMINATION.value:
        return _build_elimination(
            seeded,
            tournament_id,
            category_id,
            is_team=is_team,
        )

    if category.competition_system == CompetitionSystem.ROUND_ROBIN.value:
        return _build_round_robin(
            seeded,
            tournament_id,
            category_id,
            is_team=is_team,
        )

    raise ValidationError(
        code="UNSUPPORTED_SYSTEM",
        message="Competition system is not supported for bracket generation.",
    )


def _generate_with_session(
    tournament_id: int,
    category_id: int,
    session: Session,
) -> dict[str, int | str]:
    if _check_existing_matches(tournament_id, category_id, session):
        raise ValidationError(
            code="BRACKET_ALREADY_EXISTS",
            message=BRACKET_ALREADY_EXISTS_MESSAGE,
        )

    category = _load_category(tournament_id, category_id, session)
    participants, is_team = _participant_ids(session, category)

    if len(participants) < 2:
        raise ValidationError(
            code="INSUFFICIENT_PARTICIPANTS",
            message="At least two participants are required to generate a bracket.",
        )

    matches = _build_matches(
        tournament_id, category_id, category, participants, is_team=is_team
    )
    session.add_all(matches)
    session.commit()

    return {
        "tournament_id": tournament_id,
        "category_id": category_id,
        "match_count": len(matches),
        "status": "generated",
    }


def generate_bracket(
    tournament_id: int,
    category_id: int,
    *,
    session: Session | None = None,
) -> dict[str, int | str]:
    """Generate and persist bracket matches as the source-of-truth bracket."""
    if session is not None:
        return _generate_with_session(tournament_id, category_id, session)

    with rx.session() as session:
        return _generate_with_session(tournament_id, category_id, session)


def propagate_winner(
    session: Session,
    completed_match: Match,
) -> None:
    """Propagate winner from a completed elimination match to the next round.

    Uses positional math: a match at round R, position P maps to the next match
    at round R+1, position ceil(P/2). Odd-position winners go to aka_id,
    even-position winners go to ao_id in the next match.

    Idempotent — does nothing if:
    - completed_match has no winner_id
    - match_type is not ELIMINATION
    - the next match slot is already filled

    Args:
        session: Active SQLModel session.
        completed_match: Completed match whose winner to propagate.
    """
    if completed_match.winner_id is None:
        return

    if completed_match.match_type != MatchType.ELIMINATION.value:
        return

    next_round = completed_match.round + 1
    next_position = (completed_match.position + 1) // 2

    next_match: Match | None = session.exec(
        select(Match).where(
            Match.tournament_id == completed_match.tournament_id,
            Match.category_id == completed_match.category_id,
            Match.round == next_round,
            Match.position == next_position,
        )
    ).first()

    if next_match is None:
        return

    is_odd = (completed_match.position % 2) == 1

    if is_odd:
        if next_match.aka_id is not None:
            return
        next_match.aka_id = completed_match.winner_id
    else:
        if next_match.ao_id is not None:
            return
        next_match.ao_id = completed_match.winner_id

    session.add(next_match)
