"""Feature parity tests - verify all tools support required features."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from tools.base import BrowserTool


# Feature test configurations
FEATURE_TESTS = {
    "navigate": {
        "setup": None,
        "test": lambda tool: tool.navigate("https://example.com"),
        "expected": "page loads",
    },
    "snapshot": {
        "setup": lambda tool: tool.navigate("https://example.com"),
        "test": lambda tool: tool.snapshot(),
        "expected": "ARIA tree returned",
    },
    "screenshot": {
        "setup": lambda tool: tool.navigate("https://example.com"),
        "test": lambda tool: tool.screenshot("/tmp/feature_test_screenshot.png"),
        "expected": "PNG file created",
    },
    "click": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/checkboxes"),
        "test": lambda tool: tool.click("input[type='checkbox']"),
        "expected": "element clicked",
    },
    "fill": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/login"),
        "test": lambda tool: tool.fill("input#username", "testuser"),
        "expected": "input filled",
    },
    "select": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/dropdown"),
        "test": lambda tool: tool.select("select#dropdown", "1"),
        "expected": "option selected",
    },
    "check": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/checkboxes"),
        "test": lambda tool: tool.check("input[type='checkbox']"),
        "expected": "checkbox checked",
    },
    "hover": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/hovers"),
        "test": lambda tool: tool.hover("div.figure"),
        "expected": "element hovered",
    },
    "scroll": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/infinite_scroll"),
        "test": lambda tool: tool.scroll(y=500),
        "expected": "page scrolled",
    },
    "press": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/key_presses"),
        "test": lambda tool: tool.press("Enter"),
        "expected": "key pressed",
    },
    "press_combo": {
        "setup": lambda tool: tool.navigate("https://the-internet.herokuapp.com/inputs"),
        "test": lambda tool: (
            tool.fill("input[type='number']", "12345"),
            tool.press_combo(["Control"], "a"),
        )[-1],  # Return last result
        "expected": "text selected",
    },
    "upload": {
        "setup": lambda tool: _setup_upload_test(tool),
        "test": lambda tool: tool.upload("input#file-upload", "/tmp/test_upload.txt"),
        "expected": "file uploaded",
    },
}


def _setup_upload_test(tool: BrowserTool) -> None:
    """Setup for upload test - create test file and navigate."""
    # Create test file
    test_file = Path("/tmp/test_upload.txt")
    test_file.write_text("This is a test file for upload benchmark.")

    # Navigate to upload page
    tool.navigate("https://the-internet.herokuapp.com/upload")


def run_feature_parity_test(tools: list[BrowserTool]) -> dict:
    """Run feature parity tests on all tools."""
    results = {
        "features": list(FEATURE_TESTS.keys()),
        "matrix": {},
        "details": {},
    }

    for tool in tools:
        print(f"  [{tool.name}]")
        results["matrix"][tool.name] = {}
        results["details"][tool.name] = {}

        for feature_name, config in FEATURE_TESTS.items():
            print(f"    {feature_name}...", end=" ")

            try:
                # Run setup if needed
                if config["setup"]:
                    config["setup"](tool)
                    time.sleep(0.3)

                # Run test
                result = config["test"](tool)

                if result.success:
                    results["matrix"][tool.name][feature_name] = "OK"
                    print("OK")
                else:
                    results["matrix"][tool.name][feature_name] = "FAIL"
                    results["details"][tool.name][feature_name] = result.error
                    print(f"FAIL: {result.error}")

            except NotImplementedError:
                results["matrix"][tool.name][feature_name] = "N/A"
                print("N/A (not implemented)")
            except Exception as e:
                results["matrix"][tool.name][feature_name] = "ERROR"
                results["details"][tool.name][feature_name] = str(e)[:200]
                print(f"ERROR: {str(e)[:50]}")

            time.sleep(0.5)

    # Compute summary
    results["summary"] = {}
    for tool in tools:
        passed = sum(1 for v in results["matrix"][tool.name].values() if v == "OK")
        total = len(FEATURE_TESTS)
        results["summary"][tool.name] = {
            "passed": passed,
            "total": total,
            "percentage": round(passed / total * 100, 1),
        }

    return results
