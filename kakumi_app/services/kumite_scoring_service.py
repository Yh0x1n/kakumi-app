"""Servicio de scoring Kumite con reglas WKF 2026."""

import datetime
import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

import reflex as rx
from sqlalchemy import or_
from sqlmodel import Session, select

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.team_model import TeamMember
from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchActionLog,
    MatchType,
    MatchScore,
    MatchStatus,
    Modality,
    Participant,
    Penalty,
    PenaltyType,
    ScoreType,
    StandingsDeltaLog,
)
from kakumi_app.services.exceptions import PenaltyEscalationError
from kakumi_app.services.exceptions import PenaltyRemovalNotAllowedError
from kakumi_app.services.exceptions import ShikkakuRevertError
from kakumi_app.services.bracket_service import propagate_winner
from kakumi_app.services.scheduling_service import check_athlete_scheduling_overlap

MATCH_STATUS_CANCELLED = "CANCELLED"


def _serialize_match_snapshot(match: Match) -> dict[str, int | str | bool | None]:
    """Serializa snapshot mínimo de match para rollback de última acción."""
    return {
        "aka_score": match.aka_score,
        "ao_score": match.ao_score,
        "aka_ippon_count": match.aka_ippon_count,
        "ao_ippon_count": match.ao_ippon_count,
        "aka_waza_ari_count": match.aka_waza_ari_count,
        "ao_waza_ari_count": match.ao_waza_ari_count,
        "aka_yuko_count": match.aka_yuko_count,
        "ao_yuko_count": match.ao_yuko_count,
        "aka_senshu": match.aka_senshu,
        "ao_senshu": match.ao_senshu,
        "winner_id": match.winner_id,
        "status": match.status,
        "end_time": match.end_time.isoformat() if match.end_time else None,
    }


def _load_action_snapshot(snapshot: str) -> dict:
    """Carga payload de snapshot para rollback."""
    decoded = json.loads(snapshot)
    if not isinstance(decoded, dict):
        raise ValueError("Invalid action snapshot payload")
    return decoded


def _restore_match_from_snapshot(match: Match, snapshot: dict) -> None:
    """Restaura valores de match desde snapshot serializado."""
    match.aka_score = int(snapshot.get("aka_score", 0))
    match.ao_score = int(snapshot.get("ao_score", 0))
    match.aka_ippon_count = int(snapshot.get("aka_ippon_count", 0))
    match.ao_ippon_count = int(snapshot.get("ao_ippon_count", 0))
    match.aka_waza_ari_count = int(snapshot.get("aka_waza_ari_count", 0))
    match.ao_waza_ari_count = int(snapshot.get("ao_waza_ari_count", 0))
    match.aka_yuko_count = int(snapshot.get("aka_yuko_count", 0))
    match.ao_yuko_count = int(snapshot.get("ao_yuko_count", 0))
    match.aka_senshu = bool(snapshot.get("aka_senshu", False))
    match.ao_senshu = bool(snapshot.get("ao_senshu", False))
    match.winner_id = snapshot.get("winner_id")
    match.status = str(snapshot.get("status", MatchStatus.PENDING.value))

    end_time = snapshot.get("end_time")
    if end_time:
        match.end_time = datetime.datetime.fromisoformat(str(end_time))
    else:
        match.end_time = None


def _build_action_snapshot(
    pre_match_snapshot: dict[str, int | str | bool | None],
    created_score_ids: list[int] | None = None,
    created_penalty_ids: list[int] | None = None,
) -> str:
    """Arma snapshot de action log usando estado previo ya capturado."""
    payload = {
        "match": pre_match_snapshot,
        "created_score_ids": created_score_ids or [],
        "created_penalty_ids": created_penalty_ids or [],
    }
    return json.dumps(payload)


def _with_retry(
    fn: Callable[[], Penalty],
    retries: int = 3,
    base_delay: float = 0.1,
) -> Penalty:
    """Execute a DB operation with exponential backoff.

    Args:
        fn: Operation callback to execute.
        retries: Maximum total attempts.
        base_delay: Base delay in seconds for exponential backoff.

    Returns:
        Penalty: The penalty produced by the callback.

    Raises:
        Exception: Re-raises final exception after exhausting retries.
    """
    for attempt in range(retries):
        try:
            return fn()
        except PenaltyEscalationError:
            raise
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(base_delay * (2**attempt))

    raise PenaltyEscalationError("Unable to apply penalty after retries")


def _count_penalties(session: Session, match_id: int, participant: str) -> int:
    """Count existing penalties for one side in one match.

    Args:
        session: Active SQLModel session.
        match_id: Target match identifier.
        participant: Side value (`AKA` or `AO`).

    Returns:
        int: Number of penalties already recorded for the side.
    """
    return len(
        session.exec(
            select(Penalty).where(
                Penalty.match_id == match_id,
                Penalty.participant == participant,
            )
        ).all()
    )


def _escalate_penalty_type(count: int) -> str:
    """Resolve automatic escalation level by existing penalty count.

    Args:
        count: Existing penalties count for one side.

    Returns:
        str: Escalated penalty level.
    """
    escalation_chain: list[str] = [
        "C1",
        "C2",
        "C3",
        PenaltyType.HANSOKU_CHUI.value,
        PenaltyType.HANSOKU.value,
    ]
    if count >= len(escalation_chain):
        return PenaltyType.HANSOKU.value
    return escalation_chain[count]


def _end_match_hansoku(session: Session, match: Match, winner_side: str) -> None:
    """Mark match as completed by HANSOKU, setting winner side.

    Args:
        session: Active SQLModel session.
        match: Match entity to update.
        winner_side: Winner side string (`AKA` or `AO`).
    """
    match.status = MatchStatus.COMPLETED.value
    match.end_time = datetime.datetime.utcnow()
    match.winner_id = (
        match.aka_id if winner_side == Participant.AKA.value else match.ao_id
    )
    session.add(match)


def _assert_match_in_progress(match: Match) -> None:
    """Ensure match is in progress before mutable penalty operations.

    WKF operator correction rule allows penalty corrections only while the
    match is active.

    Args:
        match: Match to validate.

    Raises:
        PenaltyRemovalNotAllowedError: If match is not ``IN_PROGRESS``.
    """
    if match.status != MatchStatus.IN_PROGRESS.value:
        raise PenaltyRemovalNotAllowedError(
            "Penalty removal only allowed when match is IN_PROGRESS"
        )


def _resolve_athlete_id_for_side(match: Match, participant_side: str) -> int:
    """Resolve athlete id from participant side in individual matches.

    Args:
        match: Match containing AKA/AO athlete references.
        participant_side: Penalized side (`AKA` or `AO`).

    Returns:
        int: Athlete id for the penalized side.

    Raises:
        PenaltyEscalationError: If side is invalid or athlete id is missing.
    """
    if participant_side == Participant.AKA.value:
        athlete_id = match.aka_id
    elif participant_side == Participant.AO.value:
        athlete_id = match.ao_id
    else:
        raise PenaltyEscalationError(f"Invalid participant side {participant_side}")

    if athlete_id is None:
        raise PenaltyEscalationError(
            f"Match {match.id} does not have athlete for side {participant_side}"
        )
    return athlete_id


def _complete_forfeit_match(match: Match, penalized_side: str) -> None:
    """Complete current match by forfeit according to WKF SHIKKAKU flow.

    WKF Art. 10.7.2 requires opponent victory after SHIKKAKU.

    Args:
        match: Match to update.
        penalized_side: Penalized side (`AKA` or `AO`).
    """
    winner_side = (
        Participant.AO.value
        if penalized_side == Participant.AKA.value
        else Participant.AKA.value
    )
    match.status = MatchStatus.COMPLETED.value
    match.end_time = datetime.datetime.utcnow()
    match.winner_id = (
        match.aka_id if winner_side == Participant.AKA.value else match.ao_id
    )


def _is_last_rr_match(session: Session, athlete_id: int, current_match_id: int) -> bool:
    """Return True when current match is athlete's last RR bout.

    WKF Art. 3.7.3 requires preserving prior scores only in the last bout.

    Args:
        session: Active SQLModel session.
        athlete_id: Penalized athlete id.
        current_match_id: Current match identifier.

    Returns:
        bool: True if there are no remaining RR matches for athlete.
    """
    current_match = session.get(Match, current_match_id)
    if current_match is None:
        raise PenaltyEscalationError(f"Match {current_match_id} not found")

    remaining = session.exec(
        select(Match).where(
            Match.id != current_match_id,
            Match.category_id == current_match.category_id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status.in_(
                [
                    MatchStatus.PENDING.value,
                    MatchStatus.READY.value,
                    MatchStatus.IN_PROGRESS.value,
                ]
            ),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()
    return len(remaining) == 0


def _nullify_rr_previous_scores(
    session: Session,
    athlete_id: int,
    current_match_id: int,
) -> list[dict]:
    """Nullify prior RR bouts scores and return pre-change snapshot.

    WKF Art. 3.7.3: for non-last RR SHIKKAKU, completed/current bout scores are
    nullified and prior victory points forfeited.

    Args:
        session: Active SQLModel session.
        athlete_id: Penalized athlete id.
        current_match_id: Current match identifier.

    Returns:
        list[dict]: Score snapshot BEFORE nullification.
    """
    current_match = session.get(Match, current_match_id)
    if current_match is None:
        raise PenaltyEscalationError(f"Match {current_match_id} not found")

    previous_matches = session.exec(
        select(Match).where(
            Match.id != current_match_id,
            Match.category_id == current_match.category_id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status == MatchStatus.COMPLETED.value,
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()

    snapshot: list[dict] = []
    for match in previous_matches:
        snapshot.append(
            {
                "match_id": match.id,
                "aka_score": match.aka_score,
                "ao_score": match.ao_score,
                "winner_id": match.winner_id,
                "status": match.status,
            }
        )
        match.aka_score = 0
        match.ao_score = 0
        match.winner_id = None
        session.add(match)

    return snapshot


def _cancel_remaining_rr_matches(
    session: Session,
    athlete_id: int,
    current_match_id: int,
) -> None:
    """Cancel all upcoming RR matches for a disqualified athlete.

    WKF Art. 3.7.3 implies athlete cannot complete remaining bouts after
    disqualification.

    Args:
        session: Active SQLModel session.
        athlete_id: Penalized athlete id.
        current_match_id: Current match identifier.
    """
    current_match = session.get(Match, current_match_id)
    if current_match is None:
        raise PenaltyEscalationError(f"Match {current_match_id} not found")

    remaining_matches = session.exec(
        select(Match).where(
            Match.id != current_match_id,
            Match.category_id == current_match.category_id,
            Match.match_type == MatchType.ROUND_ROBIN.value,
            Match.status.in_([MatchStatus.PENDING.value, MatchStatus.READY.value]),
            or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
        )
    ).all()

    for match in remaining_matches:
        match.status = MATCH_STATUS_CANCELLED
        if match.aka_id == athlete_id:
            match.winner_id = match.ao_id
        else:
            match.winner_id = match.aka_id
        session.add(match)


def _serialize_scores_snapshot(matches: list[Match]) -> str:
    """Serialize match scores and status to JSON string snapshot.

    Args:
        matches: Match rows to serialize before mutating SHIKKAKU operations.

    Returns:
        str: JSON payload with one entry per match.
    """
    snapshot_records: list[dict[str, int | str | None]] = []
    for match in matches:
        snapshot_records.append(
            {
                "match_id": match.id,
                "aka_score": match.aka_score,
                "ao_score": match.ao_score,
                "winner_id": match.winner_id,
                "status": match.status,
            }
        )
    return json.dumps(snapshot_records)


def _deserialize_scores_snapshot(snapshot: str) -> list[dict]:
    """Deserialize SHIKKAKU snapshot JSON payload.

    Args:
        snapshot: JSON payload stored in ``StandingsDeltaLog.before_snapshot``.

    Returns:
        list[dict]: Parsed snapshot rows.

    Raises:
        ShikkakuRevertError: If payload is not valid list JSON.
    """
    try:
        decoded = json.loads(snapshot)
    except json.JSONDecodeError as error:
        raise ShikkakuRevertError("Stored SHIKKAKU snapshot is invalid JSON") from error

    if not isinstance(decoded, list):
        raise ShikkakuRevertError("Stored SHIKKAKU snapshot must be a list")
    return decoded


def _apply_shikkaku_round_robin(
    session: Session,
    match_id: int,
    athlete_id: int,
    participant_side: str,
) -> None:
    """Apply SHIKKAKU round-robin branch by last-bout determination.

    WKF Art. 3.7.3:
    - Last RR bout: preserve prior results.
    - Non-last RR bout: nullify prior completed bouts and cancel remaining.

    Args:
        session: Active SQLModel session.
        match_id: Current match identifier.
        athlete_id: Penalized athlete id.
        participant_side: Penalized side (`AKA` or `AO`).
    """
    match = session.get(Match, match_id)
    if match is None:
        raise PenaltyEscalationError(f"Match {match_id} not found")

    is_last_match = _is_last_rr_match(session, athlete_id, match_id)
    if not is_last_match:
        previous_matches = session.exec(
            select(Match).where(
                Match.id != match_id,
                Match.category_id == match.category_id,
                Match.match_type == MatchType.ROUND_ROBIN.value,
                Match.status == MatchStatus.COMPLETED.value,
                or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
            )
        ).all()

        remaining_matches = session.exec(
            select(Match).where(
                Match.id != match_id,
                Match.category_id == match.category_id,
                Match.match_type == MatchType.ROUND_ROBIN.value,
                Match.status.in_([MatchStatus.PENDING.value, MatchStatus.READY.value]),
                or_(Match.aka_id == athlete_id, Match.ao_id == athlete_id),
            )
        ).all()

        before_snapshot = _serialize_scores_snapshot(
            previous_matches + remaining_matches
        )
        standings_log = StandingsDeltaLog(
            athlete_id=athlete_id,
            tournament_id=match.category.tournament_id,
            change_key=f"shikkaku-match-{match_id}",
            before_snapshot=before_snapshot,
        )
        session.add(standings_log)
        _nullify_rr_previous_scores(session, athlete_id, match_id)

    _cancel_remaining_rr_matches(session, athlete_id, match_id)
    _complete_forfeit_match(match, participant_side)

    athlete = session.get(Athlete, athlete_id)
    if athlete is None:
        raise PenaltyEscalationError(f"Athlete {athlete_id} not found")
    athlete.is_disqualified = True
    session.add(athlete)
    session.add(match)


def _apply_shikkaku(session: Session, match_id: int, participant: str) -> None:
    """Apply SHIKKAKU by modality: individual athlete or whole team.

    WKF Art. 10.7.2 enforces full disqualification from tournament and
    opponent forfeit win.

    Args:
        session: Active SQLModel session.
        match_id: Current match identifier.
        participant: Penalized side (`AKA` or `AO`).
    """
    match = session.get(Match, match_id)
    if match is None:
        raise PenaltyEscalationError(f"Match {match_id} not found")

    is_team_match = (
        match.category.modality == Modality.KUMITE_TEAM.value
        or match.aka_team_id is not None
        or match.ao_team_id is not None
    )

    if is_team_match:
        team_id = (
            match.aka_team_id
            if participant == Participant.AKA.value
            else match.ao_team_id
        )
        if team_id is None:
            raise PenaltyEscalationError(
                f"Match {match_id} does not have team for side {participant}"
            )

        team_members = session.exec(
            select(TeamMember).where(TeamMember.team_id == team_id)
        ).all()
        for member in team_members:
            athlete = session.get(Athlete, member.athlete_id)
            if athlete is not None:
                athlete.is_disqualified = True
                session.add(athlete)

        _complete_forfeit_match(match, participant)
        if participant == Participant.AKA.value:
            match.aka_score = 0
            match.ao_score = 8
        else:
            match.ao_score = 0
            match.aka_score = 8
        session.add(match)
        return

    athlete_id = _resolve_athlete_id_for_side(match, participant)
    if match.category.competition_system == CompetitionSystem.ROUND_ROBIN.value:
        _apply_shikkaku_round_robin(session, match_id, athlete_id, participant)
        return

    athlete = session.get(Athlete, athlete_id)
    if athlete is None:
        raise PenaltyEscalationError(f"Athlete {athlete_id} not found")
    athlete.is_disqualified = True
    _complete_forfeit_match(match, participant)
    session.add(athlete)
    session.add(match)


def apply_penalty(
    session: Session,
    match_id: int,
    participant: str,
    penalty_type: Optional[PenaltyType | str] = None,
) -> Penalty:
    """Apply penalty with side-based escalation and row locking.

    Args:
        session: Active SQLModel session.
        match_id: Target match identifier.
        participant: Penalized side (`AKA` or `AO`).
        penalty_type: Optional explicit level override.

    Returns:
        Penalty: The created penalty row.

    Raises:
        PenaltyEscalationError: If match is missing or not in progress.
    """

    return _with_retry(
        lambda: _apply_penalty_with_rollback(
            session=session,
            match_id=match_id,
            participant=participant,
            penalty_type=penalty_type,
        )
    )


def _resolve_athlete_id_for_penalty_side(
    match: Match, participant: str
) -> Optional[int]:
    """Resolve athlete id from penalty side for scheduling checks."""
    if participant == Participant.AKA.value:
        return match.aka_id
    if participant == Participant.AO.value:
        return match.ao_id
    return None


def _resolve_tournament_gap_seconds(match: Match) -> int:
    """Resolve configured scheduling gap from tournament with default fallback."""
    if match.category is not None and match.category.tournament is not None:
        return match.category.tournament.scheduling_gap_seconds
    return 75


def _resolve_penalty_type(
    session: Session,
    match_id: int,
    participant: str,
    penalty_type: Optional[PenaltyType | str],
) -> str:
    """Resolve final penalty type from explicit input or escalation chain."""
    if penalty_type is None:
        count = _count_penalties(session, match_id, participant)
        return _escalate_penalty_type(count)
    if isinstance(penalty_type, PenaltyType):
        return penalty_type.value
    return penalty_type


def _apply_terminal_penalty(
    session: Session,
    match: Match,
    match_id: int,
    participant: str,
    resolved_type: str,
) -> None:
    """Apply side effects for terminal penalties."""
    if resolved_type == PenaltyType.HANSOKU.value:
        winner_side = (
            Participant.AO.value
            if participant == Participant.AKA.value
            else Participant.AKA.value
        )
        _end_match_hansoku(session, match, winner_side)
        return
    if resolved_type == PenaltyType.SHIKKAKU.value:
        _apply_shikkaku(session, match_id, participant)


def _apply_penalty_operation(
    session: Session,
    match_id: int,
    participant: str,
    penalty_type: Optional[PenaltyType | str],
) -> Penalty:
    """Perform one penalty operation transaction body."""
    pre_match = session.get(Match, match_id)
    if pre_match is not None:
        athlete_id = _resolve_athlete_id_for_penalty_side(pre_match, participant)
        if athlete_id is not None:
            gap_seconds = _resolve_tournament_gap_seconds(pre_match)
            check_athlete_scheduling_overlap(
                session=session,
                athlete_id=athlete_id,
                match_id=match_id,
                gap_seconds=gap_seconds,
            )

    stmt = select(Match).where(Match.id == match_id).with_for_update()
    match = session.exec(stmt).first()
    if match is None:
        raise PenaltyEscalationError(f"Match {match_id} not found")

    try:
        _assert_match_in_progress(match)
    except PenaltyRemovalNotAllowedError as error:
        raise PenaltyEscalationError(
            f"Cannot apply penalty to match with status {match.status}"
        ) from error

    resolved_type = _resolve_penalty_type(session, match_id, participant, penalty_type)
    penalty = Penalty(
        match_id=match.id,
        given_by_id=match.referee_id or 1,
        participant=participant,
        penalty_type=resolved_type,
        reason="AUTO_APPLY",
        is_accumulated=penalty_type is None,
    )
    session.add(penalty)
    _apply_terminal_penalty(
        session=session,
        match=match,
        match_id=match_id,
        participant=participant,
        resolved_type=resolved_type,
    )

    session.commit()
    if match.winner_id is not None:
        propagate_winner(session, match)
        session.commit()
    session.refresh(penalty)
    return penalty


def _apply_penalty_with_rollback(
    session: Session,
    match_id: int,
    participant: str,
    penalty_type: Optional[PenaltyType | str],
) -> Penalty:
    """Apply penalty and rollback session on failures."""
    try:
        return _apply_penalty_operation(
            session=session,
            match_id=match_id,
            participant=participant,
            penalty_type=penalty_type,
        )
    except Exception:
        session.rollback()
        raise


def remove_last_penalty(
    session: Session,
    match_id: int,
    participant: str,
) -> Penalty:
    """Remove most recent penalty for one side in active match.

    WKF operator correction rule: correction is valid only during active match.

    Args:
        session: Active database session.
        match_id: ID of the match.
        participant: Side (AKA/AO) whose last penalty is removed.

    Returns:
        The deleted penalty object.

    Raises:
        PenaltyRemovalNotAllowedError: If match is not ``IN_PROGRESS``.
        ValueError: If side has no penalties.
    """
    match = session.get(Match, match_id)
    if match is None:
        raise PenaltyRemovalNotAllowedError(
            f"Penalty removal only allowed when match is IN_PROGRESS: {match_id}"
        )

    _assert_match_in_progress(match)

    penalty = session.exec(
        select(Penalty)
        .where(
            Penalty.match_id == match_id,
            Penalty.participant == participant,
        )
        .order_by(Penalty.id.desc())
    ).first()
    if penalty is None:
        raise ValueError("No penalties to remove")

    session.delete(penalty)
    session.commit()
    return penalty


def revert_shikkaku(
    session: Session,
    change_key: str,
) -> None:
    """Revert a SHIKKAKU standing change using the StandingsDeltaLog snapshot.

    Restores all match scores nullified by a prior SHIKKAKU application,
    un-cancels affected matches, and clears the athlete's disqualification flag.
    Admin-only operation (caller is responsible for permission checks).

    Args:
        session: Active database session.
        change_key: The change key written by _apply_shikkaku_round_robin(),
            e.g. "shikkaku-match-{match_id}".

    Raises:
        ShikkakuRevertError: If no delta log found for the given change_key.
    """
    delta_log = session.exec(
        select(StandingsDeltaLog).where(StandingsDeltaLog.change_key == change_key)
    ).first()
    if delta_log is None:
        raise ShikkakuRevertError(
            f"No SHIKKAKU delta log found for change_key={change_key}"
        )

    snapshot_records = _deserialize_scores_snapshot(delta_log.before_snapshot)

    for record in snapshot_records:
        match_id = record.get("match_id")
        if match_id is None:
            continue

        match = session.get(Match, match_id)
        if match is None:
            raise ShikkakuRevertError(
                f"Match {match_id} not found during SHIKKAKU revert"
            )

        match.aka_score = int(record.get("aka_score", 0))
        match.ao_score = int(record.get("ao_score", 0))
        match.winner_id = record.get("winner_id")
        status = record.get("status")
        if status is not None:
            match.status = str(status)
        session.add(match)

    athlete = session.get(Athlete, delta_log.athlete_id)
    if athlete is None:
        raise ShikkakuRevertError(
            f"Athlete {delta_log.athlete_id} not found during SHIKKAKU revert"
        )
    athlete.is_disqualified = False
    session.add(athlete)

    match_id_prefix = "shikkaku-match-"
    if change_key.startswith(match_id_prefix):
        match_id = int(change_key[len(match_id_prefix) :])
        shikkaku_penalties = session.exec(
            select(Penalty).where(
                Penalty.match_id == match_id,
                Penalty.penalty_type == PenaltyType.SHIKKAKU.value,
            )
        ).all()
        for penalty in shikkaku_penalties:
            session.delete(penalty)

    session.delete(delta_log)
    session.commit()


@dataclass
class MatchResult:
    """Resultado de aplicación de puntuación."""

    success: bool
    match_ended: bool
    winner: Optional[str]
    message: str
    end_reason: Optional[str] = None
    hantei_required: bool = False


@dataclass
class PenaltyResult:
    """Resultado de aplicación de penalidad."""

    success: bool
    penalty_type: Optional[str]
    match_ended: bool
    winner: Optional[str]
    message: str


@dataclass
class TiebreakerResult:
    """Resultado de resolución de desempate."""

    winner: Optional[str]
    reason: str
    is_draw: bool


@dataclass
class SenshuResult:
    """Resultado de operación manual de SENSHU."""

    success: bool
    message: str


class KumiteScoringService:
    """Servicio backend para scoring manual de Kumite."""

    POINT_VALUES: dict[str, int] = {
        ScoreType.YUKO.value: 1,
        ScoreType.WAZA_ARI.value: 2,
        ScoreType.IPPON.value: 3,
    }
    SUPERIORITY_LEAD: int = 8
    MAX_CHUI: int = 3

    @staticmethod
    def _set_match_completed_for_winner(match: Match, winner: str) -> None:
        """Set match terminal fields for resolved AKA/AO winner."""
        match.status = MatchStatus.COMPLETED.value
        match.end_time = datetime.datetime.utcnow()
        match.winner_id = (
            match.aka_id if winner == Participant.AKA.value else match.ao_id
        )

    @staticmethod
    def _resolve_time_over_decision(match: Match) -> tuple[Optional[str], str, bool]:
        """Resolve winner when time expires: points, then SENSHU, else HANTEI."""
        if match.aka_score != match.ao_score:
            winner = (
                Participant.AKA.value
                if match.aka_score > match.ao_score
                else Participant.AO.value
            )
            return winner, "TIME_OVER_POINTS", False

        if match.aka_senshu and not match.ao_senshu:
            return Participant.AKA.value, "TIME_OVER_SENSHU", False
        if match.ao_senshu and not match.aka_senshu:
            return Participant.AO.value, "TIME_OVER_SENSHU", False

        return None, "HANTEI_REQUIRED", True

    @staticmethod
    def apply_score(
        match_id: int,
        participant: Participant,
        score_type: ScoreType,
        applied_by_id: int,
    ) -> MatchResult:
        """Aplica puntaje manual al match en progreso."""
        participant_value = (
            participant.value if isinstance(participant, Participant) else participant
        )
        score_type_value = (
            score_type.value if isinstance(score_type, ScoreType) else score_type
        )

        if score_type_value not in KumiteScoringService.POINT_VALUES:
            return MatchResult(
                success=False,
                match_ended=False,
                winner=None,
                message=f"Tipo de puntaje inválido: {score_type_value}",
                end_reason=None,
                hantei_required=False,
            )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return MatchResult(False, False, None, "Match no está en progreso")

            pre_match_snapshot = _serialize_match_snapshot(match)

            points = KumiteScoringService.POINT_VALUES[score_type_value]
            if participant_value == Participant.AKA.value:
                match.aka_score += points
                KumiteScoringService._increment_score_counter(
                    match, "aka", score_type_value
                )
            elif participant_value == Participant.AO.value:
                match.ao_score += points
                KumiteScoringService._increment_score_counter(
                    match, "ao", score_type_value
                )
            else:
                return MatchResult(False, False, None, "Participante inválido")

            winner, end_reason = KumiteScoringService._check_match_termination(match)
            match_score = MatchScore(
                match_id=match.id,
                judge_id=match.referee_id or 1,
                participant=participant_value,
                score_value=float(points),
                score_type=score_type_value,
                applied_by_id=applied_by_id,
                is_valid=True,
                created_at=datetime.datetime.utcnow(),
            )
            session.add(match)
            session.add(match_score)
            session.flush()

            session.add(
                MatchActionLog(
                    match_id=match.id,
                    applied_by_id=applied_by_id,
                    action_kind="SCORE_APPLY",
                    participant=participant_value,
                    before_snapshot=_build_action_snapshot(
                        pre_match_snapshot=pre_match_snapshot,
                        created_score_ids=[match_score.id],
                    ),
                )
            )
            session.commit()

            if winner is not None:
                propagate_winner(session, match)
                session.commit()

            return MatchResult(
                success=True,
                match_ended=winner is not None,
                winner=winner,
                message="Puntaje aplicado",
                end_reason=end_reason,
                hantei_required=False,
            )

    @staticmethod
    def resolve_time_expired(match_id: int) -> MatchResult:
        """Resolve end-of-time winner contract for real match flow."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return MatchResult(False, False, None, "Match no está en progreso")

            winner, end_reason, hantei_required = (
                KumiteScoringService._resolve_time_over_decision(match)
            )
            if winner is not None:
                KumiteScoringService._set_match_completed_for_winner(match, winner)
            else:
                match.end_time = datetime.datetime.utcnow()

            session.add(match)
            session.commit()

            if winner is not None:
                propagate_winner(session, match)
                session.commit()

            return MatchResult(
                success=True,
                match_ended=True,
                winner=winner,
                message="Tiempo finalizado",
                end_reason=end_reason,
                hantei_required=hantei_required,
            )

    @staticmethod
    def apply_hantei_decision(
        match_id: int,
        winner_participant: Participant | str,
    ) -> MatchResult:
        """Apply operator HANTEI winner decision and complete match."""
        winner_value = (
            winner_participant.value
            if isinstance(winner_participant, Participant)
            else winner_participant
        )
        if winner_value not in (Participant.AKA.value, Participant.AO.value):
            return MatchResult(
                success=False,
                match_ended=False,
                winner=None,
                message="Participante inválido",
            )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return MatchResult(False, False, None, "Match no está en progreso")

            KumiteScoringService._set_match_completed_for_winner(match, winner_value)
            session.add(match)
            session.commit()

            propagate_winner(session, match)
            session.commit()

            return MatchResult(
                success=True,
                match_ended=True,
                winner=winner_value,
                message="HANTEI aplicado",
                end_reason="HANTEI_DECISION",
                hantei_required=False,
            )

    @staticmethod
    def apply_disqualification(
        match_id: int,
        penalized_participant: Participant | str,
        disqualification_type: str,
    ) -> MatchResult:
        """Apply manual disqualification (SHIKKAKU/KIKEN) and end match."""
        penalized_value = (
            penalized_participant.value
            if isinstance(penalized_participant, Participant)
            else penalized_participant
        )
        if penalized_value not in (Participant.AKA.value, Participant.AO.value):
            return MatchResult(
                success=False,
                match_ended=False,
                winner=None,
                message="Participante inválido",
            )

        sanction_type = str(disqualification_type or "").upper()
        if sanction_type not in {"SHIKKAKU", "KIKEN"}:
            return MatchResult(
                success=False,
                match_ended=False,
                winner=None,
                message="Tipo de descalificación inválido",
            )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return MatchResult(False, False, None, "Match no está en progreso")

            winner = KumiteScoringService._get_opponent(penalized_value)
            KumiteScoringService._set_match_completed_for_winner(match, winner)
            session.add(match)
            session.commit()

            propagate_winner(session, match)
            session.commit()

            return MatchResult(
                success=True,
                match_ended=True,
                winner=winner,
                message="Descalificación aplicada",
                end_reason=sanction_type,
                hantei_required=False,
            )

    @staticmethod
    def apply_penalty(
        match_id: int,
        participant: Participant,
        penalty_type: PenaltyType,
        reason: str,
        applied_by_id: int,
    ) -> PenaltyResult:
        """Aplica penalidad con escalación WKF 2026."""
        participant_value = (
            participant.value if isinstance(participant, Participant) else participant
        )
        penalty_type_value = (
            penalty_type.value
            if isinstance(penalty_type, PenaltyType)
            else penalty_type
        )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return PenaltyResult(False, None, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return PenaltyResult(
                    False,
                    None,
                    False,
                    None,
                    "Match no está en progreso",
                )

            pre_match_snapshot = _serialize_match_snapshot(match)

            existing_penalties = session.exec(
                select(Penalty).where(
                    Penalty.match_id == match.id,
                    Penalty.participant == participant_value,
                )
            ).all()
            chui_count = sum(
                1
                for penalty in existing_penalties
                if penalty.penalty_type == PenaltyType.CHUI.value
            )
            has_hansoku_chui = any(
                penalty.penalty_type == PenaltyType.HANSOKU_CHUI.value
                for penalty in existing_penalties
            )

            applied_level = penalty_type_value
            if penalty_type_value == PenaltyType.CHUI.value:
                if has_hansoku_chui:
                    applied_level = PenaltyType.HANSOKU.value
                else:
                    applied_level = KumiteScoringService._get_next_penalty_level(
                        chui_count
                    ).value
            elif (
                penalty_type_value == PenaltyType.HANSOKU_CHUI.value
                and has_hansoku_chui
            ):
                applied_level = PenaltyType.HANSOKU.value

            penalty = Penalty(
                match_id=match.id,
                given_by_id=match.referee_id or 1,
                participant=participant_value,
                penalty_type=applied_level,
                reason=reason,
                is_accumulated=applied_level != penalty_type_value,
            )
            session.add(penalty)

            created_score_ids: list[int] = []

            winner: Optional[str] = None
            if applied_level == PenaltyType.HANSOKU.value:
                winner = KumiteScoringService._get_opponent(participant_value)
                created_score_ids = KumiteScoringService._apply_hansoku_result(
                    match=match,
                    winner_participant=winner,
                    session=session,
                )
                winner_id = (
                    match.aka_id if winner == Participant.AKA.value else match.ao_id
                )
                match.status = MatchStatus.COMPLETED.value
                match.winner_id = winner_id
                match.end_time = datetime.datetime.utcnow()

            session.add(match)
            session.flush()

            session.add(
                MatchActionLog(
                    match_id=match.id,
                    applied_by_id=applied_by_id,
                    action_kind="PENALTY_APPLY",
                    participant=participant_value,
                    before_snapshot=_build_action_snapshot(
                        pre_match_snapshot=pre_match_snapshot,
                        created_score_ids=created_score_ids,
                        created_penalty_ids=[penalty.id],
                    ),
                )
            )
            session.commit()

            if winner is not None:
                propagate_winner(session, match)
                session.commit()

            return PenaltyResult(
                success=True,
                penalty_type=applied_level,
                match_ended=winner is not None,
                winner=winner,
                message="Penalidad aplicada",
            )

    @staticmethod
    def apply_manual_senshu(match_id: int, participant: Participant) -> SenshuResult:
        """Otorga manualmente SENSHU al participante indicado."""
        participant_value = (
            participant.value if isinstance(participant, Participant) else participant
        )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return SenshuResult(success=False, message="Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return SenshuResult(
                    success=False,
                    message="Match no está en progreso",
                )

            if participant_value == Participant.AKA.value:
                match.aka_senshu = True
                match.ao_senshu = False
            elif participant_value == Participant.AO.value:
                match.ao_senshu = True
                match.aka_senshu = False
            else:
                return SenshuResult(success=False, message="Participante inválido")

            session.add(match)
            session.commit()
            return SenshuResult(success=True, message="SENSHU otorgado")

    @staticmethod
    def revoke_senshu(match_id: int, participant: Participant) -> SenshuResult:
        """Revoca manualmente SENSHU del participante indicado."""
        participant_value = (
            participant.value if isinstance(participant, Participant) else participant
        )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return SenshuResult(success=False, message="Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return SenshuResult(
                    success=False,
                    message="Match no está en progreso",
                )

            if participant_value == Participant.AKA.value:
                match.aka_senshu = False
            elif participant_value == Participant.AO.value:
                match.ao_senshu = False
            else:
                return SenshuResult(success=False, message="Participante inválido")

            session.add(match)
            session.commit()
            return SenshuResult(success=True, message="SENSHU revocado")

    @staticmethod
    def undo_last_action(match_id: int) -> MatchResult:
        """Revierte última acción persistida del match."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")

            action_log = session.exec(
                select(MatchActionLog)
                .where(MatchActionLog.match_id == match_id)
                .order_by(MatchActionLog.id.desc())
            ).first()
            if action_log is None:
                return MatchResult(False, False, None, "No hay acciones para deshacer")

            try:
                payload = _load_action_snapshot(action_log.before_snapshot)
            except (ValueError, json.JSONDecodeError):
                return MatchResult(False, False, None, "Snapshot inválido para undo")

            _restore_match_from_snapshot(match, payload.get("match", {}))

            for score_id in payload.get("created_score_ids", []):
                score_row = session.get(MatchScore, int(score_id))
                if score_row is not None:
                    session.delete(score_row)

            for penalty_id in payload.get("created_penalty_ids", []):
                penalty_row = session.get(Penalty, int(penalty_id))
                if penalty_row is not None:
                    session.delete(penalty_row)

            session.delete(action_log)
            session.add(match)
            session.commit()
            return MatchResult(True, False, None, "Acción revertida")

    @staticmethod
    def _check_match_termination(match: Match) -> tuple[Optional[str], Optional[str]]:
        """Finaliza match por superioridad (diferencia >= 8)."""
        score_diff = abs(match.aka_score - match.ao_score)
        if score_diff < KumiteScoringService.SUPERIORITY_LEAD:
            return None, None

        winner = (
            Participant.AKA.value
            if match.aka_score > match.ao_score
            else Participant.AO.value
        )
        KumiteScoringService._set_match_completed_for_winner(match, winner)
        return winner, "SUPERIORITY"

    @staticmethod
    def _get_tiebreaker_winner(match: Match) -> TiebreakerResult:
        """Resuelve desempate: SENSHU > IPPON > WAZA_ARI > HANTEI/HIKIWAKE."""
        if match.aka_senshu and not match.ao_senshu:
            return TiebreakerResult(Participant.AKA.value, "SENSHU", False)
        if match.ao_senshu and not match.aka_senshu:
            return TiebreakerResult(Participant.AO.value, "SENSHU", False)

        if match.aka_ippon_count > match.ao_ippon_count:
            return TiebreakerResult(Participant.AKA.value, "MORE_IPPON", False)
        if match.ao_ippon_count > match.aka_ippon_count:
            return TiebreakerResult(Participant.AO.value, "MORE_IPPON", False)

        if match.aka_waza_ari_count > match.ao_waza_ari_count:
            return TiebreakerResult(Participant.AKA.value, "MORE_WAZA_ARI", False)
        if match.ao_waza_ari_count > match.aka_waza_ari_count:
            return TiebreakerResult(Participant.AO.value, "MORE_WAZA_ARI", False)

        return TiebreakerResult(None, "HANTEI_REQUIRED", True)

    @staticmethod
    def resolve_tiebreaker(match_id: int) -> TiebreakerResult:
        """API pública para resolver desempate por id de match."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return TiebreakerResult(None, "MATCH_NOT_FOUND", True)
            return KumiteScoringService._get_tiebreaker_winner(match)

    @staticmethod
    def _get_next_penalty_level(chui_count: int) -> PenaltyType:
        """Define siguiente escalón de penalidad para CHUI acumulado."""
        if chui_count < KumiteScoringService.MAX_CHUI:
            return PenaltyType.CHUI
        return PenaltyType.HANSOKU_CHUI

    @staticmethod
    def _increment_score_counter(match: Match, side: str, score_type: str) -> None:
        """Incrementa contador de tipo de puntaje por lado."""
        if side == "aka":
            if score_type == ScoreType.IPPON.value:
                match.aka_ippon_count += 1
            elif score_type == ScoreType.WAZA_ARI.value:
                match.aka_waza_ari_count += 1
            elif score_type == ScoreType.YUKO.value:
                match.aka_yuko_count += 1
        elif side == "ao":
            if score_type == ScoreType.IPPON.value:
                match.ao_ippon_count += 1
            elif score_type == ScoreType.WAZA_ARI.value:
                match.ao_waza_ari_count += 1
            elif score_type == ScoreType.YUKO.value:
                match.ao_yuko_count += 1

    @staticmethod
    def _get_opponent(participant: str) -> str:
        """Retorna lado oponente para AKA/AO."""
        if participant == Participant.AKA.value:
            return Participant.AO.value
        return Participant.AKA.value

    @staticmethod
    def _apply_hansoku_result(
        match: Match,
        winner_participant: str,
        session: rx.session,
    ) -> list[int]:
        """Aplica resultado de HANSOKU según sistema de competencia."""
        is_round_robin = (
            match.category is not None
            and match.category.competition_system == CompetitionSystem.ROUND_ROBIN.value
        )

        if is_round_robin:
            return KumiteScoringService._apply_hansoku_round_robin(
                match=match,
                winner_participant=winner_participant,
                session=session,
            )

        return KumiteScoringService._add_yuko_by_hansoku(
            match=match,
            participant=winner_participant,
            session=session,
            count=1,
        )

    @staticmethod
    def _apply_hansoku_round_robin(
        match: Match,
        winner_participant: str,
        session: rx.session,
    ) -> list[int]:
        """Art. 12.3.2: round-robin HANSOKU => 4-0 o score >4 preservado."""
        loser_participant = KumiteScoringService._get_opponent(winner_participant)

        if loser_participant == Participant.AKA.value:
            match.aka_score = 0
        else:
            match.ao_score = 0

        current_winner_score = (
            match.aka_score
            if winner_participant == Participant.AKA.value
            else match.ao_score
        )
        if current_winner_score > 4:
            return []

        needed = 4 - current_winner_score
        return KumiteScoringService._add_yuko_by_hansoku(
            match=match,
            participant=winner_participant,
            session=session,
            count=needed,
        )

    @staticmethod
    def _add_yuko_by_hansoku(
        match: Match,
        participant: str,
        session: rx.session,
        count: int,
    ) -> list[int]:
        """Suma YUKO(s) por HANSOKU y persiste auditoría MatchScore."""
        if count <= 0:
            return []

        if participant == Participant.AKA.value:
            match.aka_score += count
            match.aka_yuko_count += count
        else:
            match.ao_score += count
            match.ao_yuko_count += count

        created_score_ids: list[int] = []
        for _ in range(count):
            row = MatchScore(
                match_id=match.id,
                judge_id=match.referee_id or 1,
                participant=participant,
                score_value=1.0,
                score_type=ScoreType.YUKO.value,
                applied_by_id=None,
                is_valid=True,
                created_at=datetime.datetime.utcnow(),
            )
            session.add(row)
            session.flush()
            created_score_ids.append(row.id)

        return created_score_ids
