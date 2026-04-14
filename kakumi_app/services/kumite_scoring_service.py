"""Servicio de scoring Kumite con reglas WKF 2026."""

import datetime
from dataclasses import dataclass
from typing import Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchScore,
    MatchStatus,
    Participant,
    Penalty,
    PenaltyType,
    ScoreType,
)


@dataclass
class MatchResult:
    """Resultado de aplicación de puntuación."""

    success: bool
    match_ended: bool
    winner: Optional[str]
    message: str


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
    """Resultado de revocación manual de SENSHU."""

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
            )

        with rx.session() as session:
            match = session.get(Match, match_id)
            if not match:
                return MatchResult(False, False, None, "Match no encontrado")
            if match.status != MatchStatus.IN_PROGRESS.value:
                return MatchResult(False, False, None, "Match no está en progreso")

            KumiteScoringService._set_senshu_if_first(match, participant_value)

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

            winner = KumiteScoringService._check_match_termination(match)
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
            session.commit()

            return MatchResult(
                success=True,
                match_ended=winner is not None,
                winner=winner,
                message="Puntaje aplicado",
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
        del applied_by_id
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

            winner: Optional[str] = None
            if applied_level == PenaltyType.HANSOKU.value:
                winner = KumiteScoringService._get_opponent(participant_value)
                KumiteScoringService._apply_hansoku_result(
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
            session.commit()

            return PenaltyResult(
                success=True,
                penalty_type=applied_level,
                match_ended=winner is not None,
                winner=winner,
                message="Penalidad aplicada",
            )

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
    def _check_match_termination(match: Match) -> Optional[str]:
        """Finaliza match solo si diferencia de puntaje es >= 8."""
        score_diff = abs(match.aka_score - match.ao_score)
        if score_diff < KumiteScoringService.SUPERIORITY_LEAD:
            return None

        winner = (
            Participant.AKA.value
            if match.aka_score > match.ao_score
            else Participant.AO.value
        )
        match.status = MatchStatus.COMPLETED.value
        match.end_time = datetime.datetime.utcnow()
        match.winner_id = (
            match.aka_id if winner == Participant.AKA.value else match.ao_id
        )
        return winner

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
    def _set_senshu_if_first(match: Match, participant: str) -> None:
        """Asigna SENSHU solo en primer puntaje sin respuesta."""
        if match.aka_score == 0 and match.ao_score == 0:
            if participant == Participant.AKA.value:
                match.aka_senshu = True
                match.ao_senshu = False
            elif participant == Participant.AO.value:
                match.ao_senshu = True
                match.aka_senshu = False

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
    ) -> None:
        """Aplica resultado de HANSOKU según sistema de competencia."""
        is_round_robin = (
            match.category is not None
            and match.category.competition_system == CompetitionSystem.ROUND_ROBIN.value
        )

        if is_round_robin:
            KumiteScoringService._apply_hansoku_round_robin(
                match=match,
                winner_participant=winner_participant,
                session=session,
            )
            return

        KumiteScoringService._add_yuko_by_hansoku(
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
    ) -> None:
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
            return

        needed = 4 - current_winner_score
        KumiteScoringService._add_yuko_by_hansoku(
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
    ) -> None:
        """Suma YUKO(s) por HANSOKU y persiste auditoría MatchScore."""
        if count <= 0:
            return

        if participant == Participant.AKA.value:
            match.aka_score += count
            match.aka_yuko_count += count
        else:
            match.ao_score += count
            match.ao_yuko_count += count

        for _ in range(count):
            session.add(
                MatchScore(
                    match_id=match.id,
                    judge_id=match.referee_id or 1,
                    participant=participant,
                    score_value=1.0,
                    score_type=ScoreType.YUKO.value,
                    applied_by_id=None,
                    is_valid=True,
                    created_at=datetime.datetime.utcnow(),
                )
            )
