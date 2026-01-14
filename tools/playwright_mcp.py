"""Playwright MCP tool wrapper."""

from __future__ import annotations

import json
import subprocess
import time
from shutil import which

from .base import BrowserTool, BenchmarkResult, estimate_tokens


class PlaywrightMCPTool(BrowserTool):
    """Playwright MCP (stdio) wrapper.

    This uses npx to spawn the Playwright MCP server for each operation,
    which is how Claude Code typically invokes it.

    Note: This measures the REAL-WORLD performance of MCP stdio,
    including process spawn overhead. This is intentional - it's how
    the tool is actually used.
    """

    def __init__(self):
        self._cold_start = True
        self._npx_path = which("npx")

    @property
    def name(self) -> str:
        return "playwright_mcp"

    def is_available(self) -> bool:
        return self._npx_path is not None

    def start(self) -> bool:
        """No persistent daemon for MCP stdio."""
        self._cold_start = True
        return True

    def stop(self) -> None:
        """No persistent daemon for MCP stdio."""
        self._cold_start = True

    def _call_mcp(
        self,
        tool_name: str,
        arguments: dict,
        operation: str,
        test_case: str = "default",
        iteration: int = 0,
    ) -> BenchmarkResult:
        """Call Playwright MCP tool via stdio.

        This spawns a new process for each call, which is the standard
        MCP stdio usage pattern.
        """
        if not self.is_available():
            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                error="npx not available",
            )

        # Create MCP request
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
        }

        start = time.perf_counter()
        try:
            # Spawn MCP server and send request
            proc = subprocess.Popen(
                [self._npx_path, "@playwright/mcp@latest"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Send request
            request_str = json.dumps(request) + "\n"
            stdout, stderr = proc.communicate(input=request_str, timeout=60)

            elapsed_ms = (time.perf_counter() - start) * 1000

            is_cold = self._cold_start
            self._cold_start = False

            # Parse response
            success = False
            error = None
            payload_size = 0

            if stdout:
                try:
                    # Find JSON response in output
                    for line in stdout.split("\n"):
                        if line.strip().startswith("{"):
                            response = json.loads(line)
                            if "result" in response:
                                success = True
                                payload_size = len(str(response.get("result", "")))
                            elif "error" in response:
                                error = str(response["error"])
                            break
                except json.JSONDecodeError:
                    pass

            if not success and not error:
                error = stderr[:500] if stderr else "Unknown error"

            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=elapsed_ms,
                success=success,
                is_cold_start=is_cold,
                payload_size=payload_size,
                token_estimate=estimate_tokens(stdout or ""),
                error=error,
            )

        except subprocess.TimeoutExpired:
            proc.kill()
            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=60000,
                success=False,
                error="Timeout after 60s",
            )
        except Exception as e:
            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                error=str(e)[:500],
            )

    def navigate(self, url: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_navigate", {"url": url}, "navigate", test_case, iteration)

    def snapshot(self, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_snapshot", {}, "snapshot", test_case, iteration)

    def screenshot(self, path: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_take_screenshot", {}, "screenshot", test_case, iteration)

    def click(self, selector: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_click", {"element": selector}, "click", test_case, iteration)

    def fill(self, selector: str, value: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_type", {"element": selector, "text": value}, "fill", test_case, iteration)

    def select(self, selector: str, value: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_select_option", {"element": selector, "values": [value]}, "select", test_case, iteration)

    def check(self, selector: str, checked: bool = True, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        # Playwright MCP uses click for checkboxes
        return self._call_mcp("browser_click", {"element": selector}, "check", test_case, iteration)

    def hover(self, selector: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_hover", {"element": selector}, "hover", test_case, iteration)

    def scroll(self, selector: str | None = None, x: int = 0, y: int = 0, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        if selector:
            return self._call_mcp("browser_scroll", {"element": selector}, "scroll", test_case, iteration)
        else:
            # Scroll by amount (may not be supported)
            return self._call_mcp("browser_scroll", {"x": x, "y": y}, "scroll", test_case, iteration)

    def press(self, key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_press_key", {"key": key}, "press", test_case, iteration)

    def press_combo(self, modifiers: list[str], key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        # Format modifiers for Playwright
        combo = "+".join(modifiers + [key])
        return self._call_mcp("browser_press_key", {"key": combo}, "press_combo", test_case, iteration)

    def upload(self, selector: str, file_path: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._call_mcp("browser_file_upload", {"paths": [file_path]}, "upload", test_case, iteration)

    def close(self) -> None:
        self._cold_start = True
