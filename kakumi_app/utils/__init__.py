"""Utility helpers for competition UI slices."""

from .bracket_utils import (
    BracketCategoryData,
    BracketRoundData,
    CompetitionCategoryData,
    MatchCardData,
    TournamentBracketData,
    build_match_cards,
    group_matches_by_round,
)

BELT_RANKS = [
    "Blanco",
    "Celeste",
    "Amarillo",
    "Naranja",
    "Verde",
    "Azul",
    "Morado",
    "Marrón",
    "Negro",
]
BELT_RANK_ORDER = {name: idx for idx, name in enumerate(BELT_RANKS)}

__all__ = [
    "BELT_RANKS",
    "BELT_RANK_ORDER",
    "BracketCategoryData",
    "BracketRoundData",
    "CompetitionCategoryData",
    "MatchCardData",
    "TournamentBracketData",
    "build_match_cards",
    "group_matches_by_round",
]
