"""Guard: the runtime package stays dependency-free (CLAUDE.md hard constraint).

discord.py is an *optional* extra, lazy-imported inside command handlers. These
tests fail if someone adds a runtime dependency or a top-level third-party import
to the package.
"""

from __future__ import annotations

import ast
import sys
import tomllib
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_PKG = _REPO_ROOT / "discord_bot_cli"

# Modules importable from the standard library / this package only.
_STDLIB = set(sys.stdlib_module_names)
_FIRST_PARTY = {"discord_bot_cli"}


def test_pyproject_runtime_dependencies_empty() -> None:
    data = tomllib.loads((_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["dependencies"] == []
    # discord.py is only an optional extra (and a dev tool), never a runtime dep.
    extras = data["project"]["optional-dependencies"]
    assert any("discord.py" in dep for dep in extras["discord"])


def _top_level_imports(path: Path) -> set[str]:
    """Root package names imported at module top level (not inside functions)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    roots: set[str] = set()
    for node in tree.body:  # module top level only — nested defs are lazy imports
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def test_no_top_level_third_party_imports() -> None:
    offenders: dict[str, set[str]] = {}
    for py in _PKG.rglob("*.py"):
        third_party = {
            root
            for root in _top_level_imports(py)
            if root not in _STDLIB and root not in _FIRST_PARTY
        }
        if third_party:
            offenders[str(py.relative_to(_REPO_ROOT))] = third_party
    assert not offenders, f"top-level third-party imports found: {offenders}"
