#!/usr/bin/env python3
"""
FGP Browser Benchmark Suite

A comprehensive, reproducible benchmark suite comparing browser automation tools:
- FGP Browser (Fast Gateway Protocol)
- agent-browser (Vercel)
- Playwright MCP (Microsoft)

Usage:
    python3 benchmark.py                          # Run all benchmarks
    python3 benchmark.py --iterations 50          # Custom iteration count
    python3 benchmark.py --suite single_ops       # Run specific suite
    python3 benchmark.py --quick                  # Quick validation run

CHANGELOG (recent first, max 5 entries)
01/14/2026 - Initial implementation for public benchmark suite (Claude)
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Import benchmark modules
from benchmarks.single_ops import run_single_ops_benchmark
from benchmarks.workflows import run_workflow_benchmark
from benchmarks.resources import run_resource_benchmark
from benchmarks.concurrency import run_concurrency_benchmark
from benchmarks.feature_parity import run_feature_parity_test
from benchmarks.statistics import compute_statistics, run_significance_tests
from tools import FGPBrowserTool, AgentBrowserTool, PlaywrightMCPTool
from visualization import generate_all_charts
from report import generate_markdown_report


@dataclass
class EnvironmentSpec:
    """Complete environment specification for reproducibility."""
    os: str
    os_version: str
    cpu: str
    cpu_cores: int
    memory_gb: int
    chrome_version: str
    node_version: str
    rust_version: str
    python_version: str
    fgp_version: str
    playwright_version: str
    agent_browser_version: str
    network_type: str
    timestamp: str

    @classmethod
    def capture(cls) -> "EnvironmentSpec":
        """Capture current environment specifications."""
        def run_cmd(cmd: list[str]) -> str:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return result.stdout.strip() if result.returncode == 0 else "unknown"
            except Exception:
                return "unknown"

        # Get Chrome version
        chrome_version = run_cmd(
            ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"]
        ).replace("Google Chrome ", "")

        # Get Node version
        node_version = run_cmd(["node", "--version"]).lstrip("v")

        # Get Rust version
        rust_version = run_cmd(["rustc", "--version"]).replace("rustc ", "").split()[0]

        # Get FGP version from Cargo.toml
        fgp_version = "0.1.0"  # From published crate
        try:
            cargo_toml = Path.home() / "projects" / "fgp" / "browser" / "Cargo.toml"
            if cargo_toml.exists():
                for line in cargo_toml.read_text().split("\n"):
                    if line.startswith("version"):
                        fgp_version = line.split("=")[1].strip().strip('"')
                        break
        except Exception:
            pass

        # Get playwright version
        playwright_version = run_cmd(["npx", "@playwright/mcp@latest", "--version"])
        if not playwright_version or playwright_version == "unknown":
            playwright_version = "latest"

        # Get agent-browser version
        agent_browser_version = run_cmd(["agent-browser", "--version"])
        if not agent_browser_version or agent_browser_version == "unknown":
            agent_browser_version = "latest"

        return cls(
            os=platform.system(),
            os_version=platform.release(),
            cpu=platform.processor() or "unknown",
            cpu_cores=subprocess.os.cpu_count() or 0,
            memory_gb=_get_memory_gb(),
            chrome_version=chrome_version,
            node_version=node_version,
            rust_version=rust_version,
            python_version=platform.python_version(),
            fgp_version=fgp_version,
            playwright_version=playwright_version,
            agent_browser_version=agent_browser_version,
            network_type="Local (no throttling)",
            timestamp=datetime.now().isoformat(),
        )


def _get_memory_gb() -> int:
    """Get system memory in GB."""
    try:
        if platform.system() == "Darwin":
            result = subprocess.run(
                ["sysctl", "-n", "hw.memsize"],
                capture_output=True, text=True
            )
            return int(result.stdout.strip()) // (1024**3)
        return 0
    except Exception:
        return 0


@dataclass
class BenchmarkConfig:
    """Benchmark configuration with statistical requirements."""
    min_iterations: int = 50
    warmup_iterations: int = 5
    confidence_level: float = 0.95
    outlier_removal: bool = True
    outlier_sigma: float = 3.0
    significance_test: str = "mann-whitney-u"
    effect_size_metric: str = "cohens-d"


@dataclass
class BenchmarkReport:
    """Complete benchmark report."""
    version: str = "1.0.0"
    generated_at: str = ""
    environment: EnvironmentSpec | None = None
    config: BenchmarkConfig = field(default_factory=BenchmarkConfig)
    single_ops: dict = field(default_factory=dict)
    workflows: dict = field(default_factory=dict)
    resources: dict = field(default_factory=dict)
    concurrency: dict = field(default_factory=dict)
    feature_parity: dict = field(default_factory=dict)
    statistics: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)


def run_all_benchmarks(
    config: BenchmarkConfig,
    suites: list[str] | None = None,
) -> BenchmarkReport:
    """Run all benchmark suites."""
    report = BenchmarkReport(
        generated_at=datetime.now().isoformat(),
        config=config,
    )

    # Capture environment
    print("Capturing environment specifications...")
    report.environment = EnvironmentSpec.capture()
    print(f"  OS: {report.environment.os} {report.environment.os_version}")
    print(f"  CPU: {report.environment.cpu} ({report.environment.cpu_cores} cores)")
    print(f"  Memory: {report.environment.memory_gb} GB")
    print(f"  Chrome: {report.environment.chrome_version}")
    print()

    # Initialize tools
    print("Initializing browser tools...")
    tools = []

    fgp = FGPBrowserTool()
    if fgp.is_available():
        tools.append(fgp)
        print(f"  [OK] FGP Browser v{report.environment.fgp_version}")
    else:
        print("  [SKIP] FGP Browser not available")

    agent_browser = AgentBrowserTool()
    if agent_browser.is_available():
        tools.append(agent_browser)
        print(f"  [OK] agent-browser")
    else:
        print("  [SKIP] agent-browser not available")

    playwright = PlaywrightMCPTool()
    if playwright.is_available():
        tools.append(playwright)
        print(f"  [OK] Playwright MCP")
    else:
        print("  [SKIP] Playwright MCP not available")

    print()

    if not tools:
        print("ERROR: No browser tools available")
        return report

    # Run benchmark suites
    suites_to_run = suites or ["single_ops", "workflows", "resources", "concurrency", "feature_parity"]

    if "single_ops" in suites_to_run:
        print("=" * 60)
        print("SINGLE OPERATION BENCHMARKS")
        print("=" * 60)
        report.single_ops = run_single_ops_benchmark(tools, config)
        print()

    if "workflows" in suites_to_run:
        print("=" * 60)
        print("WORKFLOW BENCHMARKS")
        print("=" * 60)
        report.workflows = run_workflow_benchmark(tools, config)
        print()

    if "resources" in suites_to_run:
        print("=" * 60)
        print("RESOURCE USAGE BENCHMARKS")
        print("=" * 60)
        report.resources = run_resource_benchmark(tools)
        print()

    if "concurrency" in suites_to_run:
        print("=" * 60)
        print("CONCURRENCY BENCHMARKS")
        print("=" * 60)
        report.concurrency = run_concurrency_benchmark(tools)
        print()

    if "feature_parity" in suites_to_run:
        print("=" * 60)
        print("FEATURE PARITY TEST")
        print("=" * 60)
        report.feature_parity = run_feature_parity_test(tools)
        print()

    # Compute statistics
    print("=" * 60)
    print("STATISTICAL ANALYSIS")
    print("=" * 60)
    report.statistics = compute_statistics(report, config)
    print()

    # Cleanup tools
    for tool in tools:
        tool.close()

    return report


def main():
    parser = argparse.ArgumentParser(
        description="FGP Browser Benchmark Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 benchmark.py                          # Full benchmark (50 iterations)
    python3 benchmark.py --quick                  # Quick validation (5 iterations)
    python3 benchmark.py --iterations 100         # Custom iteration count
    python3 benchmark.py --suite single_ops       # Run specific suite
    python3 benchmark.py --suite workflows        # Run workflow benchmarks only
        """
    )
    parser.add_argument(
        "--iterations", "-i",
        type=int,
        default=50,
        help="Number of iterations per test (default: 50)"
    )
    parser.add_argument(
        "--warmup", "-w",
        type=int,
        default=5,
        help="Number of warmup iterations (default: 5)"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick run with 5 iterations (for validation)"
    )
    parser.add_argument(
        "--suite", "-s",
        choices=["single_ops", "workflows", "resources", "concurrency", "feature_parity", "all"],
        default="all",
        help="Which benchmark suite to run"
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output JSON file path"
    )
    parser.add_argument(
        "--no-charts",
        action="store_true",
        help="Skip chart generation"
    )
    args = parser.parse_args()

    # Configure
    config = BenchmarkConfig(
        min_iterations=5 if args.quick else args.iterations,
        warmup_iterations=1 if args.quick else args.warmup,
    )

    suites = None if args.suite == "all" else [args.suite]

    print()
    print("=" * 60)
    print("FGP BROWSER BENCHMARK SUITE")
    print("=" * 60)
    print(f"Iterations: {config.min_iterations}")
    print(f"Warmup: {config.warmup_iterations}")
    print(f"Suites: {suites or 'all'}")
    print()

    # Run benchmarks
    report = run_all_benchmarks(config, suites)

    # Generate charts
    if not args.no_charts and report.single_ops:
        print("Generating charts...")
        chart_paths = generate_all_charts(report)
        for path in chart_paths:
            print(f"  Generated: {path}")
        print()

    # Generate markdown report
    print("Generating report...")
    markdown = generate_markdown_report(report)
    readme_path = Path(__file__).parent / "README.md"
    readme_path.write_text(markdown)
    print(f"  Generated: {readme_path}")

    # Save JSON results
    results_dir = Path(__file__).parent / "results"
    results_dir.mkdir(exist_ok=True)

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = results_dir / f"benchmark_{timestamp}.json"

    # Convert report to dict
    report_dict = {
        "version": report.version,
        "generated_at": report.generated_at,
        "environment": asdict(report.environment) if report.environment else None,
        "config": asdict(report.config),
        "single_ops": report.single_ops,
        "workflows": report.workflows,
        "resources": report.resources,
        "concurrency": report.concurrency,
        "feature_parity": report.feature_parity,
        "statistics": report.statistics,
    }

    with open(output_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=str)
    print(f"  Saved: {output_path}")

    # Also save as latest.json
    latest_path = results_dir / "latest.json"
    with open(latest_path, "w") as f:
        json.dump(report_dict, f, indent=2, default=str)
    print(f"  Saved: {latest_path}")

    print()
    print("=" * 60)
    print("BENCHMARK COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
