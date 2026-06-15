"""Concurrency and retry behavior tests for penalty service."""

from unittest.mock import patch

import pytest
import reflex as rx
from sqlalchemy.exc import OperationalError

from kakumi_app.models.tournament_model import Match, MatchStatus, Participant
from kakumi_app.services.kumite_scoring_service import _with_retry, apply_penalty


@pytest.mark.skip(reason="requires PostgreSQL")
def test_scenario_1_concurrent_apply_penalty_documented() -> None:
    """Document expected Postgres contention behavior for same match writes."""


def test_scenario_2_with_for_update_noop_sqlite(
    rr_pool_fixture: dict[str, int],
) -> None:
    """SQLite ignores FOR UPDATE but apply_penalty still succeeds."""
    with rx.session() as session:
        match = session.get(Match, rr_pool_fixture["current_match_id"])
        assert match is not None
        match.status = MatchStatus.IN_PROGRESS.value
        session.add(match)
        session.commit()

        penalty = apply_penalty(
            session=session,
            match_id=rr_pool_fixture["current_match_id"],
            participant=Participant.AKA.value,
        )

        assert penalty.penalty_type == "C1"


def test_scenario_3_retry_backoff_called_on_contention() -> None:
    """_with_retry retries once after OperationalError and then succeeds."""
    operation_error = OperationalError("statement", {}, Exception("locked"))
    call_count = {"count": 0}

    def flaky_operation() -> str:
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise operation_error
        return "ok"

    with patch("kakumi_app.services.kumite_scoring_service.time.sleep") as sleep_mock:
        result = _with_retry(flaky_operation)  # type: ignore[arg-type]

    assert result == "ok"
    assert call_count["count"] == 2
    sleep_mock.assert_called_once()
