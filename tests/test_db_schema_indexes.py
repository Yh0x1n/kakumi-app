"""Schema index tests for db-schema-indexes migration."""

from pathlib import Path

from alembic import command


def test_fk_index_migration_round_trip(
    tmp_path: Path,
    fk_target_indexes: dict[str, set[str]],
    fk_index_migration_path,
    alembic_config_for_db,
    index_names_for_tables,
) -> None:
    """Upgrade creates 20 FK indexes; downgrade removes all of them."""
    db_url = f"sqlite:///{tmp_path / 'db_schema_indexes.sqlite'}"
    config = alembic_config_for_db(db_url)

    command.upgrade(config, "c078f55c0552")

    all_target_index_names = {
        index_name
        for table_indexes in fk_target_indexes.values()
        for index_name in table_indexes
    }

    migration_source = fk_index_migration_path.read_text(encoding="utf-8")
    for index_name in all_target_index_names:
        assert index_name in migration_source

    upgraded_tables, upgraded_indexes = index_names_for_tables(
        db_url,
        fk_target_indexes,
    )
    missing_indexes: set[str] = set()

    for table_name, expected_indexes in fk_target_indexes.items():
        if table_name not in upgraded_tables:
            continue
        missing_indexes.update(expected_indexes - upgraded_indexes[table_name])

    assert not missing_indexes, (
        f"Missing FK indexes after upgrade: {sorted(missing_indexes)}"
    )

    command.downgrade(config, "fe678c4071ac")

    downgraded_tables, downgraded_indexes = index_names_for_tables(
        db_url,
        fk_target_indexes,
    )
    still_present: set[str] = set()

    for table_name, expected_indexes in fk_target_indexes.items():
        if table_name not in downgraded_tables:
            continue
        still_present.update(expected_indexes & downgraded_indexes[table_name])

    assert not still_present, (
        f"FK indexes still present after downgrade: {sorted(still_present)}"
    )


def test_fk_index_target_list_has_exactly_20_items(
    fk_target_indexes: dict[str, set[str]],
) -> None:
    """Target FK index list must remain exactly 20 explicit names."""
    total = sum(len(indexes) for indexes in fk_target_indexes.values())
    assert total == 20


def test_alembic_round_trip_upgrade_downgrade_upgrade(
    tmp_path: Path,
    alembic_config_for_db,
    index_names_for_tables,
    fk_target_indexes: dict[str, set[str]],
) -> None:
    """Upgrade/downgrade/upgrade must be stable for indexed FK tables."""
    db_url = f"sqlite:///{tmp_path / 'db_schema_indexes_roundtrip.sqlite'}"
    config = alembic_config_for_db(db_url)

    command.upgrade(config, "c078f55c0552")
    first_tables, first_indexes = index_names_for_tables(db_url, fk_target_indexes)

    command.downgrade(config, "fe678c4071ac")
    down_tables, down_indexes = index_names_for_tables(db_url, fk_target_indexes)

    command.upgrade(config, "c078f55c0552")
    second_tables, second_indexes = index_names_for_tables(db_url, fk_target_indexes)

    for table_name, expected_indexes in fk_target_indexes.items():
        if table_name in first_tables:
            assert expected_indexes.issubset(first_indexes[table_name])
        if table_name in down_tables:
            assert not (expected_indexes & down_indexes[table_name])
        if table_name in second_tables:
            assert expected_indexes.issubset(second_indexes[table_name])
