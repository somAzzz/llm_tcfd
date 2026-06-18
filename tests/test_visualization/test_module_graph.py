"""Tests for AST-based module dependency discovery."""
import textwrap
from pathlib import Path

from tcfd_extractor.visualization.module_graph import discover_module_graph


def _write_module(tmp_path: Path, name: str, source: str) -> Path:
    p = tmp_path / f"{name}.py"
    p.write_text(textwrap.dedent(source), encoding="utf-8")
    return p


class TestDiscoverModuleGraph:
    def test_finds_simple_imports(self, tmp_path):
        _write_module(tmp_path, "a", "from . import b")
        _write_module(tmp_path, "b", "")
        graph = discover_module_graph(tmp_path)
        assert "a" in graph
        assert "b" in graph["a"]
        assert graph["b"] == []

    def test_finds_relative_imports(self, tmp_path):
        _write_module(tmp_path, "a", "from .b import foo")
        _write_module(tmp_path, "b", "")
        graph = discover_module_graph(tmp_path)
        assert graph["a"] == ["b"]

    def test_empty_directory(self, tmp_path):
        graph = discover_module_graph(tmp_path)
        assert graph == {}

    def test_skips_init_file(self, tmp_path):
        _write_module(tmp_path, "__init__", "from . import a, b")
        _write_module(tmp_path, "a", "")
        _write_module(tmp_path, "b", "")
        graph = discover_module_graph(tmp_path)
        assert "__init__" not in graph
        assert graph["a"] == []
        assert graph["b"] == []

    def test_ignores_third_party_imports(self, tmp_path):
        _write_module(tmp_path, "a", "import json\nimport pandas\nfrom . import b")
        _write_module(tmp_path, "b", "")
        graph = discover_module_graph(tmp_path)
        assert "json" not in graph["a"]
        assert "pandas" not in graph["a"]
        assert "b" in graph["a"]
