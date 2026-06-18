"""AST-based discovery of import relationships between local modules."""
from __future__ import annotations

import ast
from pathlib import Path


def discover_module_graph(eval_dir: Path) -> dict[str, list[str]]:
    """Scan `eval_dir` for *.py files and return their local dependencies.

    Excludes `__init__.py` from both keys and dependency targets.
    Only includes LOCAL imports (relative imports starting with `.`).
    """
    if not eval_dir.exists():
        return {}

    module_names = set()
    for py_file in eval_dir.glob("*.py"):
        if py_file.stem == "__init__":
            continue
        module_names.add(py_file.stem)

    graph: dict[str, list[str]] = {}
    for py_file in sorted(eval_dir.glob("*.py")):
        if py_file.stem == "__init__":
            continue
        module_name = py_file.stem
        deps = _extract_local_dependencies(py_file, module_names)
        graph[module_name] = sorted(set(deps))

    return graph


def _extract_local_dependencies(py_file: Path, local_modules: set[str]) -> list[str]:
    """Parse a Python file and return names of local modules it imports."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    deps: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            if node.module is None:
                for alias in node.names:
                    if alias.name in local_modules:
                        deps.add(alias.name)
            else:
                full_name = node.module
                if full_name in local_modules:
                    deps.add(full_name)
                else:
                    parts = full_name.split(".")
                    for i in range(len(parts)):
                        candidate = ".".join(parts[i:])
                        if candidate in local_modules:
                            deps.add(candidate)
                            break
        elif isinstance(node, ast.Import):
            continue

    return sorted(deps)
