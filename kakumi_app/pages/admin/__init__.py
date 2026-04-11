"""
Admin pages package.
"""

from .athletes_page import athletes, new_athlete
from .referees_page import referees, new_referee
from .teams_page import teams, new_team
from .import_page import import_athletes as import_athletes_page
from .export_page import export_results

__all__ = [
    "athletes",
    "new_athlete",
    "referees",
    "new_referee",
    "teams",
    "new_team",
    "import_athletes_page",
    "export_results",
]
