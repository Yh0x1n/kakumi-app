"""Tests for bracket grouping utilities."""

from kakumi_app.utils.bracket_utils import (
    _resolve_live_match_href,
    build_match_cards,
    group_matches_by_round,
)


def test_group_matches_by_round_returns_empty_list_for_empty_input() -> None:
    """Empty inputs should produce an empty grouped result."""
    assert group_matches_by_round([]) == []


def test_group_matches_by_round_groups_sorts_and_resolves_bye_tbd() -> None:
    """Matches should group by round, sort by position, and resolve fallback labels."""
    grouped = group_matches_by_round(
        [
            {
                "id": 30,
                "round": 2,
                "position": 1,
                "status": "PENDING",
                "match_type": "ELIMINATION",
                "aka_name": None,
                "ao_name": None,
                "tatami_name": None,
                "referee_name": None,
            },
            {
                "id": 11,
                "round": 1,
                "position": 2,
                "status": "READY",
                "match_type": "ELIMINATION",
                "aka_name": "Ana",
                "ao_name": None,
                "tatami_name": "Tatami 2",
                "referee_name": None,
            },
            {
                "id": 10,
                "round": 1,
                "position": 1,
                "status": "PENDING",
                "match_type": "ELIMINATION",
                "aka_name": "Carlos",
                "ao_name": "Lucía",
                "tatami_name": "Tatami 1",
                "referee_name": "Ref Uno",
            },
        ]
    )

    assert [round_group["round"] for round_group in grouped] == [1, 2]
    assert [match["position"] for match in grouped[0]["matches"]] == [1, 2]
    assert grouped[0]["matches"][1]["ao_label"] == "BYE"
    assert grouped[1]["matches"][0]["aka_label"] == "TBD"
    assert grouped[1]["matches"][0]["ao_label"] == "TBD"


def test_group_matches_by_round_preserves_display_fields_and_none_assignments() -> None:
    """Grouped matches should keep render-ready fields without coercing None labels."""
    grouped = group_matches_by_round(
        [
            {
                "id": 77,
                "round": 3,
                "position": 4,
                "status": "COMPLETED",
                "match_type": "FINAL",
                "aka_name": "Equipo Aka",
                "ao_name": "Equipo Ao",
                "tatami_name": None,
                "referee_name": None,
            }
        ]
    )

    assert grouped == [
        {
            "round": 3,
            "matches": [
                {
                    "id": 77,
                    "round": 3,
                    "position": 4,
                    "status": "COMPLETED",
                    "match_type": "FINAL",
                    "aka_label": "Equipo Aka",
                    "ao_label": "Equipo Ao",
                    "tatami_label": None,
                    "referee_label": None,
                    "live_match_href": None,
                }
            ],
        }
    ]


def test_resolve_live_match_href_chooses_kata_path_for_kata_modality() -> None:
    class _Category:
        modality = "KATA_INDIVIDUAL"

    class _Match:
        id = 42
        status = "PENDING"
        category = _Category()

    assert _resolve_live_match_href(_Match()) == "/competition/match/42/kata"


def test_resolve_live_match_href_chooses_kumite_path_for_other_modalities() -> None:
    class _Category:
        modality = "KUMITE_INDIVIDUAL"

    class _Match:
        id = 77
        status = "PENDING"
        category = _Category()

    assert _resolve_live_match_href(_Match()) == "/competition/match/77/kumite"


def test_build_match_cards_uses_category_modality_mapping_for_live_route() -> None:
    class _Match:
        id = 9
        round = 1
        position = 1
        status = "PENDING"
        match_type = "ELIMINATION"
        aka_id = None
        aka_team_id = None
        ao_id = None
        ao_team_id = None
        tatami_id = None
        referee_id = None
        category_id = 77

    cards = build_match_cards(
        [_Match()],
        athlete_names={},
        team_names={},
        tatami_names={},
        referee_names={},
        category_modalities={77: "KATA_TEAM"},
    )

    assert cards[0]["live_match_href"] == "/competition/match/9/kata"
