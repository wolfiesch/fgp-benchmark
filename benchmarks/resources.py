"""Resource usage benchmarks - memory, CPU monitoring."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Any

from tools.base import BrowserTool


@dataclass
class ResourceSample:
    """Single resource usage sample."""
    timestamp: float
    cpu_percent: float
    memory_mb: float
    threads: int


@dataclass
class ResourceSummary:
    """Summary of resource usage over a period."""
    tool: str
    samples: int
    peak_memory_mb: float
    avg_memory_mb: float
    peak_cpu_percent: float
    avg_cpu_percent: float
    thread_count: int


def _get_process_stats(pid: int) -> tuple[float, float, int] | None:
    """Get CPU%, memory MB, thread count for a process."""
    try:
        # Use ps on macOS/Linux
        result = subprocess.run(
            ["ps", "-p", str(pid), "-o", "%cpu,%mem,rss,nlwp"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return None

        parts = lines[1].split()
        if len(parts) < 3:
            return None

        cpu_percent = float(parts[0])
        memory_kb = int(parts[2])
        memory_mb = memory_kb / 1024
        threads = int(parts[3]) if len(parts) > 3 else 1

        return cpu_percent, memory_mb, threads
    except Exception:
        return None


def monitor_resource_usage(
    tool: BrowserTool,
    duration_seconds: float = 10,
    sample_interval: float = 0.5,
) -> ResourceSummary:
    """Monitor resource usage while tool performs operations."""
    samples = []
    pid = tool.get_pid()

    if pid is None:
        return ResourceSummary(
            tool=tool.name,
            samples=0,
            peak_memory_mb=0,
            avg_memory_mb=0,
            peak_cpu_percent=0,
            avg_cpu_percent=0,
            thread_count=0,
        )

    end_time = time.time() + duration_seconds

    while time.time() < end_time:
        stats = _get_process_stats(pid)
        if stats:
            cpu, memory, threads = stats
            samples.append(ResourceSample(
                timestamp=time.time(),
                cpu_percent=cpu,
                memory_mb=memory,
                threads=threads,
            ))
        time.sleep(sample_interval)

    if not samples:
        return ResourceSummary(
            tool=tool.name,
            samples=0,
            peak_memory_mb=0,
            avg_memory_mb=0,
            peak_cpu_percent=0,
            avg_cpu_percent=0,
            thread_count=0,
        )

    return ResourceSummary(
        tool=tool.name,
        samples=len(samples),
        peak_memory_mb=max(s.memory_mb for s in samples),
        avg_memory_mb=sum(s.memory_mb for s in samples) / len(samples),
        peak_cpu_percent=max(s.cpu_percent for s in samples),
        avg_cpu_percent=sum(s.cpu_percent for s in samples) / len(samples),
        thread_count=samples[-1].threads,
    )


def run_resource_benchmark(tools: list[BrowserTool]) -> dict:
    """Run resource usage benchmarks."""
    results = {
        "summaries": {},
    }

    for tool in tools:
        print(f"  [{tool.name}] Monitoring resources...")

        # Start tool if needed
        tool.start()
        time.sleep(1)

        # Perform some operations while monitoring
        pid = tool.get_pid()
        if pid:
            # Do some work
            tool.navigate("https://example.com")
            summary = monitor_resource_usage(tool, duration_seconds=5)

            # Do more work
            tool.navigate("https://quotes.toscrape.com/")
            tool.snapshot()
            summary2 = monitor_resource_usage(tool, duration_seconds=5)

            # Combine summaries
            results["summaries"][tool.name] = {
                "peak_memory_mb": max(summary.peak_memory_mb, summary2.peak_memory_mb),
                "avg_memory_mb": (summary.avg_memory_mb + summary2.avg_memory_mb) / 2,
                "peak_cpu_percent": max(summary.peak_cpu_percent, summary2.peak_cpu_percent),
                "avg_cpu_percent": (summary.avg_cpu_percent + summary2.avg_cpu_percent) / 2,
                "thread_count": summary2.thread_count,
                "samples": summary.samples + summary2.samples,
            }

            print(f"    Memory: {results['summaries'][tool.name]['peak_memory_mb']:.1f} MB peak")
            print(f"    CPU: {results['summaries'][tool.name]['avg_cpu_percent']:.1f}% avg")
        else:
            print(f"    [SKIP] Cannot get PID for {tool.name}")
            results["summaries"][tool.name] = {
                "peak_memory_mb": 0,
                "avg_memory_mb": 0,
                "peak_cpu_percent": 0,
                "avg_cpu_percent": 0,
                "thread_count": 0,
                "samples": 0,
                "note": "Could not get process ID",
            }

    return results
