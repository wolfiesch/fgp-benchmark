"""Workflow benchmarks - multi-step automation scenarios."""

from __future__ import annotations

import statistics
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from tools.base import BrowserTool, BenchmarkResult


@dataclass
class StepResult:
    """Result of a single workflow step."""
    step_name: str
    latency_ms: float
    success: bool
    error: str | None = None


@dataclass
class WorkflowResult:
    """Result of a complete workflow."""
    workflow_name: str
    tool: str
    iteration: int
    steps: list[StepResult] = field(default_factory=list)
    total_latency_ms: float = 0.0
    success: bool = True
    error: str | None = None

    @property
    def step_count(self) -> int:
        return len(self.steps)


def workflow_login(tool: BrowserTool, iteration: int) -> WorkflowResult:
    """
    Login Flow (5 steps):
    1. Navigate to login page
    2. Fill username
    3. Fill password
    4. Click submit
    5. Verify logged in (snapshot)
    """
    result = WorkflowResult(workflow_name="login", tool=tool.name, iteration=iteration)
    start = time.perf_counter()

    # Step 1: Navigate
    step_start = time.perf_counter()
    r = tool.navigate("https://the-internet.herokuapp.com/login", test_case="login", iteration=iteration)
    step = StepResult("navigate", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.error = f"Step 1 failed: {r.error}"
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 2: Fill username
    step_start = time.perf_counter()
    r = tool.fill("input#username", "tomsmith", test_case="login", iteration=iteration)
    step = StepResult("fill_username", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.error = f"Step 2 failed: {r.error}"
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 3: Fill password
    step_start = time.perf_counter()
    r = tool.fill("input#password", "SuperSecretPassword!", test_case="login", iteration=iteration)
    step = StepResult("fill_password", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.error = f"Step 3 failed: {r.error}"
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 4: Click submit
    step_start = time.perf_counter()
    r = tool.click("button[type='submit']", test_case="login", iteration=iteration)
    step = StepResult("click_submit", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.error = f"Step 4 failed: {r.error}"
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Wait for page load
    time.sleep(0.5)

    # Step 5: Verify login (snapshot)
    step_start = time.perf_counter()
    r = tool.snapshot(test_case="login", iteration=iteration)
    step = StepResult("verify_snapshot", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    result.total_latency_ms = (time.perf_counter() - start) * 1000
    result.success = all(s.success for s in result.steps)
    return result


def workflow_search_extract(tool: BrowserTool, iteration: int) -> WorkflowResult:
    """
    Search + Extract Flow (6 steps):
    1. Navigate to quotes page
    2. Get initial snapshot
    3. Click on author link
    4. Get author page snapshot
    5. Navigate back
    6. Get final snapshot
    """
    result = WorkflowResult(workflow_name="search_extract", tool=tool.name, iteration=iteration)
    start = time.perf_counter()

    # Step 1: Navigate
    step_start = time.perf_counter()
    r = tool.navigate("https://quotes.toscrape.com/", test_case="search", iteration=iteration)
    step = StepResult("navigate", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 2: Initial snapshot
    step_start = time.perf_counter()
    r = tool.snapshot(test_case="search", iteration=iteration)
    step = StepResult("snapshot_initial", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 3: Click author link
    step_start = time.perf_counter()
    r = tool.click("small.author + a", test_case="search", iteration=iteration)
    if not r.success:
        # Fallback: direct navigation
        r = tool.navigate("https://quotes.toscrape.com/author/Albert-Einstein/", test_case="search", iteration=iteration)
    step = StepResult("click_author", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    time.sleep(0.3)

    # Step 4: Author page snapshot
    step_start = time.perf_counter()
    r = tool.snapshot(test_case="search", iteration=iteration)
    step = StepResult("snapshot_author", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 5: Navigate back
    step_start = time.perf_counter()
    r = tool.navigate("https://quotes.toscrape.com/", test_case="search", iteration=iteration)
    step = StepResult("navigate_back", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 6: Final snapshot
    step_start = time.perf_counter()
    r = tool.snapshot(test_case="search", iteration=iteration)
    step = StepResult("snapshot_final", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    result.total_latency_ms = (time.perf_counter() - start) * 1000
    result.success = all(s.success for s in result.steps)
    return result


def workflow_form_submit(tool: BrowserTool, iteration: int) -> WorkflowResult:
    """
    Form Submission Flow (7 steps):
    1. Navigate to form
    2. Fill name
    3. Fill phone
    4. Fill email
    5. Check checkbox
    6. Fill comments
    7. Take screenshot (verify)
    """
    result = WorkflowResult(workflow_name="form_submit", tool=tool.name, iteration=iteration)
    start = time.perf_counter()

    # Step 1: Navigate
    step_start = time.perf_counter()
    r = tool.navigate("https://httpbin.org/forms/post", test_case="form", iteration=iteration)
    step = StepResult("navigate", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 2: Fill name
    step_start = time.perf_counter()
    r = tool.fill("input[name='custname']", "Test User", test_case="form", iteration=iteration)
    step = StepResult("fill_name", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 3: Fill phone
    step_start = time.perf_counter()
    r = tool.fill("input[name='custtel']", "555-1234", test_case="form", iteration=iteration)
    step = StepResult("fill_phone", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 4: Fill email
    step_start = time.perf_counter()
    r = tool.fill("input[name='custemail']", "test@example.com", test_case="form", iteration=iteration)
    step = StepResult("fill_email", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 5: Check checkbox
    step_start = time.perf_counter()
    r = tool.check("input[name='topping'][value='cheese']", test_case="form", iteration=iteration)
    step = StepResult("check_topping", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 6: Fill comments
    step_start = time.perf_counter()
    r = tool.fill("textarea[name='comments']", "This is a test order", test_case="form", iteration=iteration)
    step = StepResult("fill_comments", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Step 7: Screenshot
    step_start = time.perf_counter()
    r = tool.screenshot(f"/tmp/form_{tool.name}_{iteration}.png", test_case="form", iteration=iteration)
    step = StepResult("screenshot", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    result.total_latency_ms = (time.perf_counter() - start) * 1000
    result.success = all(s.success for s in result.steps)
    return result


def workflow_pagination(tool: BrowserTool, iteration: int, pages: int = 5) -> WorkflowResult:
    """
    Pagination Loop (2 + pages*2 steps):
    1. Navigate to paginated content
    2. Snapshot page 1
    For each additional page:
      - Click next
      - Snapshot page N
    """
    result = WorkflowResult(workflow_name="pagination", tool=tool.name, iteration=iteration)
    start = time.perf_counter()

    # Step 1: Navigate
    step_start = time.perf_counter()
    r = tool.navigate("https://quotes.toscrape.com/", test_case="pagination", iteration=iteration)
    step = StepResult("navigate", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)
    if not r.success:
        result.success = False
        result.total_latency_ms = (time.perf_counter() - start) * 1000
        return result

    # Step 2: Snapshot page 1
    step_start = time.perf_counter()
    r = tool.snapshot(test_case="pagination", iteration=iteration)
    step = StepResult("snapshot_page1", (time.perf_counter() - step_start) * 1000, r.success, r.error)
    result.steps.append(step)

    # Loop through pages
    for page_num in range(2, pages + 1):
        # Click next
        step_start = time.perf_counter()
        r = tool.click("li.next a", test_case="pagination", iteration=iteration)
        if not r.success:
            # Fallback: direct navigation
            r = tool.navigate(f"https://quotes.toscrape.com/page/{page_num}/", test_case="pagination", iteration=iteration)
        step = StepResult(f"click_next_{page_num}", (time.perf_counter() - step_start) * 1000, r.success, r.error)
        result.steps.append(step)

        time.sleep(0.2)

        # Snapshot
        step_start = time.perf_counter()
        r = tool.snapshot(test_case="pagination", iteration=iteration)
        step = StepResult(f"snapshot_page{page_num}", (time.perf_counter() - step_start) * 1000, r.success, r.error)
        result.steps.append(step)

    result.total_latency_ms = (time.perf_counter() - start) * 1000
    result.success = all(s.success for s in result.steps)
    return result


WORKFLOWS: dict[str, Callable[[BrowserTool, int], WorkflowResult]] = {
    "login": workflow_login,
    "search_extract": workflow_search_extract,
    "form_submit": workflow_form_submit,
    "pagination": workflow_pagination,
}


def run_workflow_benchmark(
    tools: list[BrowserTool],
    config: Any,
) -> dict:
    """Run all workflow benchmarks."""
    results = {
        "workflows": list(WORKFLOWS.keys()),
        "raw_results": [],
        "summaries": {},
        "comparison": {},
    }

    iterations = config.min_iterations

    # MCP overhead estimate (for comparison)
    MCP_OVERHEAD_MS = 2300

    for workflow_name, workflow_fn in WORKFLOWS.items():
        print(f"\n[Workflow: {workflow_name}]")

        for tool in tools:
            print(f"  [{tool.name}]")
            workflow_results = []

            for i in range(iterations):
                wr = workflow_fn(tool, i)
                workflow_results.append(wr)
                status = "" if wr.success else ""
                print(f"    [{i+1}/{iterations}] {status} {wr.total_latency_ms:.0f}ms ({wr.step_count} steps)")

                # Small pause between iterations
                time.sleep(0.3)

            # Compute summary
            successful = [w for w in workflow_results if w.success]
            if successful:
                latencies = [w.total_latency_ms for w in successful]
                step_count = successful[0].step_count

                summary = {
                    "tool": tool.name,
                    "workflow": workflow_name,
                    "step_count": step_count,
                    "iterations": len(workflow_results),
                    "success_rate": len(successful) / len(workflow_results),
                    "mean_ms": statistics.mean(latencies),
                    "median_ms": statistics.median(latencies),
                    "min_ms": min(latencies),
                    "max_ms": max(latencies),
                    "std_dev_ms": statistics.stdev(latencies) if len(latencies) > 1 else 0,
                    "mcp_estimate_ms": step_count * MCP_OVERHEAD_MS,
                    "speedup_vs_mcp": (step_count * MCP_OVERHEAD_MS) / statistics.mean(latencies) if latencies else 0,
                }

                results["summaries"][f"{tool.name}_{workflow_name}"] = summary

            # Store raw results
            for wr in workflow_results:
                results["raw_results"].append({
                    "workflow": wr.workflow_name,
                    "tool": wr.tool,
                    "iteration": wr.iteration,
                    "steps": [s.__dict__ for s in wr.steps],
                    "total_ms": wr.total_latency_ms,
                    "step_count": wr.step_count,
                    "success": wr.success,
                    "error": wr.error,
                })

    # Build comparison table
    for workflow_name in WORKFLOWS.keys():
        results["comparison"][workflow_name] = {}
        for tool in tools:
            key = f"{tool.name}_{workflow_name}"
            if key in results["summaries"]:
                s = results["summaries"][key]
                results["comparison"][workflow_name][tool.name] = {
                    "mean_ms": round(s["mean_ms"], 0),
                    "step_count": s["step_count"],
                    "speedup_vs_mcp": round(s["speedup_vs_mcp"], 1),
                    "success_rate": round(s["success_rate"] * 100, 1),
                }

    return results
