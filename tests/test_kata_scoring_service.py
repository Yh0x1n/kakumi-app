"""Tests del servicio de scoring Kata bajo reglas WKF 2026."""

import pytest
import reflex as rx

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import Match, MatchType, ScoreType


def _create_athlete(name: str, email: str) -> Athlete:
    """Crea atleta auxiliar para escenarios round-robin."""
    with rx.session() as session:
        athlete = Athlete(
            name=name,
            age=27,
            gender="MALE",
            email=email,
            belt_rank="Negro",
            dojo="Dojo Test",
            is_active=True,
        )
        session.add(athlete)
        session.commit()
        session.refresh(athlete)
        return athlete


def _create_match(category_id: int, aka_id: int, ao_id: int) -> Match:
    """Crea match auxiliar para pruebas de standings."""
    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=MatchType.ROUND_ROBIN.value,
            category_id=category_id,
            aka_id=aka_id,
            ao_id=ao_id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def _create_team_match(category_id: int, aka_team_id: int, ao_team_id: int) -> Match:
    """Crea match auxiliar para escenarios Team Kata."""
    with rx.session() as session:
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=MatchType.ROUND_ROBIN.value,
            category_id=category_id,
            aka_team_id=aka_team_id,
            ao_team_id=ao_team_id,
        )
        session.add(match)
        session.commit()
        session.refresh(match)
        return match


def test_score_type_exposes_kata_score() -> None:
    """ScoreType expone KATA_SCORE para auditoría de kata."""
    assert ScoreType.KATA_SCORE.value == "KATA_SCORE"


@pytest.mark.parametrize("score", [5.0, 7.5, 10.0, 0.0])
def test_record_numerical_score_accepts_valid_scores(
    kata_match, sample_judges, score: float
) -> None:
    """Acepta 5.0-10.0 y 0.0 (DQ) para score numérico."""
    from kakumi_app.models.kata_model import KataJudgeScore
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judge = sample_judges()[0]
    saved = KataScoringService.record_numerical_score(
        match_id=kata_match.id,
        judge_id=judge.id,
        participant="AKA",
        performer_id=kata_match.aka_id,
        team_id=None,
        score=score,
    )

    assert isinstance(saved, KataJudgeScore)
    assert saved.score == score


@pytest.mark.parametrize("score", [4.9, 10.1, -1.0])
def test_record_numerical_score_rejects_invalid_scores(
    kata_match, sample_judges, score: float
) -> None:
    """Rechaza score fuera de rango con excepción custom."""
    from kakumi_app.models.kata_model import KataScoreValidationError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judge = sample_judges()[0]
    with pytest.raises(KataScoreValidationError):
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=score,
        )


def test_record_numerical_score_rejects_duplicate_judge(
    kata_match, sample_judges
) -> None:
    """Rechaza score duplicado de mismo juez y mismo lado."""
    from kakumi_app.models.kata_model import KataDuplicateScoreError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judge = sample_judges()[0]
    KataScoringService.record_numerical_score(
        match_id=kata_match.id,
        judge_id=judge.id,
        participant="AKA",
        performer_id=kata_match.aka_id,
        team_id=None,
        score=7.3,
    )

    with pytest.raises(KataDuplicateScoreError):
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=8.1,
        )


def test_calculate_match_winner_numerical_majority_3_2(
    kata_match, sample_judges
) -> None:
    """Panel 5 jueces: mayoría 3-2 define ganador."""
    from kakumi_app.models.kata_model import KataDecisionRule
    from kakumi_app.services.kata_scoring_service import KataScoringService

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        category = match.category
        category.kata_decision_rule = KataDecisionRule.MAJORITY_BY_JUDGE.value
        session.add(category)
        session.commit()

    judges = sample_judges(5)
    for index, judge in enumerate(judges):
        aka_score = 8.0 if index < 3 else 7.0
        ao_score = 7.0 if index < 3 else 8.0
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=aka_score,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=ao_score,
        )

    result = KataScoringService.calculate_match_winner(kata_match.id)
    assert result.winner == "AKA"
    assert result.aka_votes == 3
    assert result.ao_votes == 2
    assert result.is_draw is False


def test_calculate_match_winner_rejects_panel_size_four(
    kata_match, sample_judges
) -> None:
    """Panel 4 debe rechazarse: contrato válido solo 3 o 5."""
    from kakumi_app.models.kata_model import KataDecisionRule
    from kakumi_app.models.kata_model import KataJudgeCountError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        category = match.category
        category.judge_panel_size = 4
        category.kata_decision_rule = KataDecisionRule.MAJORITY_BY_JUDGE.value
        session.add(category)
        session.commit()

    judges = sample_judges(4)
    for index, judge in enumerate(judges):
        aka_score = 8.2 if index < 3 else 7.1
        ao_score = 7.1 if index < 3 else 8.2
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=aka_score,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=ao_score,
        )

    with pytest.raises(KataJudgeCountError):
        KataScoringService.calculate_match_winner(kata_match.id)


def test_calculate_match_winner_average_with_discard_for_five_judges(
    kata_match, sample_judges
) -> None:
    """Modo legacy: descarta alto/bajo y define por promedio."""
    from kakumi_app.models.kata_model import KataDecisionRule
    from kakumi_app.services.kata_scoring_service import KataScoringService

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        category = match.category
        category.judge_panel_size = 5
        category.kata_decision_rule = KataDecisionRule.AVERAGE_WITH_DISCARD.value
        session.add(category)
        session.commit()

    judges = sample_judges(5)
    aka_scores = [9.9, 8.4, 8.5, 8.6, 7.0]
    ao_scores = [8.8, 8.3, 8.2, 8.1, 7.2]
    for index, judge in enumerate(judges):
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=aka_scores[index],
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=ao_scores[index],
        )

    result = KataScoringService.calculate_match_winner(kata_match.id)
    assert result.winner == "AKA"
    assert result.aka_votes == 4
    assert result.ao_votes == 1


def test_calculate_match_winner_rejects_panel_size_greater_than_five(
    kata_match, sample_judges
) -> None:
    """Panel 7 debe rechazarse por contrato 3..5."""
    from kakumi_app.models.kata_model import KataJudgeCountError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    with rx.session() as session:
        match = session.get(Match, kata_match.id)
        category = match.category
        category.judge_panel_size = 7
        session.add(category)
        session.commit()

    for judge in sample_judges(5):
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=8.0,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=7.0,
        )

    with pytest.raises(KataJudgeCountError):
        KataScoringService.calculate_match_winner(kata_match.id)


def test_record_flag_vote_creates_kata_judge_score(kata_match, sample_judges) -> None:
    """FLAG mode crea score con is_flag_mode=True."""
    from kakumi_app.models.kata_model import FlagVote
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judge = sample_judges()[0]
    saved = KataScoringService.record_flag_vote(
        match_id=kata_match.id,
        judge_id=judge.id,
        flag_vote=FlagVote.AKA,
    )

    assert saved.is_flag_mode is True
    assert saved.flag_vote == FlagVote.AKA.value


def test_record_flag_vote_rejects_duplicate_judge(kata_match, sample_judges) -> None:
    """FLAG mode rechaza voto duplicado de mismo juez."""
    from kakumi_app.models.kata_model import FlagVote, KataDuplicateScoreError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judge = sample_judges()[0]
    KataScoringService.record_flag_vote(
        match_id=kata_match.id,
        judge_id=judge.id,
        flag_vote=FlagVote.AKA,
    )

    with pytest.raises(KataDuplicateScoreError):
        KataScoringService.record_flag_vote(
            match_id=kata_match.id,
            judge_id=judge.id,
            flag_vote=FlagVote.AO,
        )


def test_calculate_match_winner_flag_majority_3_2(kata_match, sample_judges) -> None:
    """FLAG mode: mayoría 3-2 decide ganador."""
    from kakumi_app.models.kata_model import FlagVote
    from kakumi_app.services.kata_scoring_service import KataScoringService

    for index, judge in enumerate(sample_judges(5)):
        vote = FlagVote.AKA if index < 3 else FlagVote.AO
        KataScoringService.record_flag_vote(
            match_id=kata_match.id,
            judge_id=judge.id,
            flag_vote=vote,
        )

    result = KataScoringService.calculate_match_winner(kata_match.id)
    assert result.winner == "AKA"
    assert result.aka_votes == 3
    assert result.ao_votes == 2


def test_assign_victory_points_winner_3_loser_0(kata_match, sample_judges) -> None:
    """Asigna VP: ganador 3, perdedor 0."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judges = sample_judges(5)
    for index, judge in enumerate(judges):
        aka_score = 8.0 if index < 3 else 7.0
        ao_score = 7.0 if index < 3 else 8.0
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=aka_score,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=ao_score,
        )

    winner = KataScoringService.calculate_match_winner(kata_match.id)
    aka_row, ao_row = KataScoringService.assign_victory_points(
        match_id=kata_match.id,
        winner_participant=winner.winner,
    )
    assert aka_row.victory_points == 3
    assert ao_row.victory_points == 0


def test_assign_victory_points_updates_votes_received(
    kata_match, sample_judges
) -> None:
    """Persistencia VP incluye votos recibidos por lado."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    judges = sample_judges(5)
    for index, judge in enumerate(judges):
        aka_score = 8.0 if index < 4 else 7.0
        ao_score = 7.0 if index < 4 else 8.0
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=aka_score,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=ao_score,
        )

    winner = KataScoringService.calculate_match_winner(kata_match.id)
    aka_row, ao_row = KataScoringService.assign_victory_points(
        match_id=kata_match.id,
        winner_participant=winner.winner,
    )
    assert aka_row.votes_received == 4
    assert ao_row.votes_received == 1


def test_calculate_standings_orders_by_vp_desc(kata_category) -> None:
    """Standings ordena por VP descendente."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    a1 = _create_athlete("A1", "a1@test.dev")
    a2 = _create_athlete("A2", "a2@test.dev")
    a3 = _create_athlete("A3", "a3@test.dev")
    match_1 = _create_match(kata_category.id, a1.id, a2.id)
    match_2 = _create_match(kata_category.id, a1.id, a3.id)
    match_3 = _create_match(kata_category.id, a2.id, a3.id)

    KataScoringService.assign_victory_points(match_1.id, "AKA", aka_votes=3, ao_votes=2)
    KataScoringService.assign_victory_points(match_2.id, "AKA", aka_votes=4, ao_votes=1)
    KataScoringService.assign_victory_points(match_3.id, "AKA", aka_votes=3, ao_votes=2)

    standings = KataScoringService.calculate_standings(kata_category.id)
    assert standings[0].athlete_id == a1.id
    assert standings[0].victory_points == 6


def test_calculate_standings_breaks_tie_by_h2h(kata_category) -> None:
    """Empate VP se resuelve por head-to-head."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    a1 = _create_athlete("H2H-A1", "h2h-a1@test.dev")
    a2 = _create_athlete("H2H-A2", "h2h-a2@test.dev")
    a3 = _create_athlete("H2H-A3", "h2h-a3@test.dev")
    match_1 = _create_match(kata_category.id, a1.id, a2.id)
    match_2 = _create_match(kata_category.id, a1.id, a3.id)
    match_3 = _create_match(kata_category.id, a2.id, a3.id)

    KataScoringService.assign_victory_points(match_1.id, "AKA", aka_votes=3, ao_votes=2)
    KataScoringService.assign_victory_points(match_2.id, "AO", aka_votes=2, ao_votes=3)
    KataScoringService.assign_victory_points(match_3.id, "AKA", aka_votes=3, ao_votes=2)

    standings = KataScoringService.calculate_standings(kata_category.id)
    assert standings[0].victory_points == 3
    assert standings[1].victory_points == 3
    assert standings[0].athlete_id == a1.id
    assert standings[1].athlete_id == a2.id


def test_calculate_standings_breaks_tie_by_votes_received(kata_category) -> None:
    """Sin H2H aplicable, desempata por suma de votos."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    a1 = _create_athlete("VOTE-A1", "vote-a1@test.dev")
    a2 = _create_athlete("VOTE-A2", "vote-a2@test.dev")
    a3 = _create_athlete("VOTE-A3", "vote-a3@test.dev")
    a4 = _create_athlete("VOTE-A4", "vote-a4@test.dev")
    match_1 = _create_match(kata_category.id, a1.id, a3.id)
    match_2 = _create_match(kata_category.id, a2.id, a4.id)

    KataScoringService.assign_victory_points(match_1.id, "AKA", aka_votes=5, ao_votes=0)
    KataScoringService.assign_victory_points(match_2.id, "AKA", aka_votes=3, ao_votes=2)

    standings = KataScoringService.calculate_standings(kata_category.id)
    top_tied = [row for row in standings if row.victory_points == 3]
    assert top_tied[0].athlete_id == a1.id
    assert top_tied[0].votes_received == 5


def test_calculate_standings_flags_needs_extra_kata_when_unresolved(
    kata_category,
) -> None:
    """Empate sin resolver marca needs_extra_kata."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    a1 = _create_athlete("EXTRA-A1", "extra-a1@test.dev")
    a2 = _create_athlete("EXTRA-A2", "extra-a2@test.dev")
    a3 = _create_athlete("EXTRA-A3", "extra-a3@test.dev")
    a4 = _create_athlete("EXTRA-A4", "extra-a4@test.dev")
    match_1 = _create_match(kata_category.id, a1.id, a3.id)
    match_2 = _create_match(kata_category.id, a2.id, a4.id)

    KataScoringService.assign_victory_points(match_1.id, "AKA", aka_votes=3, ao_votes=2)
    KataScoringService.assign_victory_points(match_2.id, "AKA", aka_votes=3, ao_votes=2)

    standings = KataScoringService.calculate_standings(kata_category.id)
    tied_rows = [row for row in standings if row.victory_points == 3]
    assert tied_rows[0].needs_extra_kata is True
    assert tied_rows[1].needs_extra_kata is True


def test_calculate_standings_breaks_team_tie_by_h2h(kata_team_category) -> None:
    """Empate de equipos se resuelve por H2H usando team_id."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    category = kata_team_category()
    with rx.session() as session:
        team_1 = Team(name="H2H Team 1", category_id=category.id, member_count=0)
        team_2 = Team(name="H2H Team 2", category_id=category.id, member_count=0)
        team_3 = Team(name="H2H Team 3", category_id=category.id, member_count=0)
        session.add(team_1)
        session.add(team_2)
        session.add(team_3)
        session.commit()
        session.refresh(team_1)
        session.refresh(team_2)
        session.refresh(team_3)

    match_h2h = _create_team_match(category.id, team_1.id, team_2.id)
    match_13 = _create_team_match(category.id, team_1.id, team_3.id)

    KataScoringService.assign_victory_points(
        match_h2h.id,
        "AO",
        aka_votes=2,
        ao_votes=3,
    )
    KataScoringService.assign_victory_points(
        match_13.id,
        "AKA",
        aka_votes=5,
        ao_votes=0,
    )
    standings = KataScoringService.calculate_standings(category.id)
    tied_rows = [row for row in standings if row.victory_points == 3]

    assert len(tied_rows) == 2
    assert tied_rows[0].team_id == team_2.id
    assert tied_rows[1].team_id == team_1.id


def test_calculate_match_winner_raises_on_incomplete_judge_panel(
    kata_match, sample_judges
) -> None:
    """Lanza KataJudgeCountError si panel no está completo."""
    from kakumi_app.models.kata_model import KataJudgeCountError
    from kakumi_app.services.kata_scoring_service import KataScoringService

    for judge in sample_judges(4):
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AKA",
            performer_id=kata_match.aka_id,
            team_id=None,
            score=8.0,
        )
        KataScoringService.record_numerical_score(
            match_id=kata_match.id,
            judge_id=judge.id,
            participant="AO",
            performer_id=kata_match.ao_id,
            team_id=None,
            score=7.0,
        )

    with pytest.raises(KataJudgeCountError):
        KataScoringService.calculate_match_winner(kata_match.id)


@pytest.mark.parametrize(
    ("bunkai_mode", "match_type", "expected"),
    [
        ("NONE", MatchType.FINAL.value, False),
        ("MEDALS_ONLY", MatchType.FINAL.value, True),
        ("MEDALS_ONLY", MatchType.ELIMINATION.value, False),
        ("ALL_ROUNDS", MatchType.ELIMINATION.value, True),
    ],
)
def test_bunkai_mode_propagation(
    kata_team_category,
    sample_team,
    sample_team_2,
    bunkai_mode: str,
    match_type: str,
    expected: bool,
) -> None:
    """Propaga bunkai_mode de categoría a flag bunkai_required en match."""
    from kakumi_app.services.kata_scoring_service import KataScoringService

    category = kata_team_category(bunkai_mode=bunkai_mode)
    with rx.session() as session:
        team_1 = session.get(type(sample_team), sample_team.id)
        team_2 = session.get(type(sample_team_2), sample_team_2.id)
        team_1.category_id = category.id
        team_2.category_id = category.id
        match = Match(
            round=1,
            match_number=1,
            position=0,
            match_type=match_type,
            category_id=category.id,
            aka_team_id=team_1.id,
            ao_team_id=team_2.id,
        )
        session.add(team_1)
        session.add(team_2)
        session.add(match)
        session.commit()
        session.refresh(match)
        KataScoringService.apply_bunkai_mode(match.id)
        session.refresh(match)
        assert match.bunkai_required is expected
