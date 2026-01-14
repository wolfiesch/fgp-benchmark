"""Concurrency benchmarks - parallel request handling."""

from __future__ import annotations

import asyncio
import concurrent.futures
import time
from dataclasses import dataclass
from typing import Any

from tools.base import BrowserTool


@dataclass
class ConcurrencyResult:
    """Result of concurrency test."""
    tool: str
    parallel_requests: int
    total_time_ms: float
    requests_per_second: float
    success_rate: float
    individual_times_ms: list[float]


CONCURRENT_URLS = [
    "https://example.com",
    "https://httpbin.org/get",
    "https://quotes.toscrape.com/",
    "https://the-internet.herokuapp.com/",
    "https://jsonplaceholder.typicode.com/",
]


def _run_single_request(tool: BrowserTool, url: str) -> tuple[bool, float]:
    """Run a single navigate request."""
    start = time.perf_counter()
    result = tool.navigate(url)
    elapsed = (time.perf_counter() - start) * 1000
    return result.success, elapsed


def test_concurrent_requests(
    tool: BrowserTool,
    parallel_count: int = 3,
) -> ConcurrencyResult:
    """Test handling of concurrent requests.

    Note: FGP supports true parallel sessions.
    Playwright MCP spawns separate processes anyway.
    agent-browser may block on concurrent requests.
    """
    urls = CONCURRENT_URLS[:parallel_count]

    # Use ThreadPoolExecutor for parallel execution
    start = time.perf_counter()
    results = []
    times = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
        futures = {
            executor.submit(_run_single_request, tool, url): url
            for url in urls
        }

        for future in concurrent.futures.as_completed(futures):
            try:
                success, elapsed = future.result(timeout=60)
                results.append(success)
                times.append(elapsed)
            except Exception:
                results.append(False)
                times.append(0)

    total_time = (time.perf_counter() - start) * 1000
    success_rate = sum(results) / len(results) if results else 0
    rps = parallel_count / (total_time / 1000) if total_time > 0 else 0

    return ConcurrencyResult(
        tool=tool.name,
        parallel_requests=parallel_count,
        total_time_ms=total_time,
        requests_per_second=rps,
        success_rate=success_rate,
        individual_times_ms=times,
    )


def run_concurrency_benchmark(tools: list[BrowserTool]) -> dict:
    """Run concurrency benchmarks."""
    results = {
        "summaries": {},
        "by_parallelism": {},
    }

    parallel_levels = [1, 2, 3, 5]

    for tool in tools:
        print(f"  [{tool.name}]")
        results["summaries"][tool.name] = {}

        for parallel_count in parallel_levels:
            print(f"    {parallel_count} parallel requests...")

            # Run test
            result = test_concurrent_requests(tool, parallel_count)

            results["summaries"][tool.name][f"parallel_{parallel_count}"] = {
                "parallel_requests": result.parallel_requests,
                "total_time_ms": round(result.total_time_ms, 1),
                "requests_per_second": round(result.requests_per_second, 2),
                "success_rate": round(result.success_rate * 100, 1),
                "individual_times_ms": [round(t, 1) for t in result.individual_times_ms],
            }

            print(f"      Total: {result.total_time_ms:.0f}ms, RPS: {result.requests_per_second:.1f}")

            # Brief pause
            time.sleep(1)

    # Build comparison
    for level in parallel_levels:
        key = f"parallel_{level}"
        results["by_parallelism"][key] = {}
        for tool in tools:
            if tool.name in results["summaries"]:
                if key in results["summaries"][tool.name]:
                    results["by_parallelism"][key][tool.name] = {
                        "rps": results["summaries"][tool.name][key]["requests_per_second"],
                        "success_rate": results["summaries"][tool.name][key]["success_rate"],
                    }

    return results
