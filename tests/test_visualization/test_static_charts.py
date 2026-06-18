"""Tests for static matplotlib charts."""
import base64

import matplotlib
matplotlib.use("Agg")

from tcfd_extractor.visualization.static_charts import (
    build_refactor_bar,
    build_module_graph_svg,
)


class TestBuildRefactorBar:
    def test_returns_base64_string(self):
        b64 = build_refactor_bar(
            god_class_lines_before=468,
            god_class_lines_after=79,
            total_module_lines=1004,
            module_count=10,
            test_count_before=16,
            test_count_after=165,
        )
        assert isinstance(b64, str)
        assert len(b64) > 100

    def test_decodes_to_png(self):
        b64 = build_refactor_bar(468, 79, 1004, 10, 16, 165)
        decoded = base64.b64decode(b64)
        assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


class TestBuildModuleGraphSvg:
    def test_returns_svg_string(self):
        modules = {
            "config": ["evaluator"],
            "evaluator": ["models", "prompts", "exceptions"],
            "models": [],
            "prompts": [],
            "exceptions": [],
        }
        svg = build_module_graph_svg(modules)
        assert isinstance(svg, str)
        assert "<svg" in svg or "<?xml" in svg

    def test_includes_all_module_labels(self):
        modules = {
            "config": ["evaluator"],
            "evaluator": ["models"],
            "models": [],
        }
        svg = build_module_graph_svg(modules)
        assert "config" in svg
        assert "evaluator" in svg
        assert "models" in svg
