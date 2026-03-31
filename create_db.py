"""
Script to recreate database tables.
"""

import reflex as rx
from kakumi_app.models import *  # noqa
from sqlalchemy import create_engine

# Create engine for kakumi.db
engine = create_engine("sqlite:///kakumi.db", echo=True)

# Create all tables
rx.Model.metadata.create_all(engine)
print("Database tables created.")
