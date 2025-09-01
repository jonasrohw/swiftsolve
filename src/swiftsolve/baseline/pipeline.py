# baseline/pipeline.py
"""
Baseline Pipeline
================

A simple pipeline that uses Claude 4 Opus directly followed by profiling.
This mirrors the SwiftSolve pipeline structure but replaces the 
planner+coder+analyst loop with a single Claude 4 Opus call.
"""

from .agent import ClaudeOpusBaselineAgent
from ..agents.profiler import Profiler
from ..schemas import ProblemInput
from ..utils.logger import get_logger


log = get_logger("BaselinePipeline")


def run_baseline_pipeline(problem: ProblemInput):
    """
    Run the baseline pipeline: Claude 4 Opus → Profiler
    
    Args:
        problem: The problem to solve
        
    Returns:
        Pipeline result with status, code, profile, etc.
    """
    log.info(f"=== Starting baseline pipeline for task_id: {problem.task_id} ===")
    log.info(f"Problem input: {problem.model_dump_json(indent=2)}")
    
    # Initialize agents
    baseline_agent = ClaudeOpusBaselineAgent()
    profiler = Profiler()
    
    # Track for consistency with main pipeline
    agent_failures = 0
    max_failures = 2
    
    # Claude 4 Opus Generation Phase
    log.info("--- Starting Claude 4 Opus Baseline Agent ---")
    try:
        code = baseline_agent.solve(problem)
        log.info(f"✅ Claude 4 Opus baseline generated solution successfully")
        log.info(f"Code length: {len(code.code_cpp)} characters")
    except Exception as e:
        agent_failures += 1
        log.error(f"Claude 4 Opus baseline failed (attempt {agent_failures}/{max_failures}): {e}")
        return {
            "status": "agent_failure", 
            "error": "Claude 4 Opus baseline failed", 
            "details": str(e), 
            "iterations": 1
        }
    
    # Profiler Phase (same as SwiftSolve)
    log.info("--- Starting Profiler ---")
    log.info(f"🔄 HANDOFF: Code → Profiler")
    try:
        profile = profiler.run(code)
        log.info(f"✅ HANDOFF: Profiler → Pipeline [SUCCESS]")
        log.info(f"Profile: {profile.model_dump_json(indent=2)}")
    except Exception as e:
        agent_failures += 1
        log.error(f"Profiler failed (attempt {agent_failures}/{max_failures}): {e}")
        return {
            "status": "agent_failure", 
            "error": "Profiler failed", 
            "details": str(e), 
            "iterations": 1
        }
    
    # Success - return the same format as SwiftSolve pipeline
    log.info("=== Baseline Pipeline SUCCESS - Solution generated and profiled ===")
    return {
        "status": "success", 
        "code": code.code_cpp, 
        "profile": profile, 
        "iterations": 1  # Baseline always uses 1 iteration
    }
