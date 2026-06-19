"""Tests for static matplotlib charts."""
import matplotlib
matplotlib.use("Agg")

from tcfd_extractor.visualization.static_charts import build_module_graph_svg


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