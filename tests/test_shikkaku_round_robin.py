"""Tests for SHIKKAKU round-robin and team disqualification rules."""

import datetime
import json

import reflex as rx
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team, TeamMember
from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchStatus,
    MatchType,
    Modality,
    Participant,
    PenaltyType,
    StandingsDeltaLog,
    Tournament,
    TournamentCategory,
    TournamentStatus,
)
from kakumi_app.services.kumite_scoring_service import apply_penalty


def _create_tournament(session: Session, name: str) -> Tournament:
    """Create and persist a tournament."""
    tournament = Tournament(
        name=name,
        venue="Dojo Central",
        start_date=datetime.date(2026, 7, 1),
        end_date=datetime.date(2026, 7, 2),
        status=TournamentStatus.PLANIFICADO.value,
        tatami_count=2,
        is_public=True,
    )
    session.add(tournament)
    session.commit()
    session.refresh(tournament)
    return tournament


def _create_category(
    session: Session,
    tournament_id: int,
    modality: str,
    competition_system: str,
) -> TournamentCategory:
    """Create and persist a category."""
    category = TournamentCategory(
        name=f"{modality}-{competition_system}",
        modality=modality,
        competition_system=competition_system,
        tournament_id=tournament_id,
    )
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


def _create_referee(session: Session) -> Referee:
    """Create referee used by penalty writes."""
    referee = Referee(
        name="Ref One",
        license_number="REF-001",
        license_level="INTERNATIONAL",
        role="REFEREE",
        is_available=True,
    )
    session.add(referee)
    session.commit()
    session.refresh(referee)
    return referee


def _create_athlete(session: Session, name: str, suffix: str) -> Athlete:
    """Create and persist one athlete."""
    athlete = Athlete(
        name=name,
        date_of_birth=datetime.date(2000, 1, 1),
        gender="MALE",
        email=f"{suffix}@test.dev",
        belt_rank="Dan 1",
        is_active=True,
    )
    session.add(athlete)
    session.commit()
    session.refresh(athlete)
    return athlete


def _create_match(
    session: Session,
    category_id: int,
    referee_id: int,
    match_number: int,
    status: str,
    aka_id: int | None = None,
    ao_id: int | None = None,
    aka_team_id: int | None = None,
    ao_team_id: int | None = None,
    aka_score: int = 0,
    ao_score: int = 0,
    winner_id: int | None = None,
) -> Match:
    """Create and persist one match."""
    match = Match(
        round=1,
        match_number=match_number,
        position=match_number,
        match_type=MatchType.ROUND_ROBIN.value,
        category_id=category_id,
        aka_id=aka_id,
        ao_id=ao_id,
        aka_team_id=aka_team_id,
        ao_team_id=ao_team_id,
        aka_score=aka_score,
        ao_score=ao_score,
        winner_id=winner_id,
        status=status,
        start_time=datetime.datetime(2026, 7, 1, 10, 0)
        + datetime.timedelta(minutes=match_number),
        referee_id=referee_id,
    )
    session.add(match)
    session.commit()
    session.refresh(match)
    return match


def _create_team_with_members(
    session: Session,
    category_id: int,
    name: str,
    prefix: str,
    member_count: int = 3,
) -> tuple[Team, list[Athlete]]:
    """Create one team and attach athletes through TeamMember rows."""
    team = Team(
        name=name,
        category_id=category_id,
        member_count=member_count,
        is_active=True,
    )
    session.add(team)
    session.commit()
    session.refresh(team)

    athletes: list[Athlete] = []
    for index in range(member_count):
        athlete = _create_athlete(
            session=session,
            name=f"{prefix} Athlete {index + 1}",
            suffix=f"{prefix.lower()}-{index + 1}",
        )
        member = TeamMember(
            team_id=team.id,
            athlete_id=athlete.id,
            position=index + 1,
            is_reserve=False,
        )
        session.add(member)
        athletes.append(athlete)

    session.commit()
    return team, athletes


def test_shikkaku_last_rr_bout_preserves_prior_scores(
    in_memory_session: Session,
) -> None:
    """Last RR bout keeps previous results while disqualifying athlete."""
    tournament = _create_tournament(in_memory_session, "RR Last Bout")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_INDIVIDUAL.value,
        CompetitionSystem.ROUND_ROBIN.value,
    )
    dq_athlete = _create_athlete(in_memory_session, "DQ Athlete", "dq-athlete")
    opp_1 = _create_athlete(in_memory_session, "Opponent One", "opp-1")
    opp_2 = _create_athlete(in_memory_session, "Opponent Two", "opp-2")
    opp_3 = _create_athlete(in_memory_session, "Opponent Three", "opp-3")

    previous_1 = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_1.id,
        aka_score=4,
        ao_score=1,
        winner_id=dq_athlete.id,
    )
    previous_2 = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=2,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_2.id,
        aka_score=3,
        ao_score=0,
        winner_id=dq_athlete.id,
    )
    current = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=3,
        status=MatchStatus.IN_PROGRESS.value,
        aka_id=dq_athlete.id,
        ao_id=opp_3.id,
    )

    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=current.id,
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    with rx.session() as session:
        refreshed_prev_1 = session.get(Match, previous_1.id)
        refreshed_prev_2 = session.get(Match, previous_2.id)
        refreshed_current = session.get(Match, current.id)
        refreshed_athlete = session.get(Athlete, dq_athlete.id)

        assert refreshed_prev_1.aka_score == 4
        assert refreshed_prev_1.ao_score == 1
        assert refreshed_prev_2.aka_score == 3
        assert refreshed_prev_2.ao_score == 0
        assert refreshed_athlete.is_disqualified is True
        assert refreshed_current.status == MatchStatus.COMPLETED.value
        assert refreshed_current.winner_id == opp_3.id


def test_shikkaku_not_last_rr_bout_nullifies_prior_scores(
    in_memory_session: Session,
) -> None:
    """Non-last RR SHIKKAKU nullifies previous results and cancels future bouts."""
    tournament = _create_tournament(in_memory_session, "RR Non Last Bout")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_INDIVIDUAL.value,
        CompetitionSystem.ROUND_ROBIN.value,
    )
    dq_athlete = _create_athlete(in_memory_session, "DQ Athlete Two", "dq-athlete-2")
    opp_1 = _create_athlete(in_memory_session, "Opponent A", "opp-a")
    opp_2 = _create_athlete(in_memory_session, "Opponent B", "opp-b")
    opp_3 = _create_athlete(in_memory_session, "Opponent C", "opp-c")
    opp_4 = _create_athlete(in_memory_session, "Opponent D", "opp-d")

    previous_1 = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_1.id,
        aka_score=4,
        ao_score=1,
        winner_id=dq_athlete.id,
    )
    previous_2 = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=2,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_2.id,
        aka_score=2,
        ao_score=0,
        winner_id=dq_athlete.id,
    )
    current = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=3,
        status=MatchStatus.IN_PROGRESS.value,
        aka_id=dq_athlete.id,
        ao_id=opp_3.id,
    )
    remaining = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=4,
        status=MatchStatus.PENDING.value,
        aka_id=dq_athlete.id,
        ao_id=opp_4.id,
    )

    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=current.id,
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    with rx.session() as session:
        refreshed_prev_1 = session.get(Match, previous_1.id)
        refreshed_prev_2 = session.get(Match, previous_2.id)
        refreshed_current = session.get(Match, current.id)
        refreshed_remaining = session.get(Match, remaining.id)
        refreshed_athlete = session.get(Athlete, dq_athlete.id)

        assert refreshed_prev_1.aka_score == 0
        assert refreshed_prev_1.ao_score == 0
        assert refreshed_prev_2.aka_score == 0
        assert refreshed_prev_2.ao_score == 0
        assert refreshed_athlete.is_disqualified is True
        assert refreshed_current.status == MatchStatus.COMPLETED.value
        assert refreshed_current.winner_id == opp_3.id
        assert refreshed_remaining.status == "CANCELLED"


def test_shikkaku_rr_writes_standings_delta_log(
    in_memory_session: Session,
) -> None:
    """Non-last RR SHIKKAKU persists a snapshot in ``StandingsDeltaLog``."""
    tournament = _create_tournament(in_memory_session, "RR Snapshot")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_INDIVIDUAL.value,
        CompetitionSystem.ROUND_ROBIN.value,
    )
    dq_athlete = _create_athlete(in_memory_session, "DQ Snapshot", "dq-snapshot")
    opp_1 = _create_athlete(in_memory_session, "Snapshot Opp 1", "snapshot-opp-1")
    opp_2 = _create_athlete(in_memory_session, "Snapshot Opp 2", "snapshot-opp-2")
    opp_3 = _create_athlete(in_memory_session, "Snapshot Opp 3", "snapshot-opp-3")

    _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.COMPLETED.value,
        aka_id=dq_athlete.id,
        ao_id=opp_1.id,
        aka_score=2,
        ao_score=1,
        winner_id=dq_athlete.id,
    )
    current = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=2,
        status=MatchStatus.IN_PROGRESS.value,
        aka_id=dq_athlete.id,
        ao_id=opp_2.id,
    )
    _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=3,
        status=MatchStatus.PENDING.value,
        aka_id=dq_athlete.id,
        ao_id=opp_3.id,
    )

    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=current.id,
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    with rx.session() as session:
        logs = session.exec(
            select(StandingsDeltaLog).where(
                StandingsDeltaLog.athlete_id == dq_athlete.id,
            )
        ).all()

        assert len(logs) == 1
        assert logs[0].change_key == f"shikkaku-match-{current.id}"
        snapshot = json.loads(logs[0].before_snapshot)
        assert isinstance(snapshot, list)
        assert len(snapshot) > 0


def test_shikkaku_team_match_disqualifies_whole_team(
    in_memory_session: Session,
) -> None:
    """Applying SHIKKAKU on team side disqualifies every athlete in that team."""
    tournament = _create_tournament(in_memory_session, "Team SHIKKAKU")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_TEAM.value,
        CompetitionSystem.ELIMINATION.value,
    )
    aka_team, aka_athletes = _create_team_with_members(
        in_memory_session,
        category.id,
        "AKA Team",
        "AKA",
    )
    _, ao_athletes = _create_team_with_members(
        in_memory_session,
        category.id,
        "AO Team",
        "AO",
    )
    match = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.IN_PROGRESS.value,
        aka_team_id=aka_team.id,
        ao_team_id=2,
    )

    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=match.id,
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    with rx.session() as session:
        refreshed = [session.get(Athlete, athlete.id) for athlete in aka_athletes]
        untouched = [session.get(Athlete, athlete.id) for athlete in ao_athletes]

        assert all(athlete.is_disqualified for athlete in refreshed)
        assert all(not athlete.is_disqualified for athlete in untouched)


def test_shikkaku_individual_match_only_disqualifies_one_athlete(
    in_memory_session: Session,
) -> None:
    """Individual SHIKKAKU affects only the penalized side athlete."""
    tournament = _create_tournament(in_memory_session, "Individual SHIKKAKU")
    referee = _create_referee(in_memory_session)
    category = _create_category(
        in_memory_session,
        tournament.id,
        Modality.KUMITE_INDIVIDUAL.value,
        CompetitionSystem.ELIMINATION.value,
    )
    aka = _create_athlete(in_memory_session, "AKA Fighter", "aka-fighter")
    ao = _create_athlete(in_memory_session, "AO Fighter", "ao-fighter")
    match = _create_match(
        in_memory_session,
        category.id,
        referee.id,
        match_number=1,
        status=MatchStatus.IN_PROGRESS.value,
        aka_id=aka.id,
        ao_id=ao.id,
    )

    with rx.session() as session:
        apply_penalty(
            session=session,
            match_id=match.id,
            participant=Participant.AKA.value,
            penalty_type=PenaltyType.SHIKKAKU,
        )

    with rx.session() as session:
        refreshed_aka = session.get(Athlete, aka.id)
        refreshed_ao = session.get(Athlete, ao.id)

        assert refreshed_aka.is_disqualified is True
        assert refreshed_ao.is_disqualified is False
