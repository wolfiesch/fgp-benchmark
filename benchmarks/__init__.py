"""Benchmark modules."""

from .single_ops import run_single_ops_benchmark
from .workflows import run_workflow_benchmark
from .resources import run_resource_benchmark
from .concurrency import run_concurrency_benchmark
from .feature_parity import run_feature_parity_test
from .statistics import compute_statistics, run_significance_tests

__all__ = [
    "run_single_ops_benchmark",
    "run_workflow_benchmark",
    "run_resource_benchmark",
    "run_concurrency_benchmark",
    "run_feature_parity_test",
    "compute_statistics",
    "run_significance_tests",
]
