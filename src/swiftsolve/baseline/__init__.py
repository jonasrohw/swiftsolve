# baseline/__init__.py
"""Baseline evaluation module for comparing against SwiftSolve."""

from .agent import GPT4BaselineAgent
from .pipeline import run_baseline_pipeline

__all__ = ["GPT4BaselineAgent", "run_baseline_pipeline"]
