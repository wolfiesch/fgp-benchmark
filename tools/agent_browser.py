"""agent-browser (Vercel) tool wrapper."""

from __future__ import annotations

import subprocess
import time
from shutil import which

from .base import BrowserTool, BenchmarkResult, estimate_tokens


class AgentBrowserTool(BrowserTool):
    """Vercel agent-browser CLI wrapper.

    This is the Vercel agent-browser package - a Playwright-based browser
    automation tool optimized for AI agents.
    """

    def __init__(self):
        self._cold_start = True
        self._cli_path = which("agent-browser")
        self._process = None

    @property
    def name(self) -> str:
        return "agent_browser"

    def is_available(self) -> bool:
        return self._cli_path is not None

    def start(self) -> bool:
        """Start agent-browser (it's already daemon-based)."""
        if not self._cli_path:
            return False
        self._cold_start = True
        return True

    def stop(self) -> None:
        """Stop agent-browser."""
        if self._cli_path:
            try:
                subprocess.run(
                    [self._cli_path, "close"],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass
        self._cold_start = True

    def _run_command(
        self,
        args: list[str],
        operation: str,
        test_case: str = "default",
        iteration: int = 0,
    ) -> BenchmarkResult:
        """Run agent-browser CLI command."""
        if not self.is_available():
            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                error="agent-browser CLI not installed",
            )

        start = time.perf_counter()
        try:
            proc = subprocess.run(
                [self._cli_path] + args,
                capture_output=True,
                timeout=60,
                text=True,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            is_cold = self._cold_start
            self._cold_start = False

            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=elapsed_ms,
                success=proc.returncode == 0,
                is_cold_start=is_cold,
                payload_size=len(proc.stdout) if proc.stdout else 0,
                token_estimate=estimate_tokens(proc.stdout or ""),
                error=proc.stderr[:500] if proc.returncode != 0 else None,
            )
        except subprocess.TimeoutExpired:
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
        return self._run_command(["open", url], "navigate", test_case, iteration)

    def snapshot(self, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["snapshot"], "snapshot", test_case, iteration)

    def screenshot(self, path: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["screenshot", path], "screenshot", test_case, iteration)

    def click(self, selector: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["click", selector], "click", test_case, iteration)

    def fill(self, selector: str, value: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["fill", selector, value], "fill", test_case, iteration)

    def select(self, selector: str, value: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        # agent-browser may use different command
        return self._run_command(["select", selector, value], "select", test_case, iteration)

    def check(self, selector: str, checked: bool = True, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        # agent-browser check command
        return self._run_command(["check", selector], "check", test_case, iteration)

    def hover(self, selector: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["hover", selector], "hover", test_case, iteration)

    def scroll(self, selector: str | None = None, x: int = 0, y: int = 0, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        if selector:
            return self._run_command(["scroll", selector], "scroll", test_case, iteration)
        else:
            # Scroll by amount
            return self._run_command(["scroll", f"0,{y}"], "scroll", test_case, iteration)

    def press(self, key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["press", key], "press", test_case, iteration)

    def press_combo(self, modifiers: list[str], key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        # Format: Ctrl+a
        combo = "+".join(modifiers + [key])
        return self._run_command(["press", combo], "press_combo", test_case, iteration)

    def upload(self, selector: str, file_path: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["upload", selector, file_path], "upload", test_case, iteration)

    def close(self) -> None:
        self.stop()
