"""Base class for browser tool wrappers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token)."""
    return len(text) // 4


@dataclass
class BenchmarkResult:
    """Result of a single benchmark operation."""
    tool: str
    operation: str
    test_case: str
    iteration: int
    latency_ms: float
    success: bool
    is_cold_start: bool = False
    payload_size: int = 0
    token_estimate: int = 0
    error: str | None = None
    metadata: dict = field(default_factory=dict)


class BrowserTool(ABC):
    """Abstract base class for browser automation tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if tool is installed and available."""
        pass

    @abstractmethod
    def start(self) -> bool:
        """Start the browser/daemon. Returns True if successful."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Stop the browser/daemon."""
        pass

    @abstractmethod
    def navigate(self, url: str, **kwargs) -> BenchmarkResult:
        """Navigate to URL."""
        pass

    @abstractmethod
    def snapshot(self, **kwargs) -> BenchmarkResult:
        """Get ARIA accessibility tree snapshot."""
        pass

    @abstractmethod
    def screenshot(self, path: str, **kwargs) -> BenchmarkResult:
        """Capture screenshot to file."""
        pass

    @abstractmethod
    def click(self, selector: str, **kwargs) -> BenchmarkResult:
        """Click element by selector."""
        pass

    @abstractmethod
    def fill(self, selector: str, value: str, **kwargs) -> BenchmarkResult:
        """Fill input field."""
        pass

    @abstractmethod
    def select(self, selector: str, value: str, **kwargs) -> BenchmarkResult:
        """Select dropdown option."""
        pass

    @abstractmethod
    def check(self, selector: str, checked: bool = True, **kwargs) -> BenchmarkResult:
        """Check/uncheck checkbox."""
        pass

    @abstractmethod
    def hover(self, selector: str, **kwargs) -> BenchmarkResult:
        """Hover over element."""
        pass

    @abstractmethod
    def scroll(self, selector: str | None = None, x: int = 0, y: int = 0, **kwargs) -> BenchmarkResult:
        """Scroll to element or by amount."""
        pass

    @abstractmethod
    def press(self, key: str, **kwargs) -> BenchmarkResult:
        """Press keyboard key."""
        pass

    @abstractmethod
    def press_combo(self, modifiers: list[str], key: str, **kwargs) -> BenchmarkResult:
        """Press key with modifiers (Ctrl, Shift, Alt, Meta)."""
        pass

    @abstractmethod
    def upload(self, selector: str, file_path: str, **kwargs) -> BenchmarkResult:
        """Upload file to file input."""
        pass

    def close(self) -> None:
        """Cleanup resources."""
        pass

    def get_pid(self) -> int | None:
        """Get process ID for resource monitoring."""
        return None
