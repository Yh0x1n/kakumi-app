"""
KAKUMI
Módulo de tablas para registros de atletas, categorías y árbitros.
"""

#Importaciones
import reflex as rx
import sqlmodel as sm
from models import Athlete, Category, Referee

def athletes_table() -> rx.Component:
    return rx.table()