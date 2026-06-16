"""Scheduling overlap enforcement for Kumite match assignments.

Ensures no athlete is assigned to two overlapping tatamis simultaneously,
enforcing the configurable scheduling gap defined per tournament.
"""

import datetime

from sqlalchemy import or_
from sqlmodel import Session, select

from kakumi_app.models.tournament_model import Match, MatchStatus
from kakumi_app.services.exceptions import AppError


def _compute_overlap_window(
    start_time: datetime.datetime,
    duration_seconds: int,
    gap_seconds: int,
) -> tuple[datetime.datetime, datetime.datetime]:
    """Compute protected window as ``[start-gap, end+gap]``.

    Args:
        start_time: Match start datetime.
        duration_seconds: Match duration in seconds.
        gap_seconds: Required gap in seconds before/after a match.

    Returns:
        tuple[datetime.datetime, datetime.datetime]: Protected start/end window.
    """
    end_time = start_time + datetime.timedelta(seconds=duration_seconds)
    protected_start = start_time - datetime.timedelta(seconds=gap_seconds)
    protected_end = end_time + datetime.timedelta(seconds=gap_seconds)
    return protected_start, protected_end


def _get_athlete_active_matches(
    session: Session,
    athlete_id: int,
    exclude_match_id: int,
) -> list[Match]:
    """Load active matches for athlete excluding one match id.

    Args:
        session: Active database session.
        athlete_id: Athlete identifier.
        exclude_match_id: Match id to exclude from query.
    Returns:
        list[Match]: Candidate active matches.
    """
    return session.exec(
        select(Match).where(
            Match.id != exclude_match_id,
            Match.tatami_id.is_not(None),
            Match.start_time.is_not(None),
            Match.status.notin_([MatchStatus.COMPLETED.value, "CANCELLED"]),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()


def check_athlete_scheduling_overlap(
    session: Session,
    athlete_id: int,
    match_id: int,
    gap_seconds: int = 75,
) -> None:
    """Check that athlete has no overlapping match within ``gap_seconds``.

    Args:
        session: Active database session.
        athlete_id: ID of the athlete to check.
        match_id: ID of the match being scheduled/penalized.
        gap_seconds: Minimum required gap between matches.

    Raises:
        AthleteSchedulingConflictError: If athlete has a conflicting match.
    """
    target_match = session.get(Match, match_id)
    if target_match is None or target_match.start_time is None:
        return

    target_duration = target_match.category.match_duration_seconds
    protected_start, protected_end = _compute_overlap_window(
        start_time=target_match.start_time,
        duration_seconds=target_duration,
        gap_seconds=gap_seconds,
    )
    candidates = _get_athlete_active_matches(
        session=session,
        athlete_id=athlete_id,
        exclude_match_id=match_id,
    )

    for candidate in candidates:
        candidate_duration = candidate.category.match_duration_seconds
        _, candidate_window_end = _compute_overlap_window(
            start_time=candidate.start_time,
            duration_seconds=candidate_duration,
            gap_seconds=0,
        )
        if (
            candidate.start_time < protected_end
            and candidate_window_end > protected_start
        ):
            raise AppError(
                f"Athlete {athlete_id} has overlapping match {candidate.id} "
                f"on tatami {candidate.tatami_id} "
                f"({candidate.start_time} - {candidate_window_end}) within "
                f"{gap_seconds}s gap"
            )
