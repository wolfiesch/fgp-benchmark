"""Statistical analysis for benchmark results."""

from __future__ import annotations

import math
import statistics
from typing import Any


def mann_whitney_u(sample1: list[float], sample2: list[float]) -> tuple[float, float]:
    """
    Mann-Whitney U test (Wilcoxon rank-sum test).

    Returns (U statistic, approximate p-value).

    This is a non-parametric test that doesn't assume normal distribution.
    """
    if not sample1 or not sample2:
        return 0.0, 1.0

    n1 = len(sample1)
    n2 = len(sample2)

    # Combine and rank
    combined = [(v, 1, i) for i, v in enumerate(sample1)] + [(v, 2, i) for i, v in enumerate(sample2)]
    combined.sort(key=lambda x: x[0])

    # Assign ranks (handle ties by averaging)
    ranks = []
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + 1 + j) / 2
        for k in range(i, j):
            ranks.append(avg_rank)
        i = j

    # Sum ranks for sample 1
    rank1_sum = sum(ranks[i] for i, (_, group, _) in enumerate(combined) if group == 1)

    # Calculate U
    u1 = rank1_sum - n1 * (n1 + 1) / 2
    u2 = n1 * n2 - u1

    # Use smaller U
    u = min(u1, u2)

    # Approximate p-value using normal approximation
    mean_u = n1 * n2 / 2
    std_u = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)

    if std_u == 0:
        return u, 1.0

    z = (u - mean_u) / std_u

    # Two-tailed p-value approximation
    p_value = 2 * (1 - _normal_cdf(abs(z)))

    return u, p_value


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def cohens_d(sample1: list[float], sample2: list[float]) -> float:
    """
    Cohen's d effect size.

    Interpretation:
    - < 0.2: negligible
    - 0.2-0.5: small
    - 0.5-0.8: medium
    - > 0.8: large
    """
    if not sample1 or not sample2:
        return 0.0

    mean1 = statistics.mean(sample1)
    mean2 = statistics.mean(sample2)

    var1 = statistics.variance(sample1) if len(sample1) > 1 else 0
    var2 = statistics.variance(sample2) if len(sample2) > 1 else 0

    n1 = len(sample1)
    n2 = len(sample2)

    # Pooled standard deviation
    pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
    pooled_std = math.sqrt(pooled_var)

    if pooled_std == 0:
        return 0.0

    return (mean1 - mean2) / pooled_std


def compute_confidence_interval(
    data: list[float],
    confidence: float = 0.95,
) -> tuple[float, float]:
    """Compute confidence interval for mean."""
    if not data:
        return 0.0, 0.0

    n = len(data)
    mean = statistics.mean(data)

    if n < 2:
        return mean, mean

    std_err = statistics.stdev(data) / math.sqrt(n)

    # Z-score for confidence level (approximate)
    z_scores = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}
    z = z_scores.get(confidence, 1.96)

    margin = z * std_err
    return mean - margin, mean + margin


def remove_outliers(data: list[float], sigma: float = 3.0) -> list[float]:
    """Remove outliers beyond sigma standard deviations."""
    if len(data) < 3:
        return data

    mean = statistics.mean(data)
    std = statistics.stdev(data)

    if std == 0:
        return data

    return [x for x in data if abs(x - mean) <= sigma * std]


def run_significance_tests(
    results_a: list[float],
    results_b: list[float],
    tool_a: str,
    tool_b: str,
) -> dict:
    """Run statistical significance tests between two tools."""
    u, p_value = mann_whitney_u(results_a, results_b)
    d = cohens_d(results_a, results_b)

    ci_a = compute_confidence_interval(results_a)
    ci_b = compute_confidence_interval(results_b)

    return {
        "comparison": f"{tool_a} vs {tool_b}",
        "mann_whitney_u": round(u, 2),
        "p_value": round(p_value, 6),
        "significant": p_value < 0.05,
        "cohens_d": round(d, 3),
        "effect_size": _interpret_effect_size(d),
        f"{tool_a}_mean": round(statistics.mean(results_a), 1) if results_a else 0,
        f"{tool_b}_mean": round(statistics.mean(results_b), 1) if results_b else 0,
        f"{tool_a}_ci_95": [round(ci_a[0], 1), round(ci_a[1], 1)],
        f"{tool_b}_ci_95": [round(ci_b[0], 1), round(ci_b[1], 1)],
    }


def _interpret_effect_size(d: float) -> str:
    """Interpret Cohen's d effect size."""
    d = abs(d)
    if d < 0.2:
        return "negligible"
    elif d < 0.5:
        return "small"
    elif d < 0.8:
        return "medium"
    else:
        return "large"


def compute_statistics(report: Any, config: Any) -> dict:
    """Compute overall statistics for benchmark report."""
    stats = {
        "methodology": {
            "iterations": config.min_iterations,
            "warmup": config.warmup_iterations,
            "confidence_level": config.confidence_level,
            "outlier_removal": config.outlier_removal,
            "outlier_sigma": config.outlier_sigma,
            "significance_test": config.significance_test,
            "effect_size_metric": config.effect_size_metric,
        },
        "comparisons": {},
    }

    # Extract latency data from single_ops
    if report.single_ops and "raw_results" in report.single_ops:
        raw = report.single_ops["raw_results"]

        # Group by tool and operation
        by_tool_op: dict[str, list[float]] = {}
        for r in raw:
            if r.get("success"):
                key = f"{r['tool']}_{r['operation']}"
                if key not in by_tool_op:
                    by_tool_op[key] = []
                by_tool_op[key].append(r["latency_ms"])

        # Find all tools and operations
        tools = list(set(r["tool"] for r in raw))
        operations = list(set(r["operation"] for r in raw))

        # Run pairwise comparisons
        for op in operations:
            for i, tool_a in enumerate(tools):
                for tool_b in tools[i+1:]:
                    key_a = f"{tool_a}_{op}"
                    key_b = f"{tool_b}_{op}"

                    if key_a in by_tool_op and key_b in by_tool_op:
                        data_a = by_tool_op[key_a]
                        data_b = by_tool_op[key_b]

                        comparison_key = f"{op}_{tool_a}_vs_{tool_b}"
                        stats["comparisons"][comparison_key] = run_significance_tests(
                            data_a, data_b, tool_a, tool_b
                        )

    return stats
