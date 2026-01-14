"""FGP Browser tool wrapper."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
import uuid
from pathlib import Path
from shutil import which

from .base import BrowserTool, BenchmarkResult, estimate_tokens


class FGPBrowserTool(BrowserTool):
    """FGP Browser daemon wrapper.

    Uses Unix socket for low-latency communication with warm browser.
    """

    SOCKET_PATH = Path.home() / ".fgp" / "services" / "browser" / "daemon.sock"

    def __init__(self):
        self._cold_start = True
        self._daemon_pid: int | None = None
        self._cli_path = self._find_cli()

    def _find_cli(self) -> str | None:
        """Find browser-gateway CLI."""
        # Check PATH
        cli = which("browser-gateway")
        if cli:
            return cli

        # Check FGP project directory
        fgp_cli = Path.home() / "projects" / "fgp" / "browser" / "target" / "release" / "browser-gateway"
        if fgp_cli.exists():
            return str(fgp_cli)

        return None

    @property
    def name(self) -> str:
        return "fgp_browser"

    def is_available(self) -> bool:
        return self._cli_path is not None

    def start(self) -> bool:
        """Start the FGP Browser daemon."""
        if not self._cli_path:
            return False

        # Stop any existing daemon
        self.stop()
        time.sleep(0.5)

        # Start daemon
        try:
            proc = subprocess.Popen(
                [self._cli_path, "start"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            time.sleep(2)  # Wait for daemon to start

            # Get PID from pidfile
            pidfile = Path.home() / ".fgp" / "services" / "browser" / "daemon.pid"
            if pidfile.exists():
                self._daemon_pid = int(pidfile.read_text().strip())

            return self.SOCKET_PATH.exists()
        except Exception:
            return False

    def stop(self) -> None:
        """Stop the FGP Browser daemon."""
        if self._cli_path:
            try:
                subprocess.run(
                    [self._cli_path, "stop"],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass

        # Force kill if PID known
        if self._daemon_pid:
            try:
                os.kill(self._daemon_pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            self._daemon_pid = None

        self._cold_start = True

    def _call(self, method: str, params: dict | None = None) -> tuple[dict, float]:
        """Call FGP method via Unix socket."""
        start = time.perf_counter()

        request = {
            "id": str(uuid.uuid4()),
            "v": 1,
            "method": method,
            "params": params or {},
        }

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(str(self.SOCKET_PATH))
        sock.sendall((json.dumps(request) + "\n").encode())

        response_data = b""
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in response_data:
                break

        sock.close()
        latency_ms = (time.perf_counter() - start) * 1000

        response = json.loads(response_data.decode().strip())
        if not response.get("ok"):
            raise Exception(response.get("error", {}).get("message", "Unknown error"))

        return response.get("result", {}), latency_ms

    def _run_command(
        self,
        args: list[str],
        operation: str,
        test_case: str = "default",
        iteration: int = 0,
    ) -> BenchmarkResult:
        """Run browser-gateway CLI command."""
        if not self.SOCKET_PATH.exists():
            return BenchmarkResult(
                tool=self.name,
                operation=operation,
                test_case=test_case,
                iteration=iteration,
                latency_ms=0,
                success=False,
                error="Daemon not running",
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
        return self._run_command(["select", selector, value], "select", test_case, iteration)

    def check(self, selector: str, checked: bool = True, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        args = ["check", selector]
        if not checked:
            args.append("--uncheck")
        return self._run_command(args, "check", test_case, iteration)

    def hover(self, selector: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["hover", selector], "hover", test_case, iteration)

    def scroll(self, selector: str | None = None, x: int = 0, y: int = 0, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        if selector:
            return self._run_command(["scroll", selector], "scroll", test_case, iteration)
        else:
            args = ["scroll"]
            if x:
                args.extend(["--x", str(x)])
            if y:
                args.extend(["--y", str(y)])
            return self._run_command(args, "scroll", test_case, iteration)

    def press(self, key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["press", key], "press", test_case, iteration)

    def press_combo(self, modifiers: list[str], key: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        args = ["press-combo", "--key", key]
        for mod in modifiers:
            args.extend(["--modifiers", mod])
        return self._run_command(args, "press_combo", test_case, iteration)

    def upload(self, selector: str, file_path: str, test_case: str = "default", iteration: int = 0, **kwargs) -> BenchmarkResult:
        return self._run_command(["upload", selector, file_path], "upload", test_case, iteration)

    def close(self) -> None:
        """Keep daemon running for next benchmark."""
        pass

    def get_pid(self) -> int | None:
        return self._daemon_pid
