"""Chart and visualization generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

# Try to import matplotlib, but don't fail if not available
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


# Color scheme
COLORS = {
    "fgp_browser": "#00D26A",      # Green
    "agent_browser": "#FFA500",    # Orange
    "playwright_mcp": "#FF4444",   # Red
}

TOOL_LABELS = {
    "fgp_browser": "FGP Browser",
    "agent_browser": "agent-browser",
    "playwright_mcp": "Playwright MCP",
}


def generate_latency_chart(report: Any, output_dir: Path) -> str | None:
    """Generate bar chart comparing latencies."""
    if not HAS_MATPLOTLIB:
        print("    [SKIP] matplotlib not installed")
        return None

    if not report.single_ops or "comparison" not in report.single_ops:
        return None

    comparison = report.single_ops["comparison"]

    # Prepare data
    operations = list(comparison.keys())
    tools = list(set(
        tool for op_data in comparison.values()
        for tool in op_data.keys()
    ))

    fig, ax = plt.subplots(figsize=(12, 6))

    x = range(len(operations))
    width = 0.25
    multiplier = 0

    for tool in tools:
        latencies = []
        for op in operations:
            if tool in comparison[op]:
                latencies.append(comparison[op][tool]["mean_ms"])
            else:
                latencies.append(0)

        offset = width * multiplier
        bars = ax.bar(
            [i + offset for i in x],
            latencies,
            width,
            label=TOOL_LABELS.get(tool, tool),
            color=COLORS.get(tool, "#888888"),
        )

        # Add value labels on bars
        for bar, val in zip(bars, latencies):
            if val > 0:
                ax.annotate(
                    f'{val:.0f}',
                    xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha='center',
                    va='bottom',
                    fontsize=8,
                )

        multiplier += 1

    ax.set_ylabel('Latency (ms)')
    ax.set_title('Single Operation Latency Comparison')
    ax.set_xticks([i + width for i in x])
    ax.set_xticklabels([op.replace('_', ' ').title() for op in operations])
    ax.legend(loc='upper left')
    ax.set_yscale('log')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_path = output_dir / "latency_comparison.png"
    plt.savefig(output_path, dpi=150)
    plt.close()

    return str(output_path)


def generate_workflow_chart(report: Any, output_dir: Path) -> str | None:
    """Generate horizontal bar chart for workflow speedups."""
    if not HAS_MATPLOTLIB:
        return None

    if not report.workflows or "comparison" not in report.workflows:
        return None

    comparison = report.workflows["comparison"]

    fig, ax = plt.subplots(figsize=(10, 6))

    workflows = list(comparison.keys())
    speedups = []

    for wf in workflows:
        if "fgp_browser" in comparison[wf]:
            speedups.append(comparison[wf]["fgp_browser"].get("speedup_vs_mcp", 0))
        else:
            speedups.append(0)

    colors = ["#00D26A" if s >= 10 else "#66BB6A" for s in speedups]

    bars = ax.barh(workflows, speedups, color=colors)

    # Add value labels
    for bar, speedup in zip(bars, speedups):
        ax.annotate(
            f'{speedup:.1f}x',
            xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
            xytext=(5, 0),
            textcoords="offset points",
            ha='left',
            va='center',
            fontweight='bold',
        )

    ax.set_xlabel('Speedup vs Playwright MCP')
    ax.set_title('FGP Browser Workflow Speedup')
    ax.axvline(x=1, color='gray', linestyle='--', alpha=0.5)
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()
    output_path = output_dir / "workflow_speedup.png"
    plt.savefig(output_path, dpi=150)
    plt.close()

    return str(output_path)


def generate_feature_parity_chart(report: Any, output_dir: Path) -> str | None:
    """Generate feature parity matrix visualization."""
    if not HAS_MATPLOTLIB:
        return None

    if not report.feature_parity or "matrix" not in report.feature_parity:
        return None

    matrix = report.feature_parity["matrix"]
    features = report.feature_parity["features"]
    tools = list(matrix.keys())

    fig, ax = plt.subplots(figsize=(10, 8))

    # Create binary matrix
    data = []
    for tool in tools:
        row = []
        for feature in features:
            status = matrix[tool].get(feature, "N/A")
            if status == "OK":
                row.append(1)  # Green
            elif status == "N/A":
                row.append(0.5)  # Gray
            else:
                row.append(0)  # Red
        data.append(row)

    # Create heatmap
    from matplotlib.colors import ListedColormap
    cmap = ListedColormap(['#FF4444', '#AAAAAA', '#00D26A'])

    im = ax.imshow(data, cmap=cmap, aspect='auto', vmin=0, vmax=1)

    # Labels
    ax.set_xticks(range(len(features)))
    ax.set_xticklabels([f.replace('_', ' ').title() for f in features], rotation=45, ha='right')
    ax.set_yticks(range(len(tools)))
    ax.set_yticklabels([TOOL_LABELS.get(t, t) for t in tools])

    # Add text annotations
    for i, tool in enumerate(tools):
        for j, feature in enumerate(features):
            status = matrix[tool].get(feature, "N/A")
            symbol = {"OK": "Y", "N/A": "-", "FAIL": "N", "ERROR": "!"}.get(status, "?")
            ax.text(j, i, symbol, ha='center', va='center', fontsize=12, fontweight='bold')

    ax.set_title('Feature Parity Matrix')

    # Legend
    legend_elements = [
        mpatches.Patch(color='#00D26A', label='Supported'),
        mpatches.Patch(color='#AAAAAA', label='Not Implemented'),
        mpatches.Patch(color='#FF4444', label='Failed'),
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.02, 1))

    plt.tight_layout()
    output_path = output_dir / "feature_parity.png"
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    return str(output_path)


def generate_twitter_chart(report: Any, output_dir: Path) -> str | None:
    """Generate a single, shareable chart for Twitter."""
    if not HAS_MATPLOTLIB:
        return None

    if not report.single_ops or "comparison" not in report.single_ops:
        return None

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Latency comparison for navigate
    comparison = report.single_ops["comparison"]
    if "navigate" in comparison:
        nav_data = comparison["navigate"]
        tools = list(nav_data.keys())
        latencies = [nav_data[t]["mean_ms"] for t in tools]
        colors = [COLORS.get(t, "#888888") for t in tools]
        labels = [TOOL_LABELS.get(t, t) for t in tools]

        bars = ax1.bar(labels, latencies, color=colors)

        # Add speedup annotations
        if len(latencies) >= 2:
            max_lat = max(latencies)
            for i, (bar, lat) in enumerate(zip(bars, latencies)):
                if lat < max_lat:
                    speedup = max_lat / lat
                    ax1.annotate(
                        f'{speedup:.0f}x faster',
                        xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
                        xytext=(0, 10),
                        textcoords="offset points",
                        ha='center',
                        fontsize=12,
                        fontweight='bold',
                        color=COLORS.get(tools[i], "#000000"),
                    )

        ax1.set_ylabel('Latency (ms)', fontsize=12)
        ax1.set_title('Navigation Latency', fontsize=14, fontweight='bold')
        ax1.set_yscale('log')
        ax1.grid(True, alpha=0.3)

    # Right: Workflow speedups
    if report.workflows and "comparison" in report.workflows:
        wf_comparison = report.workflows["comparison"]
        workflows = list(wf_comparison.keys())
        speedups = []

        for wf in workflows:
            if "fgp_browser" in wf_comparison[wf]:
                speedups.append(wf_comparison[wf]["fgp_browser"].get("speedup_vs_mcp", 0))
            else:
                speedups.append(0)

        colors = ["#00D26A" for _ in speedups]
        bars = ax2.barh(
            [wf.replace('_', ' ').title() for wf in workflows],
            speedups,
            color=colors,
        )

        for bar, speedup in zip(bars, speedups):
            ax2.annotate(
                f'{speedup:.0f}x',
                xy=(bar.get_width(), bar.get_y() + bar.get_height() / 2),
                xytext=(5, 0),
                textcoords="offset points",
                ha='left',
                va='center',
                fontsize=12,
                fontweight='bold',
            )

        ax2.set_xlabel('Speedup vs MCP', fontsize=12)
        ax2.set_title('Workflow Speedup (FGP Browser)', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')

    plt.suptitle(
        'FGP Browser: 292x Faster Than Playwright MCP',
        fontsize=16,
        fontweight='bold',
        y=1.02,
    )

    plt.tight_layout()
    output_path = output_dir / "twitter_chart.png"
    plt.savefig(output_path, dpi=200, bbox_inches='tight')
    plt.close()

    return str(output_path)


def generate_all_charts(report: Any) -> list[str]:
    """Generate all charts and return paths."""
    output_dir = Path(__file__).parent / "results" / "charts"
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = []

    chart_generators = [
        generate_latency_chart,
        generate_workflow_chart,
        generate_feature_parity_chart,
        generate_twitter_chart,
    ]

    for generator in chart_generators:
        path = generator(report, output_dir)
        if path:
            paths.append(path)

    return paths
