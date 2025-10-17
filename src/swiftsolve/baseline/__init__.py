"""
Baseline Module
==============

Provides a baseline implementation using Claude 4 Opus directly
for comparison against the SwiftSolve multi-agent system.
"""

from .agent import ClaudeOpusBaselineAgent
from .evaluation import BaselineEvaluationRunner, BaselineRunResult
from .pipeline import run_baseline_pipeline

__all__ = [
    "ClaudeOpusBaselineAgent",
    "BaselineEvaluationRunner", 
    "BaselineRunResult",
    "run_baseline_pipeline"
]
