"""Guards for legacy main competition cleanup."""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOTS = (
    REPO_ROOT / "kakumi_app",
    REPO_ROOT / "tests",
)
FORBIDDEN_IMPORT_SNIPPETS = (
    "kakumi_app.services.bracket_service",
    "kakumi_app.services.penalty_service",
    "kakumi_app.services.scoring_service",
    "kakumi_app.services.tie_breaking_service",
)
FORBIDDEN_ARTIFACTS = (
    REPO_ROOT / "kakumi_app/services/bracket_service.py",
    REPO_ROOT / "kakumi_app/services/penalty_service.py",
    REPO_ROOT / "kakumi_app/services/scoring_service.py",
    REPO_ROOT / "kakumi_app/services/tie_breaking_service.py",
    REPO_ROOT / "create_db.py",
    REPO_ROOT / "SPECS_UPDATE_PROPOSAL.md",
)


def _iter_python_files() -> list[Path]:
    files: list[Path] = []
    for root in RUNTIME_ROOTS:
        files.extend(sorted(root.rglob("*.py")))
    current_test_file = Path(__file__).resolve()
    return [path for path in files if path.resolve() != current_test_file]


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_runtime_imports_do_not_reference_removed_legacy_services() -> None:
    offenders: list[str] = []
    for file_path in _iter_python_files():
        content = file_path.read_text(encoding="utf-8")
        if any(snippet in content for snippet in FORBIDDEN_IMPORT_SNIPPETS):
            offenders.append(_relative(file_path))

    assert offenders == []


def test_runtime_and_tests_do_not_depend_on_create_db_script() -> None:
    offenders: list[str] = []
    for file_path in _iter_python_files():
        content = file_path.read_text(encoding="utf-8")
        if "create_db.py" in content or "create_db" in content:
            offenders.append(_relative(file_path))

    assert offenders == []


def test_legacy_artifacts_removed_from_runtime_tree() -> None:
    existing = [_relative(path) for path in FORBIDDEN_ARTIFACTS if path.exists()]
    assert existing == []


def test_active_runtime_and_services_remain_importable() -> None:
    import kakumi_app.kakumi_app  # noqa: F401
    import kakumi_app.services.kata_scoring_service  # noqa: F401
    import kakumi_app.services.kumite_scoring_service  # noqa: F401


def test_migration_76ed8bac3e8b_has_duplicate_downgrade_note_only() -> None:
    migration_path = (
        REPO_ROOT
        / "alembic/versions/76ed8bac3e8b_add_tournament_fields_and_status_enum.py"
    )
    content = migration_path.read_text(encoding="utf-8")

    assert "# BUG: duplicate downgrade" in content
    assert content.count("def downgrade()") == 2
