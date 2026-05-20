"""Standards cleanup checks for archived batch-4 change."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read_ast(relative_path: str) -> tuple[ast.Module, Path]:
    """Parse Python file into AST and return tree plus path."""
    file_path = PROJECT_ROOT / relative_path
    source = file_path.read_text(encoding="utf-8")
    return ast.parse(source), file_path


def _class_methods(
    tree: ast.Module,
    class_name: str,
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return mapping of method names for given class AST node."""
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {
                fn.name: fn
                for fn in node.body
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
            }
    raise AssertionError(f"Class {class_name} not found")


def test_state_methods_have_explicit_return_annotations() -> None:
    """Touched state methods must keep explicit return annotations."""
    files = {
        "kakumi_app/states/athlete_state.py": "AthleteState",
        "kakumi_app/states/referee_state.py": "RefereeState",
        "kakumi_app/states/team_state.py": "TeamState",
    }

    missing: list[str] = []
    for relative_path, class_name in files.items():
        tree, _ = _read_ast(relative_path)
        methods = _class_methods(tree, class_name)
        for method_name, method_node in methods.items():
            if method_name.startswith("__"):
                continue
            if method_node.returns is None:
                missing.append(f"{relative_path}:{class_name}.{method_name}")

    assert missing == []


def test_athlete_helper_validators_have_docstrings() -> None:
    """Athlete helper validators should carry docstrings."""
    tree, _ = _read_ast("kakumi_app/states/athlete_state.py")
    methods = _class_methods(tree, "AthleteState")

    expected_helpers = [
        "_validate_name",
        "_validate_age",
        "_validate_gender",
        "_validate_weight",
        "_validate_belt_rank",
    ]

    missing_docstrings = [
        helper
        for helper in expected_helpers
        if ast.get_docstring(methods[helper]) is None
    ]

    assert missing_docstrings == []


def test_migration_lines_stay_within_88_chars() -> None:
    """Migration file should respect Black-compatible line length."""
    migration_path = PROJECT_ROOT / "alembic/versions/1a9f9cf5faa1_.py"
    long_lines = []

    for idx, line in enumerate(
        migration_path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        if len(line) > 88:
            long_lines.append((idx, len(line)))

    assert long_lines == []
