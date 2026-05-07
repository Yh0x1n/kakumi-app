"""Servicio de scoring Kata con reglas WKF 2026."""

from dataclasses import dataclass
from typing import Optional

import reflex as rx
from sqlmodel import select

from kakumi_app.models.kata_model import (
    BunkaiMode,
    FlagVote,
    KataDecisionRule,
    KataDuplicateScoreError,
    KataJudgeCountError,
    KataJudgeScore,
    KataRoundStanding,
    KataScoreValidationError,
)
from kakumi_app.models.tournament_model import Match, MatchType


@dataclass
class KataMatchResult:
    """Resultado de cálculo de ganador de un match Kata."""

    winner: Optional[str]
    aka_votes: int
    ao_votes: int
    is_draw: bool
    message: str
    success: bool = True
    panel_complete: bool = True
    needs_extra_kata: bool = False
    match_ended: bool = True


class KataScoringService:
    """Servicio backend para scoring de Kata."""

    VALID_PANEL_SIZES: tuple[int, ...] = (3, 5)
    SCORE_MIN: float = 5.0
    SCORE_MAX: float = 10.0
    SCORE_DQ: float = 0.0
    VP_WIN: int = 3
    VP_LOSS: int = 0

    @staticmethod
    def record_numerical_score(
        match_id: int,
        judge_id: int,
        participant: str,
        performer_id: Optional[int],
        team_id: Optional[int],
        score: float,
    ) -> KataJudgeScore:
        """Registra score numérico para AKA/AO."""
        if participant not in (FlagVote.AKA.value, FlagVote.AO.value):
            raise KataScoreValidationError("Participante inválido")

        if score != KataScoringService.SCORE_DQ and not (
            KataScoringService.SCORE_MIN <= score <= KataScoringService.SCORE_MAX
        ):
            raise KataScoreValidationError("Score fuera de rango permitido")

        with rx.session() as session:
            duplicate = session.exec(
                select(KataJudgeScore).where(
                    KataJudgeScore.match_id == match_id,
                    KataJudgeScore.judge_id == judge_id,
                    KataJudgeScore.participant == participant,
                    KataJudgeScore.is_flag_mode.is_(False),
                )
            ).first()
            if duplicate is not None:
                raise KataDuplicateScoreError("Juez ya puntuó este lado")

            score_row = KataJudgeScore(
                judge_id=judge_id,
                match_id=match_id,
                performer_id=performer_id,
                team_id=team_id,
                participant=participant,
                score=score,
                flag_vote=None,
                is_flag_mode=False,
            )
            session.add(score_row)
            session.commit()
            session.refresh(score_row)
            return score_row

    @staticmethod
    def record_flag_vote(
        match_id: int,
        judge_id: int,
        flag_vote: FlagVote,
    ) -> KataJudgeScore:
        """Registra voto directo por bandera."""
        vote_value = flag_vote.value if isinstance(flag_vote, FlagVote) else flag_vote
        if vote_value not in (FlagVote.AKA.value, FlagVote.AO.value):
            raise KataScoreValidationError("Voto de bandera inválido")

        with rx.session() as session:
            duplicate = session.exec(
                select(KataJudgeScore).where(
                    KataJudgeScore.match_id == match_id,
                    KataJudgeScore.judge_id == judge_id,
                    KataJudgeScore.is_flag_mode.is_(True),
                )
            ).first()
            if duplicate is not None:
                raise KataDuplicateScoreError("Juez ya votó en modo bandera")

            score_row = KataJudgeScore(
                judge_id=judge_id,
                match_id=match_id,
                participant=vote_value,
                score=0.0,
                flag_vote=vote_value,
                is_flag_mode=True,
            )
            session.add(score_row)
            session.commit()
            session.refresh(score_row)
            return score_row

    @staticmethod
    def calculate_match_winner(match_id: int) -> KataMatchResult:
        """Calcula ganador por mayoría de votos."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if match is None or match.category is None:
                raise KataJudgeCountError("Match o categoría no encontrados")

            panel_size = int(match.category.judge_panel_size)
            if panel_size not in KataScoringService.VALID_PANEL_SIZES:
                raise KataJudgeCountError("Panel de jueces inválido")

            all_scores = session.exec(
                select(KataJudgeScore).where(KataJudgeScore.match_id == match_id)
            ).all()

            flag_scores = [row for row in all_scores if row.is_flag_mode]
            if flag_scores:
                return KataScoringService._calculate_flag_winner(
                    flag_scores, panel_size
                )

            decision_rule = str(
                getattr(
                    match.category,
                    "kata_decision_rule",
                    KataDecisionRule.AVERAGE_WITH_DISCARD.value,
                )
                or KataDecisionRule.AVERAGE_WITH_DISCARD.value
            )
            return KataScoringService._calculate_numerical_winner(
                all_scores,
                panel_size,
                decision_rule=decision_rule,
            )

    @staticmethod
    def assign_victory_points(
        match_id: int,
        winner_participant: Optional[str],
        aka_votes: Optional[int] = None,
        ao_votes: Optional[int] = None,
    ) -> tuple[KataRoundStanding, KataRoundStanding]:
        """Asigna VP y votos recibidos para ambos lados del match."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if match is None:
                raise KataJudgeCountError("Match no encontrado")

            if aka_votes is None or ao_votes is None:
                result = KataScoringService.calculate_match_winner(match_id)
                aka_votes = result.aka_votes
                ao_votes = result.ao_votes

            aka_row = KataScoringService._get_or_create_standing(
                session=session,
                match_id=match_id,
                athlete_id=match.aka_id,
                team_id=match.aka_team_id,
            )
            ao_row = KataScoringService._get_or_create_standing(
                session=session,
                match_id=match_id,
                athlete_id=match.ao_id,
                team_id=match.ao_team_id,
            )

            aka_row.votes_received = int(aka_votes)
            ao_row.votes_received = int(ao_votes)

            if winner_participant == FlagVote.AKA.value:
                aka_row.victory_points = KataScoringService.VP_WIN
                ao_row.victory_points = KataScoringService.VP_LOSS
            elif winner_participant == FlagVote.AO.value:
                aka_row.victory_points = KataScoringService.VP_LOSS
                ao_row.victory_points = KataScoringService.VP_WIN
            else:
                aka_row.victory_points = KataScoringService.VP_LOSS
                ao_row.victory_points = KataScoringService.VP_LOSS

            session.add(aka_row)
            session.add(ao_row)
            session.commit()
            session.refresh(aka_row)
            session.refresh(ao_row)
            return aka_row, ao_row

    @staticmethod
    def calculate_standings(category_id: int) -> list[KataRoundStanding]:
        """Calcula tabla agregada por cascada VP > H2H > votos."""
        with rx.session() as session:
            matches = session.exec(
                select(Match).where(Match.category_id == category_id)
            ).all()
            if not matches:
                return []

            match_ids = [item.id for item in matches]
            standings_rows = session.exec(
                select(KataRoundStanding).where(
                    KataRoundStanding.match_id.in_(match_ids)
                )
            ).all()

            aggregated = KataScoringService._aggregate_rows(standings_rows)
            grouped: dict[int, list[KataRoundStanding]] = {}
            for row in aggregated:
                grouped.setdefault(row.victory_points, []).append(row)

            ordered: list[KataRoundStanding] = []
            for vp in sorted(grouped.keys(), reverse=True):
                tie_group = grouped[vp]
                if len(tie_group) == 1:
                    ordered.extend(tie_group)
                    continue

                resolved = KataScoringService._resolve_group_tiebreaker(
                    category_id=category_id,
                    rows=tie_group,
                )
                ordered.extend(resolved)

            return ordered

    @staticmethod
    def resolve_tiebreaker(
        category_id: int,
        athlete_a_id: Optional[int],
        athlete_b_id: Optional[int],
        team_a_id: Optional[int],
        team_b_id: Optional[int],
    ) -> list[KataRoundStanding]:
        """Resuelve desempate entre dos participantes."""
        standings = KataScoringService.calculate_standings(category_id)
        selected: list[KataRoundStanding] = []
        for row in standings:
            if (
                row.athlete_id in (athlete_a_id, athlete_b_id)
                and row.athlete_id is not None
            ):
                selected.append(row)
                continue
            if row.team_id in (team_a_id, team_b_id) and row.team_id is not None:
                selected.append(row)

        if len(selected) <= 1:
            return selected

        return KataScoringService._resolve_group_tiebreaker(
            category_id=category_id,
            rows=selected,
        )

    @staticmethod
    def apply_bunkai_mode(match_id: int) -> Match:
        """Propaga bunkai_mode de categoría a bunkai_required de match."""
        with rx.session() as session:
            match = session.get(Match, match_id)
            if match is None or match.category is None:
                raise KataJudgeCountError("Match o categoría no encontrados")

            mode = match.category.bunkai_mode
            if mode == BunkaiMode.NONE.value:
                match.bunkai_required = False
            elif mode == BunkaiMode.ALL_ROUNDS.value:
                match.bunkai_required = True
            elif mode == BunkaiMode.MEDALS_ONLY.value:
                match.bunkai_required = match.match_type in (
                    MatchType.FINAL.value,
                    MatchType.BRONZE.value,
                )
            else:
                raise KataScoreValidationError("bunkai_mode inválido")

            session.add(match)
            session.commit()
            session.refresh(match)
            return match

    @staticmethod
    def _calculate_flag_winner(
        flag_scores: list[KataJudgeScore], panel_size: int
    ) -> KataMatchResult:
        """Calcula ganador en modo FLAG."""
        if len(flag_scores) != panel_size:
            raise KataJudgeCountError("Panel incompleto para modo bandera")

        aka_votes = sum(
            1 for item in flag_scores if item.flag_vote == FlagVote.AKA.value
        )
        ao_votes = sum(1 for item in flag_scores if item.flag_vote == FlagVote.AO.value)
        winner = None
        is_draw = aka_votes == ao_votes
        if aka_votes > ao_votes:
            winner = FlagVote.AKA.value
        elif ao_votes > aka_votes:
            winner = FlagVote.AO.value

        return KataMatchResult(
            winner=winner,
            aka_votes=aka_votes,
            ao_votes=ao_votes,
            is_draw=is_draw,
            message="Winner calculado por votos de bandera",
        )

    @staticmethod
    def _calculate_numerical_winner(
        scores: list[KataJudgeScore],
        panel_size: int,
        decision_rule: str,
    ) -> KataMatchResult:
        """Calcula ganador en modo numérico comparando score por juez."""
        per_judge = KataScoringService._group_scores_by_judge(scores)

        if len(per_judge) != panel_size:
            raise KataJudgeCountError("Panel incompleto para modo numérico")

        aka_votes, ao_votes = KataScoringService._count_numerical_votes(per_judge)
        winner, is_draw = KataScoringService._resolve_numerical_winner(
            per_judge,
            decision_rule=decision_rule,
            aka_votes=aka_votes,
            ao_votes=ao_votes,
        )

        return KataMatchResult(
            winner=winner,
            aka_votes=aka_votes,
            ao_votes=ao_votes,
            is_draw=is_draw,
            message="Winner calculado por score numérico",
        )

    @staticmethod
    def _resolve_numerical_winner(
        per_judge: dict[int, dict[str, float]],
        *,
        decision_rule: str,
        aka_votes: int,
        ao_votes: int,
    ) -> tuple[Optional[str], bool]:
        """Resuelve ganador numérico por regla de decisión configurada."""
        if decision_rule == KataDecisionRule.MAJORITY_BY_JUDGE.value:
            if aka_votes > ao_votes:
                return FlagVote.AKA.value, False
            if ao_votes > aka_votes:
                return FlagVote.AO.value, False
            return None, True

        if decision_rule != KataDecisionRule.AVERAGE_WITH_DISCARD.value:
            raise KataScoreValidationError("Regla de decisión kata inválida")

        aka_scores = [scores[FlagVote.AKA.value] for scores in per_judge.values()]
        ao_scores = [scores[FlagVote.AO.value] for scores in per_judge.values()]
        aka_average = KataScoringService._average_with_optional_discard(aka_scores)
        ao_average = KataScoringService._average_with_optional_discard(ao_scores)
        if aka_average > ao_average:
            return FlagVote.AKA.value, False
        if ao_average > aka_average:
            return FlagVote.AO.value, False
        return None, True

    @staticmethod
    def _average_with_optional_discard(scores: list[float]) -> float:
        """Promedia score; con 5 jueces descarta extremo alto y bajo."""
        if len(scores) == 5:
            sorted_scores = sorted(scores)
            usable_scores = sorted_scores[1:-1]
            return sum(usable_scores) / len(usable_scores)
        return sum(scores) / len(scores)

    @staticmethod
    def _group_scores_by_judge(
        scores: list[KataJudgeScore],
    ) -> dict[int, dict[str, float]]:
        """Agrupa scores numéricos válidos por juez."""
        per_judge: dict[int, dict[str, float]] = {}
        for row in scores:
            if row.is_flag_mode:
                continue
            if row.participant not in (FlagVote.AKA.value, FlagVote.AO.value):
                continue
            per_judge.setdefault(row.judge_id, {})[row.participant] = row.score
        return per_judge

    @staticmethod
    def _count_numerical_votes(
        per_judge: dict[int, dict[str, float]],
    ) -> tuple[int, int]:
        """Cuenta votos AKA/AO comparando score por juez."""
        aka_votes = 0
        ao_votes = 0
        for judge_scores in per_judge.values():
            if (
                FlagVote.AKA.value not in judge_scores
                or FlagVote.AO.value not in judge_scores
            ):
                raise KataJudgeCountError("Faltan scores por juez")
            aka_score = judge_scores[FlagVote.AKA.value]
            ao_score = judge_scores[FlagVote.AO.value]
            if aka_score > ao_score:
                aka_votes += 1
            elif ao_score > aka_score:
                ao_votes += 1

        return aka_votes, ao_votes

    @staticmethod
    def _get_or_create_standing(
        session: rx.session,
        match_id: int,
        athlete_id: Optional[int],
        team_id: Optional[int],
    ) -> KataRoundStanding:
        """Retorna standing existente o crea fila nueva."""
        existing = session.exec(
            select(KataRoundStanding).where(
                KataRoundStanding.match_id == match_id,
                KataRoundStanding.athlete_id == athlete_id,
                KataRoundStanding.team_id == team_id,
            )
        ).first()
        if existing is not None:
            return existing
        return KataRoundStanding(
            match_id=match_id,
            athlete_id=athlete_id,
            team_id=team_id,
        )

    @staticmethod
    def _aggregate_rows(rows: list[KataRoundStanding]) -> list[KataRoundStanding]:
        """Suma VP y votos por participante/equipo."""
        grouped: dict[tuple[Optional[int], Optional[int]], KataRoundStanding] = {}
        for row in rows:
            key = (row.athlete_id, row.team_id)
            if key not in grouped:
                grouped[key] = KataRoundStanding(
                    match_id=0,
                    athlete_id=row.athlete_id,
                    team_id=row.team_id,
                    victory_points=0,
                    votes_received=0,
                    needs_extra_kata=False,
                )
            grouped[key].victory_points += row.victory_points
            grouped[key].votes_received += row.votes_received

        return list(grouped.values())

    @staticmethod
    def _resolve_group_tiebreaker(
        category_id: int,
        rows: list[KataRoundStanding],
    ) -> list[KataRoundStanding]:
        """Aplica cascada H2H -> votos -> extra kata."""
        if len(rows) == 2:
            h2h = KataScoringService._resolve_head_to_head(
                category_id, rows[0], rows[1]
            )
            if h2h is not None:
                return h2h

        sorted_by_votes = sorted(
            rows, key=lambda item: item.votes_received, reverse=True
        )
        if len(sorted_by_votes) >= 2 and (
            sorted_by_votes[0].votes_received == sorted_by_votes[1].votes_received
        ):
            for row in sorted_by_votes:
                row.needs_extra_kata = True

        return sorted_by_votes

    @staticmethod
    def _resolve_head_to_head(
        category_id: int,
        first: KataRoundStanding,
        second: KataRoundStanding,
    ) -> Optional[list[KataRoundStanding]]:
        """Resuelve desempate directo entre dos participantes."""

        def _same_competitor(
            match_athlete_id: Optional[int],
            match_team_id: Optional[int],
            standing: KataRoundStanding,
        ) -> bool:
            return (
                match_athlete_id == standing.athlete_id
                and match_team_id == standing.team_id
            )

        with rx.session() as session:
            matches = session.exec(
                select(Match).where(Match.category_id == category_id)
            ).all()
            for match in matches:
                if (
                    _same_competitor(match.aka_id, match.aka_team_id, first)
                    and _same_competitor(match.ao_id, match.ao_team_id, second)
                ) or (
                    _same_competitor(match.aka_id, match.aka_team_id, second)
                    and _same_competitor(match.ao_id, match.ao_team_id, first)
                ):
                    pair_rows = session.exec(
                        select(KataRoundStanding).where(
                            KataRoundStanding.match_id == match.id
                        )
                    ).all()
                    aka_row = next(
                        (
                            row
                            for row in pair_rows
                            if row.athlete_id == match.aka_id
                            and row.team_id == match.aka_team_id
                        ),
                        None,
                    )
                    ao_row = next(
                        (
                            row
                            for row in pair_rows
                            if row.athlete_id == match.ao_id
                            and row.team_id == match.ao_team_id
                        ),
                        None,
                    )
                    if aka_row is None or ao_row is None:
                        return None

                    if aka_row.victory_points > ao_row.victory_points:
                        winner_key = (match.aka_id, match.aka_team_id)
                    elif ao_row.victory_points > aka_row.victory_points:
                        winner_key = (match.ao_id, match.ao_team_id)
                    else:
                        return None

                    if (first.athlete_id, first.team_id) == winner_key:
                        return [first, second]
                    return [second, first]

        return None
