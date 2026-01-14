"""Single operation benchmarks."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tools.base import BrowserTool, BenchmarkResult


# Test URLs
TEST_URLS = {
    "simple": "https://example.com",
    "quotes": "https://quotes.toscrape.com/",
    "form": "https://the-internet.herokuapp.com/login",
    "dynamic": "https://the-internet.herokuapp.com/dynamic_loading/1",
}


@dataclass
class OperationSummary:
    """Statistical summary of an operation."""
    tool: str
    operation: str
    test_case: str
    count: int
    success_rate: float
    mean_ms: float
    median_ms: float
    std_dev_ms: float
    min_ms: float
    max_ms: float
    p95_ms: float
    p99_ms: float
    cold_start_ms: float | None
    warm_mean_ms: float


def _percentile(data: list[float], p: float) -> float:
    """Calculate percentile."""
    if not data:
        return 0.0
    sorted_data = sorted(data)
    k = (len(sorted_data) - 1) * p / 100
    f = int(k)
    c = f + 1 if f < len(sorted_data) - 1 else f
    return sorted_data[f] + (k - f) * (sorted_data[c] - sorted_data[f])


def _compute_summary(results: list[BenchmarkResult]) -> OperationSummary:
    """Compute statistical summary from results."""
    if not results:
        return OperationSummary(
            tool="unknown",
            operation="unknown",
            test_case="unknown",
            count=0,
            success_rate=0.0,
            mean_ms=0.0,
            median_ms=0.0,
            std_dev_ms=0.0,
            min_ms=0.0,
            max_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
            cold_start_ms=None,
            warm_mean_ms=0.0,
        )

    successful = [r for r in results if r.success]
    latencies = [r.latency_ms for r in successful]
    cold_latencies = [r.latency_ms for r in successful if r.is_cold_start]
    warm_latencies = [r.latency_ms for r in successful if not r.is_cold_start]

    return OperationSummary(
        tool=results[0].tool,
        operation=results[0].operation,
        test_case=results[0].test_case,
        count=len(results),
        success_rate=len(successful) / len(results) if results else 0.0,
        mean_ms=statistics.mean(latencies) if latencies else 0.0,
        median_ms=statistics.median(latencies) if latencies else 0.0,
        std_dev_ms=statistics.stdev(latencies) if len(latencies) > 1 else 0.0,
        min_ms=min(latencies) if latencies else 0.0,
        max_ms=max(latencies) if latencies else 0.0,
        p95_ms=_percentile(latencies, 95),
        p99_ms=_percentile(latencies, 99),
        cold_start_ms=cold_latencies[0] if cold_latencies else None,
        warm_mean_ms=statistics.mean(warm_latencies) if warm_latencies else 0.0,
    )


def benchmark_navigate(
    tool: BrowserTool,
    iterations: int,
    warmup: int,
) -> list[BenchmarkResult]:
    """Benchmark navigation operation."""
    results = []
    url = TEST_URLS["simple"]

    print(f"  [{tool.name}] Navigate ({url})")

    # Warmup
    for i in range(warmup):
        tool.navigate(url, test_case="warmup", iteration=i)

    # Benchmark
    for i in range(iterations):
        result = tool.navigate(url, test_case="navigate_simple", iteration=i)
        results.append(result)
        status = "" if result.success else ""
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.1f}ms")

    return results


def benchmark_snapshot(
    tool: BrowserTool,
    iterations: int,
    warmup: int,
) -> list[BenchmarkResult]:
    """Benchmark ARIA snapshot operation."""
    results = []
    url = TEST_URLS["quotes"]

    print(f"  [{tool.name}] Snapshot ({url})")

    # Navigate first
    nav_result = tool.navigate(url, test_case="snapshot_setup", iteration=0)
    if not nav_result.success:
        print(f"    Navigation failed: {nav_result.error}")
        return results

    # Warmup
    for i in range(warmup):
        tool.snapshot(test_case="warmup", iteration=i)

    # Benchmark
    for i in range(iterations):
        result = tool.snapshot(test_case="snapshot_quotes", iteration=i)
        results.append(result)
        status = "" if result.success else ""
        tokens = result.token_estimate or 0
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.1f}ms (~{tokens} tokens)")

    return results


def benchmark_screenshot(
    tool: BrowserTool,
    iterations: int,
    warmup: int,
) -> list[BenchmarkResult]:
    """Benchmark screenshot operation."""
    results = []
    url = TEST_URLS["simple"]
    output_dir = Path("/tmp/fgp-benchmark-screenshots")
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"  [{tool.name}] Screenshot ({url})")

    # Navigate first
    nav_result = tool.navigate(url, test_case="screenshot_setup", iteration=0)
    if not nav_result.success:
        print(f"    Navigation failed: {nav_result.error}")
        return results

    # Warmup
    for i in range(warmup):
        tool.screenshot(str(output_dir / f"warmup_{i}.png"), test_case="warmup", iteration=i)

    # Benchmark
    for i in range(iterations):
        output_path = str(output_dir / f"{tool.name}_{i}.png")
        result = tool.screenshot(output_path, test_case="screenshot_simple", iteration=i)
        results.append(result)
        status = "" if result.success else ""
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.1f}ms")

    return results


def benchmark_click(
    tool: BrowserTool,
    iterations: int,
    warmup: int,
) -> list[BenchmarkResult]:
    """Benchmark click operation."""
    results = []
    url = TEST_URLS["form"]

    print(f"  [{tool.name}] Click ({url})")

    # Navigate first
    nav_result = tool.navigate(url, test_case="click_setup", iteration=0)
    if not nav_result.success:
        print(f"    Navigation failed: {nav_result.error}")
        return results

    # Warmup
    for i in range(warmup):
        tool.click("input#username", test_case="warmup", iteration=i)

    # Benchmark
    for i in range(iterations):
        result = tool.click("input#username", test_case="click_input", iteration=i)
        results.append(result)
        status = "" if result.success else ""
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.1f}ms")

    return results


def benchmark_fill(
    tool: BrowserTool,
    iterations: int,
    warmup: int,
) -> list[BenchmarkResult]:
    """Benchmark fill operation."""
    results = []
    url = TEST_URLS["form"]

    print(f"  [{tool.name}] Fill ({url})")

    # Navigate first
    nav_result = tool.navigate(url, test_case="fill_setup", iteration=0)
    if not nav_result.success:
        print(f"    Navigation failed: {nav_result.error}")
        return results

    # Warmup
    for i in range(warmup):
        tool.fill("input#username", "testuser", test_case="warmup", iteration=i)

    # Benchmark
    for i in range(iterations):
        result = tool.fill("input#username", f"testuser{i}", test_case="fill_input", iteration=i)
        results.append(result)
        status = "" if result.success else ""
        print(f"    [{i+1}/{iterations}] {status} {result.latency_ms:.1f}ms")

    return results


def run_single_ops_benchmark(
    tools: list[BrowserTool],
    config: Any,
) -> dict:
    """Run all single operation benchmarks."""
    results = {
        "operations": ["navigate", "snapshot", "screenshot", "click", "fill"],
        "raw_results": [],
        "summaries": {},
    }

    iterations = config.min_iterations
    warmup = config.warmup_iterations

    for tool in tools:
        print(f"\n[{tool.name}]")
        print("-" * 40)

        # Navigation
        nav_results = benchmark_navigate(tool, iterations, warmup)
        results["raw_results"].extend([r.__dict__ for r in nav_results])
        results["summaries"][f"{tool.name}_navigate"] = _compute_summary(nav_results).__dict__

        # Snapshot
        snap_results = benchmark_snapshot(tool, iterations, warmup)
        results["raw_results"].extend([r.__dict__ for r in snap_results])
        results["summaries"][f"{tool.name}_snapshot"] = _compute_summary(snap_results).__dict__

        # Screenshot
        ss_results = benchmark_screenshot(tool, iterations, warmup)
        results["raw_results"].extend([r.__dict__ for r in ss_results])
        results["summaries"][f"{tool.name}_screenshot"] = _compute_summary(ss_results).__dict__

        # Click
        click_results = benchmark_click(tool, iterations, warmup)
        results["raw_results"].extend([r.__dict__ for r in click_results])
        results["summaries"][f"{tool.name}_click"] = _compute_summary(click_results).__dict__

        # Fill
        fill_results = benchmark_fill(tool, iterations, warmup)
        results["raw_results"].extend([r.__dict__ for r in fill_results])
        results["summaries"][f"{tool.name}_fill"] = _compute_summary(fill_results).__dict__

    # Create comparison table
    comparison = {}
    for op in results["operations"]:
        comparison[op] = {}
        for tool in tools:
            key = f"{tool.name}_{op}"
            if key in results["summaries"]:
                summary = results["summaries"][key]
                comparison[op][tool.name] = {
                    "mean_ms": round(summary["mean_ms"], 1),
                    "median_ms": round(summary["median_ms"], 1),
                    "p95_ms": round(summary["p95_ms"], 1),
                    "success_rate": round(summary["success_rate"] * 100, 1),
                }

    results["comparison"] = comparison

    return results
