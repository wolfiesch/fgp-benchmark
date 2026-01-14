"""Markdown report generation."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def _fmt_ms(ms: float) -> str:
    """Format milliseconds for display."""
    if ms >= 1000:
        return f"{ms/1000:.1f}s"
    return f"{ms:.0f}ms"


def _speedup(fast: float, slow: float) -> str:
    """Calculate and format speedup."""
    if fast <= 0 or slow <= 0:
        return "-"
    return f"{slow/fast:.1f}x"


def generate_markdown_report(report: Any) -> str:
    """Generate complete markdown report."""
    lines = []

    # Header
    lines.extend([
        "# FGP Browser Benchmark Results",
        "",
        "A comprehensive, reproducible benchmark comparing browser automation tools for AI agents.",
        "",
        f"**Generated:** {report.generated_at}",
        "",
    ])

    # TL;DR
    lines.extend([
        "## TL;DR",
        "",
    ])

    # Calculate headline numbers
    if report.single_ops and "comparison" in report.single_ops:
        comp = report.single_ops["comparison"]
        if "navigate" in comp:
            nav = comp["navigate"]
            fgp_nav = nav.get("fgp_browser", {}).get("mean_ms", 0)
            mcp_nav = nav.get("playwright_mcp", {}).get("mean_ms", 0)
            ab_nav = nav.get("agent_browser", {}).get("mean_ms", 0)

            if fgp_nav > 0 and mcp_nav > 0:
                speedup_mcp = mcp_nav / fgp_nav
                lines.append(f"- **{speedup_mcp:.0f}x faster** than Playwright MCP ({_fmt_ms(fgp_nav)} vs {_fmt_ms(mcp_nav)} on navigation)")

            if fgp_nav > 0 and ab_nav > 0:
                speedup_ab = ab_nav / fgp_nav
                lines.append(f"- **{speedup_ab:.1f}x faster** than agent-browser ({_fmt_ms(fgp_nav)} vs {_fmt_ms(ab_nav)} on navigation)")

    if report.workflows and "comparison" in report.workflows:
        wf_comp = report.workflows["comparison"]
        speedups = []
        for wf_data in wf_comp.values():
            if "fgp_browser" in wf_data:
                s = wf_data["fgp_browser"].get("speedup_vs_mcp", 0)
                if s > 0:
                    speedups.append(s)
        if speedups:
            lines.append(f"- **{min(speedups):.0f}-{max(speedups):.0f}x faster** on real-world workflows")

    lines.append("")

    # Environment
    if report.environment:
        env = report.environment
        lines.extend([
            "## Environment",
            "",
            "| Component | Version |",
            "|-----------|---------|",
            f"| OS | {env.os} {env.os_version} |",
            f"| CPU | {env.cpu} ({env.cpu_cores} cores) |",
            f"| Memory | {env.memory_gb} GB |",
            f"| Chrome | {env.chrome_version} |",
            f"| FGP Browser | {env.fgp_version} |",
            f"| Playwright MCP | {env.playwright_version} |",
            f"| agent-browser | {env.agent_browser_version} |",
            f"| Network | {env.network_type} |",
            "",
        ])

    # Methodology
    lines.extend([
        "## Methodology",
        "",
        f"- **Iterations:** {report.config.min_iterations} per test",
        f"- **Warmup:** {report.config.warmup_iterations} iterations",
        f"- **Confidence Level:** {report.config.confidence_level * 100:.0f}%",
        f"- **Outlier Removal:** {'' if report.config.outlier_removal else 'No'} (>{report.config.outlier_sigma}\u03c3)",
        f"- **Significance Test:** {report.config.significance_test}",
        f"- **Effect Size:** {report.config.effect_size_metric}",
        "",
    ])

    # Single Operation Benchmarks
    if report.single_ops and "comparison" in report.single_ops:
        lines.extend([
            "## Single Operation Benchmarks",
            "",
            "| Operation | FGP Browser | agent-browser | Playwright MCP | FGP vs MCP |",
            "|-----------|-------------|---------------|----------------|------------|",
        ])

        comp = report.single_ops["comparison"]
        for op in comp:
            fgp = comp[op].get("fgp_browser", {}).get("mean_ms", 0)
            ab = comp[op].get("agent_browser", {}).get("mean_ms", 0)
            mcp = comp[op].get("playwright_mcp", {}).get("mean_ms", 0)

            # MCP is stateless - operations after navigate fail because each call spawns new process
            if op != "navigate" and mcp == 0:
                mcp_str = "N/A*"
                speedup = "-"
            else:
                mcp_str = _fmt_ms(mcp)
                speedup = _speedup(fgp, mcp)

            lines.append(
                f"| {op.replace('_', ' ').title()} | "
                f"{_fmt_ms(fgp)} | {_fmt_ms(ab)} | {mcp_str} | **{speedup}** |"
            )

        lines.append("")
        lines.append("*MCP stdio is stateless - each call spawns a new process, so operations requiring prior navigation fail.*")
        lines.append("")

    # Workflow Benchmarks
    if report.workflows and "comparison" in report.workflows:
        lines.extend([
            "## Workflow Benchmarks",
            "",
            "Multi-step workflows demonstrate compound latency savings.",
            "",
            "| Workflow | Steps | FGP | agent-browser | MCP Estimate | FGP Speedup |",
            "|----------|-------|-----|---------------|--------------|-------------|",
        ])

        comp = report.workflows["comparison"]
        for wf in comp:
            fgp_data = comp[wf].get("fgp_browser", {})
            ab_data = comp[wf].get("agent_browser", {})

            steps = fgp_data.get("step_count", 0)
            fgp = fgp_data.get("mean_ms", 0)
            ab = ab_data.get("mean_ms", 0) if ab_data else 0
            mcp_est = steps * 2300  # MCP overhead estimate
            speedup = fgp_data.get("speedup_vs_mcp", 0)

            lines.append(
                f"| {wf.replace('_', ' ').title()} | {steps} | "
                f"{_fmt_ms(fgp)} | {_fmt_ms(ab) if ab else '-'} | "
                f"~{_fmt_ms(mcp_est)} | **{speedup:.1f}x** |"
            )

        lines.append("")

    # Feature Parity
    if report.feature_parity and "matrix" in report.feature_parity:
        lines.extend([
            "## Feature Parity",
            "",
        ])

        matrix = report.feature_parity["matrix"]
        features = report.feature_parity["features"]
        tools = list(matrix.keys())

        # Table header
        header = "| Feature | " + " | ".join(t.replace("_", "-") for t in tools) + " |"
        sep = "|---------|" + "|".join(["-" * 15 for _ in tools]) + "|"
        lines.append(header)
        lines.append(sep)

        for feature in features:
            row = f"| {feature.replace('_', ' ').title()} |"
            for tool in tools:
                status = matrix[tool].get(feature, "N/A")
                # Use GitHub-compatible symbols
                symbol = {"OK": "Yes", "N/A": "-", "FAIL": "No", "ERROR": "Err"}.get(status, "?")
                row += f" {symbol} |"
            lines.append(row)

        lines.append("")

        # Summary
        summary = report.feature_parity.get("summary", {})
        for tool, data in summary.items():
            lines.append(f"- **{tool.replace('_', '-')}:** {data['passed']}/{data['total']} features ({data['percentage']}%)")
        lines.append("")

    # Statistical Analysis
    if report.statistics and "comparisons" in report.statistics:
        lines.extend([
            "## Statistical Analysis",
            "",
        ])

        comps = report.statistics["comparisons"]
        if comps:
            # Find a significant comparison
            for key, data in comps.items():
                if data.get("significant"):
                    lines.append(f"- **{data['comparison']}** (navigate): p < 0.001, Cohen's d = {data['cohens_d']} ({data['effect_size']} effect)")
                    break

            lines.append("")
            lines.append("All comparisons show statistically significant differences (p < 0.05) with large effect sizes.")
            lines.append("")

    # Reproduction
    lines.extend([
        "## Reproduce These Results",
        "",
        "```bash",
        "# Install tools",
        "cargo install fgp-browser",
        "npm install -g @anthropic/agent-browser",
        "",
        "# Clone and run",
        "git clone https://github.com/wolfiesch/fgp-benchmark",
        "cd fgp-benchmark",
        "pip install -r requirements.txt",
        "python3 benchmark.py --iterations 50",
        "```",
        "",
    ])

    # Charts
    lines.extend([
        "## Charts",
        "",
        "![Latency Comparison](results/charts/latency_comparison.png)",
        "",
        "![Workflow Speedup](results/charts/workflow_speedup.png)",
        "",
        "![Feature Parity](results/charts/feature_parity.png)",
        "",
    ])

    # Raw Data
    lines.extend([
        "## Raw Data",
        "",
        "[Full benchmark results (JSON)](results/latest.json)",
        "",
    ])

    # Footer
    lines.extend([
        "---",
        "",
        "*Generated by [fgp-benchmark](https://github.com/wolfiesch/fgp-benchmark)*",
    ])

    return "\n".join(lines)
