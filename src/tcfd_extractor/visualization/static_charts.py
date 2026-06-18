"""Static matplotlib charts for the HR report."""
from __future__ import annotations

import base64
import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

matplotlib.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei", "SimHei", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False


def build_refactor_bar(
    god_class_lines_before: int,
    god_class_lines_after: int,
    total_module_lines: int,
    module_count: int,
    test_count_before: int,
    test_count_after: int,
) -> str:
    """Build a before/after horizontal bar chart. Returns base64 PNG."""
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))

    ax = axes[0]
    bars = ax.barh(
        ["Before\n(refactor)", "After\n(refactor)"],
        [god_class_lines_before, god_class_lines_after],
        color=["#d62728", "#2ca02c"],
    )
    ax.set_title(f"God-Class Lines: {god_class_lines_before} → {god_class_lines_after}", fontsize=12)
    ax.set_xlabel("Lines of Code")
    ax.invert_yaxis()
    for bar, value in zip(bars, [god_class_lines_before, god_class_lines_after]):
        ax.text(value + 10, bar.get_y() + bar.get_height() / 2, str(value), va="center")

    ax = axes[1]
    bars = ax.barh(
        ["Before\n(refactor)", "After\n(refactor)"],
        [test_count_before, test_count_after],
        color=["#d62728", "#2ca02c"],
    )
    ax.set_title(f"Test Count: {test_count_before} → {test_count_after}", fontsize=12)
    ax.set_xlabel("Tests Passing")
    ax.invert_yaxis()
    for bar, value in zip(bars, [test_count_before, test_count_after]):
        ax.text(value + 1, bar.get_y() + bar.get_height() / 2, str(value), va="center")

    fig.suptitle(
        f"Engineering Refactor: 1 God-Class → {module_count} Focused Modules ({total_module_lines} lines total)",
        fontsize=13,
        fontweight="bold",
    )
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


def build_module_graph_svg(modules: dict[str, list[str]]) -> str:
    """Build a directed graph of module dependencies. Returns SVG string."""
    G = nx.DiGraph()
    for mod, deps in modules.items():
        G.add_node(mod)
        for dep in deps:
            G.add_edge(mod, dep)

    try:
        pos = nx.nx_agraph.graphviz_layout(G, prog="dot")
    except (ImportError, AttributeError):
        try:
            pos = nx.spring_layout(G, k=2, seed=42)
        except Exception:
            pos = {n: (i, 0) for i, n in enumerate(G.nodes())}

    fig, ax = plt.subplots(figsize=(10, 8))
    nx.draw_networkx_nodes(
        G, pos, ax=ax, node_color="#1f77b4", node_size=2000, alpha=0.8
    )
    nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_color="white")
    nx.draw_networkx_edges(
        G, pos, ax=ax, edge_color="#666", arrows=True, arrowsize=15, width=1.0
    )
    ax.set_title("Module Dependency Graph (Tech Deep Dive)", fontsize=12, fontweight="bold")
    ax.axis("off")
    fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="svg", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read().decode("utf-8")
