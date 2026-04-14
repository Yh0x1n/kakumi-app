"""Tests del servicio de scoring Kumite bajo reglas WKF 2026."""

import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    CompetitionSystem,
    Match,
    MatchScore,
    MatchStatus,
    Participant,
    PenaltyType,
    ScoreType,
)


def _set_match_in_progress(match_id: int) -> Match:
    """Setea un match a IN_PROGRESS y retorna la entidad refrescada."""
    with rx.session() as session:
        match = session.get(Match, match_id)
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def _set_match_completed(match_id: int) -> Match:
    """Setea un match a COMPLETED y retorna la entidad refrescada."""
    with rx.session() as session:
        match = session.get(Match, match_id)
        match.status = MatchStatus.COMPLETED.value
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def _set_match_competition_system(match_id: int, competition_system: str) -> None:
    """Actualiza competition_system de categoría del match."""
    with rx.session() as session:
        match = session.get(Match, match_id)
        category = match.category
        category.competition_system = competition_system
        session.add(category)
        session.commit()


def test_yuko_adds_1_point(sample_match, sample_user):
    """YUKO suma 1 punto al participante seleccionado."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.aka_score == 1
        assert refreshed.aka_yuko_count == 1


def test_waza_ari_adds_2_points(sample_match, sample_user):
    """WAZA_ARI suma 2 puntos al participante seleccionado."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AO,
        score_type=ScoreType.WAZA_ARI,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.ao_score == 2
        assert refreshed.ao_waza_ari_count == 1


def test_ippon_adds_3_points(sample_match, sample_user):
    """IPPON suma 3 puntos al participante seleccionado."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.IPPON,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.aka_score == 3
        assert refreshed.aka_ippon_count == 1


def test_ippon_alone_does_not_end_match(sample_match, sample_user):
    """Un solo IPPON no termina combate si ventaja < 8."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.IPPON,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    assert result.match_ended is False
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.IN_PROGRESS.value


def test_8_point_lead_ends_match(sample_match, sample_user):
    """Ventaja >= 8 termina match inmediatamente."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.IPPON,
        applied_by_id=sample_user.id,
    )
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.IPPON,
        applied_by_id=sample_user.id,
    )
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.WAZA_ARI,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    assert result.match_ended is True
    assert result.winner == Participant.AKA.value
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value


def test_senshu_set_on_first_score(sample_match, sample_user):
    """Primer puntaje sin respuesta activa SENSHU."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.aka_senshu is True
        assert refreshed.ao_senshu is False


def test_senshu_not_set_if_opponent_has_score(sample_match, sample_user):
    """Si rival ya puntuó, nuevo puntaje no activa SENSHU."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AO,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.ao_senshu is False


def test_revoke_senshu_clears_flag(sample_match, sample_user):
    """revoke_senshu limpia bandera del lado indicado."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    result = KumiteScoringService.revoke_senshu(match.id, Participant.AKA)
    assert result.success is True

    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.aka_senshu is False


def test_tiebreaker_senshu_wins(sample_match):
    """Desempate: SENSHU decide primero."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        match.aka_score = 2
        match.ao_score = 2
        match.aka_senshu = True
        session.add(match)
        session.commit()
        session.refresh(match)

    result = KumiteScoringService._get_tiebreaker_winner(match)
    assert result.winner == Participant.AKA.value
    assert result.reason == "SENSHU"


def test_tiebreaker_ippon_count_wins(sample_match):
    """Desempate: luego de SENSHU, gana más IPPON."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        match.aka_score = 3
        match.ao_score = 3
        match.aka_ippon_count = 1
        match.ao_ippon_count = 0
        session.add(match)
        session.commit()
        session.refresh(match)

    result = KumiteScoringService._get_tiebreaker_winner(match)
    assert result.winner == Participant.AKA.value
    assert result.reason == "MORE_IPPON"


def test_tiebreaker_waza_ari_count_wins(sample_match):
    """Desempate: si IPPON igual, gana más WAZA_ARI."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        match.aka_score = 2
        match.ao_score = 2
        match.aka_waza_ari_count = 1
        match.ao_waza_ari_count = 0
        session.add(match)
        session.commit()
        session.refresh(match)

    result = KumiteScoringService._get_tiebreaker_winner(match)
    assert result.winner == Participant.AKA.value
    assert result.reason == "MORE_WAZA_ARI"


def test_tiebreaker_draw_when_all_equal(sample_match):
    """Desempate: todo igual requiere HANTEI/HIKIWAKE."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        match.aka_score = 2
        match.ao_score = 2
        session.add(match)
        session.commit()
        session.refresh(match)

    result = KumiteScoringService._get_tiebreaker_winner(match)
    assert result.winner is None
    assert result.is_draw is True
    assert result.reason == "HANTEI_REQUIRED"


def test_penalty_chui_escalation(sample_match, sample_user):
    """Escalación: 3 CHUI y luego HANSOKU_CHUI."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    for _ in range(3):
        result = KumiteScoringService.apply_penalty(
            match_id=match.id,
            participant=Participant.AKA,
            penalty_type=PenaltyType.CHUI,
            reason="Falta menor",
            applied_by_id=sample_user.id,
        )
        assert result.penalty_type == PenaltyType.CHUI.value

    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="Cuarta falta",
        applied_by_id=sample_user.id,
    )
    assert result.penalty_type == PenaltyType.HANSOKU_CHUI.value


def test_penalty_hansoku_ends_match(sample_match, sample_user):
    """HANSOKU termina match y otorga YUKO al oponente."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU,
        reason="Falta grave",
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    assert result.match_ended is True
    assert result.winner == Participant.AO.value

    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.ao_score == 1


def test_hansoku_chui_escalates_to_hansoku(sample_match, sample_user):
    """HANSOKU_CHUI previo + nueva infracción escala a HANSOKU y termina."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)

    first = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU_CHUI,
        reason="Penalidad previa",
        applied_by_id=sample_user.id,
    )
    second = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="Nueva infracción",
        applied_by_id=sample_user.id,
    )

    assert first.success is True
    assert first.penalty_type == PenaltyType.HANSOKU_CHUI.value
    assert second.success is True
    assert second.penalty_type == PenaltyType.HANSOKU.value
    assert second.match_ended is True
    assert second.winner == Participant.AO.value


def test_hansoku_creates_yuko_match_score_for_opponent(sample_match, sample_user):
    """HANSOKU crea MatchScore audit con score_type YUKO para rival."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU,
        reason="Descalificación",
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        scores = session.exec(
            select(MatchScore).where(MatchScore.match_id == match.id)
        ).all()
        assert len(scores) == 1
        assert scores[0].participant == Participant.AO.value
        assert scores[0].score_type == ScoreType.YUKO.value


def test_hansoku_in_elimination_ends_match_directly(sample_match, sample_user):
    """En eliminación, HANSOKU termina combate sin regla 4-0 round-robin."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    _set_match_competition_system(match.id, CompetitionSystem.ELIMINATION.value)

    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU,
        reason="Descalificación",
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    assert result.match_ended is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.aka_score == 0
        assert refreshed.ao_score == 1


def test_hansoku_in_round_robin_sets_4_0_when_opponent_has_less(
    sample_match, sample_user
):
    """En round-robin, HANSOKU fuerza mínimo 4-0 (YUKO contado)."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    _set_match_competition_system(match.id, CompetitionSystem.ROUND_ROBIN.value)

    with rx.session() as session:
        seeded = session.get(Match, match.id)
        seeded.ao_score = 2
        seeded.ao_yuko_count = 2
        session.add(seeded)
        session.commit()

    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU,
        reason="Descalificación",
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.aka_score == 0
        assert refreshed.ao_score == 4


def test_hansoku_in_round_robin_keeps_score_when_opponent_has_more_than_4(
    sample_match, sample_user
):
    """En round-robin, si rival ya tiene >4, score se conserva."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    _set_match_competition_system(match.id, CompetitionSystem.ROUND_ROBIN.value)

    with rx.session() as session:
        seeded = session.get(Match, match.id)
        seeded.ao_score = 5
        seeded.aka_score = 3
        session.add(seeded)
        session.commit()

    result = KumiteScoringService.apply_penalty(
        match_id=match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.HANSOKU,
        reason="Descalificación",
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        refreshed = session.get(Match, match.id)
        assert refreshed.status == MatchStatus.COMPLETED.value
        assert refreshed.aka_score == 0
        assert refreshed.ao_score == 5


def test_resolve_tiebreaker_public_method_exists(sample_match):
    """Servicio expone resolve_tiebreaker(match_id) como API pública."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    with rx.session() as session:
        match = session.get(Match, sample_match.id)
        match.aka_score = 2
        match.ao_score = 2
        match.aka_senshu = True
        session.add(match)
        session.commit()

    result = KumiteScoringService.resolve_tiebreaker(sample_match.id)
    assert result.winner == Participant.AKA.value
    assert result.reason == "SENSHU"
    assert result.is_draw is False


def test_apply_score_invalid_when_match_not_in_progress(sample_match, sample_user):
    """apply_score falla si match no está IN_PROGRESS."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    _set_match_completed(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=sample_match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    assert result.success is False


def test_match_score_record_created_on_apply(sample_match, sample_user):
    """apply_score crea MatchScore con audit operator aplicado."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    assert result.success is True
    with rx.session() as session:
        scores = session.exec(
            select(MatchScore).where(MatchScore.match_id == match.id)
        ).all()
        assert len(scores) == 1
        assert scores[0].applied_by_id == sample_user.id
        assert scores[0].score_type == ScoreType.YUKO.value


def test_apply_penalty_invalid_when_match_not_in_progress(sample_match, sample_user):
    """apply_penalty falla si match no está IN_PROGRESS."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    _set_match_completed(sample_match.id)
    result = KumiteScoringService.apply_penalty(
        match_id=sample_match.id,
        participant=Participant.AKA,
        penalty_type=PenaltyType.CHUI,
        reason="Falta fuera de tiempo",
        applied_by_id=sample_user.id,
    )

    assert result.success is False


def test_apply_score_rejects_invalid_score_type(sample_match, sample_user):
    """apply_score rechaza tipo de puntaje no permitido."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant=Participant.AKA,
        score_type="INVALID",  # type: ignore[arg-type]
        applied_by_id=sample_user.id,
    )

    assert result.success is False


def test_apply_score_rejects_invalid_participant(sample_match, sample_user):
    """apply_score rechaza participante inválido."""
    from kakumi_app.services.kumite_scoring_service import KumiteScoringService

    match = _set_match_in_progress(sample_match.id)
    result = KumiteScoringService.apply_score(
        match_id=match.id,
        participant="INVALID",  # type: ignore[arg-type]
        score_type=ScoreType.YUKO,
        applied_by_id=sample_user.id,
    )

    assert result.success is False
