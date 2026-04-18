"""Schema-level relationship symmetry tests for db-schema-indexes."""

from sqlalchemy import inspect as sa_inspect

from kakumi_app.models.athlete_model import Athlete
from kakumi_app.models.referee_model import Referee
from kakumi_app.models.team_model import Team
from kakumi_app.models.tournament_model import Match, MatchScore, Penalty, Tatami
from kakumi_app.models.user_model import User


def test_match_relationship_back_populates_contract() -> None:
    """Match-side relationships must declare symmetric back_populates."""
    rel = sa_inspect(Match).relationships

    assert rel["aka"].back_populates == "matches_as_aka"
    assert rel["ao"].back_populates == "matches_as_ao"
    assert rel["winner"].back_populates == "matches_won"
    assert rel["aka_team"].back_populates == "matches_as_aka"
    assert rel["ao_team"].back_populates == "matches_as_ao"
    assert rel["tatami"].back_populates == "matches"
    assert rel["referee"].back_populates == "matches_as_referee"


def test_score_and_penalty_relationship_back_populates_contract() -> None:
    """Score/Penalty relationships must declare symmetric back_populates."""
    score_rel = sa_inspect(MatchScore).relationships
    penalty_rel = sa_inspect(Penalty).relationships

    assert score_rel["judge"].back_populates == "scores_as_judge"
    assert score_rel["applied_by"].back_populates == "applied_scores"
    assert penalty_rel["given_by"].back_populates == "penalties_given"


def test_reverse_relationship_attributes_exist() -> None:
    """Reverse relationship attributes required by REQ-1 must exist."""
    assert "matches_as_aka" in sa_inspect(Athlete).relationships
    assert "matches_as_ao" in sa_inspect(Athlete).relationships
    assert "matches_won" in sa_inspect(Athlete).relationships
    assert "matches_as_aka" in sa_inspect(Team).relationships
    assert "matches_as_ao" in sa_inspect(Team).relationships
    assert "matches" in sa_inspect(Tatami).relationships
    assert "applied_scores" in sa_inspect(User).relationships


def test_tatami_current_match_back_reference_contract() -> None:
    """Tatami.current_match must have back reference on Match."""
    tatami_rel = sa_inspect(Tatami).relationships
    match_rel = sa_inspect(Match).relationships

    assert tatami_rel["current_match"].back_populates == "current_tatamis"
    assert match_rel["current_tatamis"].back_populates == "current_match"
    assert match_rel["current_tatamis"].uselist is True
    assert tatami_rel["current_match"].uselist is False


def test_referee_reverse_relationships_still_intact() -> None:
    """Referee reverse side must remain wired to Match/Score/Penalty."""
    rel = sa_inspect(Referee).relationships
    assert rel["matches_as_referee"].back_populates == "referee"
    assert rel["scores_as_judge"].back_populates == "judge"
    assert rel["penalties_given"].back_populates == "given_by"
