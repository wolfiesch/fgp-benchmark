"""Browser tool wrappers for benchmarking."""

from .base import BrowserTool, BenchmarkResult
from .fgp import FGPBrowserTool
from .agent_browser import AgentBrowserTool
from .playwright_mcp import PlaywrightMCPTool

__all__ = [
    "BrowserTool",
    "BenchmarkResult",
    "FGPBrowserTool",
    "AgentBrowserTool",
    "PlaywrightMCPTool",
]
