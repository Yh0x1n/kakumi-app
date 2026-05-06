"""Bracket transformation helpers for competition UI."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, TypedDict


class MatchCardData(TypedDict):
    """Render-ready match payload."""

    id: int
    round: int
    position: int
    status: str
    match_type: str
    aka_label: str
    ao_label: str
    tatami_label: str | None
    referee_label: str | None
    live_match_href: str | None


class BracketRoundData(TypedDict):
    """Bracket round payload."""

    round: int
    matches: list[MatchCardData]


class BracketCategoryData(TypedDict):
    """Bracket category payload."""

    id: int
    name: str
    modality: str
    competition_system: str
    status: str
    rounds: list[BracketRoundData]


class TournamentBracketData(TypedDict):
    """Tournament header payload."""

    id: int
    name: str
    status: str
    tatami_count: int


class CompetitionCategoryData(TypedDict):
    """Competition category summary payload."""

    id: int
    name: str
    modality: str
    competition_system: str
    status: str


def _resolve_participant_label(name: str | None, round_number: int) -> str:
    """Resolve participant display labels for bracket and category pages."""
    if name:
        return name
    return "TBD" if round_number > 1 else "BYE"


def _to_display_match(match: Mapping[str, Any]) -> MatchCardData:
    """Convert a raw match mapping into render-ready JSON data."""
    round_number = int(match.get("round") or 0)
    aka_label = match.get("aka_label")
    ao_label = match.get("ao_label")
    return {
        "id": int(match.get("id") or 0),
        "round": round_number,
        "position": int(match.get("position") or 0),
        "status": str(match.get("status") or "PENDING"),
        "match_type": str(match.get("match_type") or "ELIMINATION"),
        "aka_label": aka_label
        if aka_label is not None
        else _resolve_participant_label(match.get("aka_name"), round_number),
        "ao_label": ao_label
        if ao_label is not None
        else _resolve_participant_label(match.get("ao_name"), round_number),
        "tatami_label": match.get("tatami_label", match.get("tatami_name")),
        "referee_label": match.get("referee_label", match.get("referee_name")),
        "live_match_href": match.get("live_match_href"),
    }


def group_matches_by_round(
    matches: Sequence[Mapping[str, Any]],
) -> list[BracketRoundData]:
    """Group match payloads by round in deterministic order."""
    grouped_matches: dict[int, list[MatchCardData]] = defaultdict(list)

    sorted_matches = sorted(
        matches,
        key=lambda match: (
            int(match.get("round") or 0),
            int(match.get("position") or 0),
            int(match.get("id") or 0),
        ),
    )

    for match in sorted_matches:
        display_match = _to_display_match(match)
        grouped_matches[display_match["round"]].append(display_match)

    return [
        {"round": round_number, "matches": grouped_matches[round_number]}
        for round_number in sorted(grouped_matches)
    ]


def build_match_cards(
    matches: Sequence[Any],
    *,
    athlete_names: Mapping[int, str],
    team_names: Mapping[int, str],
    tatami_names: Mapping[int, str],
    referee_names: Mapping[int, str],
) -> list[MatchCardData]:
    """Build render-ready match card payloads from persisted match rows."""
    payloads: list[dict[str, Any]] = []

    for match in sorted(
        matches,
        key=lambda current: (
            int(getattr(current, "round", 0) or 0),
            int(getattr(current, "position", 0) or 0),
            int(getattr(current, "id", 0) or 0),
        ),
    ):
        aka_id = getattr(match, "aka_id", None) or -1
        aka_team_id = getattr(match, "aka_team_id", None) or -1
        ao_id = getattr(match, "ao_id", None) or -1
        ao_team_id = getattr(match, "ao_team_id", None) or -1
        tatami_id = getattr(match, "tatami_id", None) or -1
        referee_id = getattr(match, "referee_id", None) or -1

        aka_name = athlete_names.get(aka_id) or team_names.get(aka_team_id)
        ao_name = athlete_names.get(ao_id) or team_names.get(ao_team_id)
        payloads.append(
            {
                "id": int(getattr(match, "id", 0) or 0),
                "round": int(getattr(match, "round", 0) or 0),
                "position": int(getattr(match, "position", 0) or 0),
                "status": str(getattr(match, "status", "PENDING") or "PENDING"),
                "match_type": str(
                    getattr(match, "match_type", "ELIMINATION") or "ELIMINATION"
                ),
                "aka_name": aka_name,
                "ao_name": ao_name,
                "tatami_name": tatami_names.get(tatami_id),
                "referee_name": referee_names.get(referee_id),
                "live_match_href": (
                    f"/competition/kumite/match/{int(getattr(match, 'id', 0) or 0)}"
                    if str(getattr(match, "status", "PENDING") or "PENDING")
                    == "PENDING"
                    else None
                ),
            }
        )

    return [_to_display_match(payload) for payload in payloads]
