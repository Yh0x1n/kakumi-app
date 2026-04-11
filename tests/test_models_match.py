"""
KAKUMI Tests - Modelos de Encuentro
====================================
Tests para: Match, MatchScore, Penalty, Tatami
Cubre: CRUD, relaciones, enums de scoring WKF 2026.
"""

import datetime

import pytest
import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import (
    Match,
    MatchScore,
    MatchStatus,
    MatchType,
    Participant,
    ParticipantSide,
    Penalty,
    PenaltyType,
    ScoreType,
    Tatami,
)


# =============================================================================
# MATCH TESTS
# =============================================================================


class TestMatchCRUD:
    """Tests de CRUD para el modelo Match."""

    def test_create_match(self, sample_match):
        """Un encuentro creado tiene los campos correctos."""
        assert sample_match.id is not None
        assert sample_match.round == 1
        assert sample_match.match_number == 1
        assert sample_match.position == 0
        assert sample_match.match_type == MatchType.ELIMINATION.value
        assert sample_match.status == MatchStatus.PENDING.value
        assert sample_match.aka_score == 0
        assert sample_match.ao_score == 0

    def test_create_match_minimal(self, sample_category):
        """Un encuentro se puede crear solo con category_id."""
        with rx.session() as session:
            match = Match(
                category_id=sample_category.id,
            )
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.id is not None
            assert match.round == 1  # default
            assert match.match_number == 1  # default
            assert match.match_type == MatchType.ELIMINATION.value  # default
            assert match.status == MatchStatus.PENDING.value  # default
            assert match.aka_score == 0  # default
            assert match.ao_score == 0  # default

    def test_read_match_by_id(self, sample_match):
        """Se puede recuperar un encuentro por ID."""
        with rx.session() as session:
            result = session.get(Match, sample_match.id)
            assert result is not None
            assert result.round == 1

    def test_update_match_scores(self, sample_match):
        """Se pueden actualizar los puntajes de un encuentro."""
        with rx.session() as session:
            match = session.get(Match, sample_match.id)
            match.aka_score = 3
            match.ao_score = 1
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.aka_score == 3
            assert match.ao_score == 1

    def test_update_match_status(self, sample_match):
        """Se puede actualizar el estado de un encuentro."""
        with rx.session() as session:
            match = session.get(Match, sample_match.id)
            match.status = MatchStatus.IN_PROGRESS.value
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.status == MatchStatus.IN_PROGRESS.value

    def test_delete_match(self, sample_category):
        """Se puede eliminar un encuentro."""
        with rx.session() as session:
            match = Match(
                category_id=sample_category.id,
                round=99,
            )
            session.add(match)
            session.commit()
            match_id = match.id

            session.delete(match)
            session.commit()

            result = session.get(Match, match_id)
            assert result is None


class TestMatchType:
    """Tests de tipos de encuentro según specs.md sección 2.5."""

    def test_match_type_enum_values(self):
        """MatchType enum tiene los valores correctos."""
        assert MatchType.ELIMINATION.value == "ELIMINATION"
        assert MatchType.BRONZE.value == "BRONZE"
        assert MatchType.FINAL.value == "FINAL"
        assert MatchType.ROUND_ROBIN.value == "ROUND_ROBIN"

    def test_match_status_enum_values(self):
        """MatchStatus enum tiene los valores correctos."""
        assert MatchStatus.PENDING.value == "PENDING"
        assert MatchStatus.READY.value == "READY"
        assert MatchStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert MatchStatus.COMPLETED.value == "COMPLETED"
        assert MatchStatus.DISQUALIFIED.value == "DISQUALIFIED"

    def test_create_bronze_match(self, sample_category):
        """Se puede crear un encuentro de tipo BRONZE."""
        with rx.session() as session:
            match = Match(
                category_id=sample_category.id,
                match_type=MatchType.BRONZE.value,
                round=3,
                match_number=1,
            )
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.match_type == MatchType.BRONZE.value

    def test_create_final_match(self, sample_category):
        """Se puede crear un encuentro de tipo FINAL."""
        with rx.session() as session:
            match = Match(
                category_id=sample_category.id,
                match_type=MatchType.FINAL.value,
                round=4,
                match_number=1,
            )
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.match_type == MatchType.FINAL.value


class TestMatchRelationships:
    """Tests de relaciones del modelo Match."""

    def test_match_belongs_to_category(self, sample_match, sample_category):
        """Un encuentro pertenece a una categoría."""
        assert sample_match.category_id == sample_category.id

    def test_match_has_aka_and_ao(self, sample_match, sample_athlete, sample_athlete_2):
        """Un encuentro tiene participantes aka y ao asignados."""
        assert sample_match.aka_id == sample_athlete.id
        assert sample_match.ao_id == sample_athlete_2.id

    def test_match_has_referee(self, sample_match, sample_referee):
        """Un encuentro tiene un árbitro asignado."""
        assert sample_match.referee_id == sample_referee.id

    def test_match_has_tatami(self, sample_match, sample_tatami):
        """Un encuentro tiene un tatami asignado."""
        assert sample_match.tatami_id == sample_tatami.id

    def test_match_winner_not_set_initially(self, sample_match):
        """Inicialmente no hay ganador asignado."""
        assert sample_match.winner_id is None

    def test_match_set_winner(self, sample_match, sample_athlete):
        """Se puede asignar un ganador al encuentro."""
        with rx.session() as session:
            match = session.get(Match, sample_match.id)
            match.winner_id = sample_athlete.id
            match.status = MatchStatus.COMPLETED.value
            session.add(match)
            session.commit()
            session.refresh(match)

            assert match.winner_id == sample_athlete.id
            assert match.status == MatchStatus.COMPLETED.value


# =============================================================================
# MATCH SCORE TESTS
# =============================================================================


class TestMatchScoreCRUD:
    """Tests de CRUD para el modelo MatchScore."""

    def test_create_match_score(self, sample_match, sample_referee):
        """Se puede crear una puntuación para un encuentro."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
                participant=Participant.AKA.value,
                score_value=3.0,
                score_type=ScoreType.IPPON.value,
                technique_time=45,
                is_valid=True,
            )
            session.add(score)
            session.commit()
            session.refresh(score)

            assert score.id is not None
            assert score.match_id == sample_match.id
            assert score.judge_id == sample_referee.id
            assert score.participant == Participant.AKA.value
            assert score.score_value == 3.0
            assert score.score_type == ScoreType.IPPON.value

    def test_create_match_score_defaults(self, sample_match, sample_referee):
        """Una puntuación tiene defaults correctos."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
            )
            session.add(score)
            session.commit()
            session.refresh(score)

            assert score.participant == Participant.AKA.value  # default
            assert score.score_value == 0.0  # default
            assert score.score_type == ScoreType.YUKO.value  # default
            assert score.is_valid is True  # default

    def test_read_match_score(self, sample_match, sample_referee):
        """Se puede recuperar una puntuación por ID."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
                score_type=ScoreType.WAZA_ARI.value,
            )
            session.add(score)
            session.commit()
            score_id = score.id

            result = session.get(MatchScore, score_id)
            assert result is not None
            assert result.score_type == ScoreType.WAZA_ARI.value

    def test_delete_match_score(self, sample_match, sample_referee):
        """Se puede eliminar una puntuación."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
            )
            session.add(score)
            session.commit()
            score_id = score.id

            session.delete(score)
            session.commit()

            result = session.get(MatchScore, score_id)
            assert result is None


class TestMatchScoreTypes:
    """Tests de tipos de puntuación WKF 2026."""

    def test_score_type_enum_values(self):
        """ScoreType enum tiene los valores WKF 2026 correctos."""
        assert ScoreType.IPPON.value == "IPPON"
        assert ScoreType.WAZA_ARI.value == "WAZA_ARI"
        assert ScoreType.YUKO.value == "YUKO"
        assert ScoreType.PENALTY.value == "PENALTY"
        assert ScoreType.WARNING.value == "WARNING"

    def test_participant_enum_values(self):
        """Participant enum tiene AKA y AO."""
        assert Participant.AKA.value == "AKA"
        assert Participant.AO.value == "AO"

    def test_score_for_ao_participant(self, sample_match, sample_referee):
        """Se puede crear una puntuación para el participante AO."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
                participant=Participant.AO.value,
                score_value=2.0,
                score_type=ScoreType.WAZA_ARI.value,
            )
            session.add(score)
            session.commit()
            session.refresh(score)

            assert score.participant == Participant.AO.value


class TestMatchScoreRelationships:
    """Tests de relaciones del modelo MatchScore."""

    def test_score_belongs_to_match(self, sample_match, sample_referee):
        """Una puntuación pertenece a un encuentro."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
            )
            session.add(score)
            session.commit()

            assert score.match_id == sample_match.id

    def test_score_has_judge(self, sample_match, sample_referee):
        """Una puntuación está vinculada a un árbitro/juez."""
        with rx.session() as session:
            score = MatchScore(
                match_id=sample_match.id,
                judge_id=sample_referee.id,
            )
            session.add(score)
            session.commit()

            assert score.judge_id == sample_referee.id


# =============================================================================
# PENALTY TESTS
# =============================================================================


class TestPenaltyCRUD:
    """Tests de CRUD para el modelo Penalty."""

    def test_create_penalty(self, sample_match, sample_referee):
        """Se puede crear una penalización."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                participant=ParticipantSide.AKA.value,
                penalty_type=PenaltyType.CHUI.value,
                reason="Contacto excesivo",
                rule_reference="WKF Rule 7.1",
                is_accumulated=False,
                match_time_seconds=60,
            )
            session.add(penalty)
            session.commit()
            session.refresh(penalty)

            assert penalty.id is not None
            assert penalty.match_id == sample_match.id
            assert penalty.given_by_id == sample_referee.id
            assert penalty.participant == ParticipantSide.AKA.value
            assert penalty.penalty_type == PenaltyType.CHUI.value
            assert penalty.reason == "Contacto excesivo"

    def test_create_penalty_defaults(self, sample_match, sample_referee):
        """Una penalización tiene defaults correctos."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                reason="Razon por defecto",
            )
            session.add(penalty)
            session.commit()
            session.refresh(penalty)

            assert penalty.participant == ParticipantSide.AKA.value  # default
            assert penalty.penalty_type == PenaltyType.CHUI.value  # default
            assert penalty.is_accumulated is False  # default

    def test_read_penalty(self, sample_match, sample_referee):
        """Se puede recuperar una penalización por ID."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                reason="Test read",
            )
            session.add(penalty)
            session.commit()
            penalty_id = penalty.id

            result = session.get(Penalty, penalty_id)
            assert result is not None
            assert result.reason == "Test read"

    def test_delete_penalty(self, sample_match, sample_referee):
        """Se puede eliminar una penalización."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                reason="Eliminar esta",
            )
            session.add(penalty)
            session.commit()
            penalty_id = penalty.id

            session.delete(penalty)
            session.commit()

            result = session.get(Penalty, penalty_id)
            assert result is None


class TestPenaltyTypes:
    """Tests de tipos de penalización WKF 2026."""

    def test_penalty_type_enum_values(self):
        """PenaltyType enum tiene los valores WKF 2026 correctos."""
        assert PenaltyType.CHUI.value == "CHUI"
        assert PenaltyType.HANSOKU_CHUI.value == "HANSOKU_CHUI"
        assert PenaltyType.HANSOKU.value == "HANSOKU"
        assert PenaltyType.SHIKKAKU.value == "SHIKKAKU"

    def test_participant_side_enum_values(self):
        """ParticipantSide enum tiene AKA, AO y BOTH."""
        assert ParticipantSide.AKA.value == "AKA"
        assert ParticipantSide.AO.value == "AO"
        assert ParticipantSide.BOTH.value == "BOTH"

    def test_penalty_to_both_participants(self, sample_match, sample_referee):
        """Se puede crear una penalización para BOTH participantes."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                participant=ParticipantSide.BOTH.value,
                penalty_type=PenaltyType.CHUI.value,
                reason="Ambos fuera de area",
            )
            session.add(penalty)
            session.commit()
            session.refresh(penalty)

            assert penalty.participant == ParticipantSide.BOTH.value

    def test_hansoku_penalty(self, sample_match, sample_referee):
        """Se puede crear una penalización HANSOKU (descalificación)."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                participant=ParticipantSide.AO.value,
                penalty_type=PenaltyType.HANSOKU.value,
                reason="Conducta antideportiva grave",
                is_accumulated=True,
            )
            session.add(penalty)
            session.commit()
            session.refresh(penalty)

            assert penalty.penalty_type == PenaltyType.HANSOKU.value
            assert penalty.is_accumulated is True


class TestPenaltyRelationships:
    """Tests de relaciones del modelo Penalty."""

    def test_penalty_belongs_to_match(self, sample_match, sample_referee):
        """Una penalización pertenece a un encuentro."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                reason="Test relacion",
            )
            session.add(penalty)
            session.commit()

            assert penalty.match_id == sample_match.id

    def test_penalty_given_by_referee(self, sample_match, sample_referee):
        """Una penalización está vinculada al árbitro que la impuso."""
        with rx.session() as session:
            penalty = Penalty(
                match_id=sample_match.id,
                given_by_id=sample_referee.id,
                reason="Test arbitro",
            )
            session.add(penalty)
            session.commit()

            assert penalty.given_by_id == sample_referee.id


# =============================================================================
# TATAMI TESTS
# =============================================================================


class TestTatamiCRUD:
    """Tests de CRUD para el modelo Tatami."""

    def test_create_tatami(self, sample_tatami):
        """Un tatami creado tiene los campos correctos."""
        assert sample_tatami.id is not None
        assert sample_tatami.name == "Tatami 1"
        assert sample_tatami.location == "Sector A"
        assert sample_tatami.is_active is True

    def test_create_tatami_minimal(self, sample_tournament):
        """Un tatami se puede crear solo con campos obligatorios."""
        with rx.session() as session:
            tatami = Tatami(
                name="Tatami 2",
                tournament_id=sample_tournament.id,
            )
            session.add(tatami)
            session.commit()
            session.refresh(tatami)

            assert tatami.id is not None
            assert tatami.name == "Tatami 2"
            assert tatami.location is None
            assert tatami.is_active is True  # default

    def test_read_tatami_by_id(self, sample_tatami):
        """Se puede recuperar un tatami por ID."""
        with rx.session() as session:
            result = session.get(Tatami, sample_tatami.id)
            assert result is not None
            assert result.name == "Tatami 1"

    def test_update_tatami(self, sample_tatami):
        """Se puede actualizar un tatami."""
        with rx.session() as session:
            tatami = session.get(Tatami, sample_tatami.id)
            tatami.location = "Sector B"
            tatami.is_active = False
            session.add(tatami)
            session.commit()
            session.refresh(tatami)

            assert tatami.location == "Sector B"
            assert tatami.is_active is False

    def test_delete_tatami(self, sample_tournament):
        """Se puede eliminar un tatami."""
        with rx.session() as session:
            tatami = Tatami(
                name="Tatami Eliminable",
                tournament_id=sample_tournament.id,
            )
            session.add(tatami)
            session.commit()
            tatami_id = tatami.id

            session.delete(tatami)
            session.commit()

            result = session.get(Tatami, tatami_id)
            assert result is None


class TestTatamiRelationships:
    """Tests de relaciones del modelo Tatami."""

    def test_tatami_belongs_to_tournament(self, sample_tatami, sample_tournament):
        """Un tatami pertenece a un torneo."""
        assert sample_tatami.tournament_id == sample_tournament.id

    def test_tatami_current_match_optional(self, sample_tatami):
        """Inicialmente current_match_id es None."""
        assert sample_tatami.current_match_id is None

    def test_tatami_set_current_match(self, sample_tatami, sample_match):
        """Se puede asignar un encuentro actual al tatami."""
        with rx.session() as session:
            tatami = session.get(Tatami, sample_tatami.id)
            tatami.current_match_id = sample_match.id
            session.add(tatami)
            session.commit()
            session.refresh(tatami)

            assert tatami.current_match_id == sample_match.id
