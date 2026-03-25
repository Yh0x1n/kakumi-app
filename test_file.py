import reflex as rx
from sqlmodel import select

from kakumi_app.models.tournament_model import Tournament


def test_database_flow():
    with rx.session() as session:
        query = select(Tournament)
        results = session.exec(query).first()

        if results:
            print(
                f"Categorías del torneo: {results.name}\n{
                    '\n'.join([str(cat.name) for cat in results.kata_categories])
                }"
            )


def test_database_flow_delete():
    with rx.session() as session:
        query = session.exec(select(Tournament)).all()
        for result in query:
            session.delete(result)
        session.commit()


test_database_flow()
