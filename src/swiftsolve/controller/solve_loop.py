from ..agents.planner import Planner
from ..agents.coder import Coder
from ..agents.profiler import Profiler
from ..agents.analyst import Analyst
from ..static_pruner import pruner
from ..schemas import ProblemInput, VerdictMessage, CodeMessage
from ..utils.config import get_settings
from ..utils.logger import get_logger
import json

log = get_logger("SolveLoop")
planner, coder, profiler, analyst = Planner(), Coder(), Profiler(), Analyst()

def run_pipeline(problem: ProblemInput):
    log.info(f"=== Starting pipeline for task_id: {problem.task_id} ===")
    log.info(f"Problem input: {problem.model_dump_json(indent=2)}")
    
    max_iter = get_settings().max_iterations
    log.info(f"Max iterations: {max_iter}")
    
    # Planner phase
    log.info("--- Starting Planner ---")
    plan = planner.run(problem)
    log.info(f"Planner completed. Plan: {plan.model_dump_json(indent=2)}")
    
    # Static pruner phase
    log.info("--- Starting Static Pruner ---")
    if not pruner.validate(plan):
        log.warning("Static pruner rejected plan")
        return {"status": "static_prune_failed"}
    log.info("Static pruner approved plan")

    last_time = float("inf")
    pending_patch = None  # Track patches to apply in next iteration
    
    for iter_idx in range(max_iter):
        log.info(f"=== Starting iteration {iter_idx + 1}/{max_iter} ===")
        
        # Coder phase - apply pending patch if any
        log.info("--- Starting Coder ---")
        if pending_patch:
            log.info(f"Applying pending patch: {pending_patch}")
            code = coder.run(plan, patch=pending_patch)
            pending_patch = None  # Clear the patch after applying
        else:
            code = coder.run(plan)
        log.info(f"Coder completed. Code message: {code.model_dump_json(indent=2)}")
        
        # Profiler phase
        log.info("--- Starting Profiler ---")
        profile = profiler.run(code)
        log.info(f"Profiler completed. Profile report: {profile.model_dump_json(indent=2)}")
        
        # Analyst phase
        log.info("--- Starting Analyst ---")
        verdict: VerdictMessage = analyst.run(profile, problem.constraints)
        log.info(f"Analyst completed. Verdict: {verdict.model_dump_json(indent=2)}")

        if verdict.efficient:
            log.info("=== Pipeline SUCCESS - Solution is efficient ===")
            return {"status": "success", "code": code.code_cpp, "profile": profile}
        
        # Store current performance for gain calculation
        current_time = profile.runtime_ms[-1] if profile.runtime_ms else float('inf')
        
        # Calculate performance gain vs last iteration
        if last_time != float('inf') and current_time != float('inf'):
            gain = (last_time - current_time) / last_time
            log.info(f"Performance gain: {gain:.4f} (threshold: {get_settings().diminish_delta})")
            
            if gain < get_settings().diminish_delta:
                log.info("Performance gain below threshold, stopping")
                break
        else:
            log.info("Cannot calculate performance gain (infinite values)")
        
        # Routing logic - prepare corrections for next iteration
        if verdict.target_agent == "CODER":
            log.info(f"Routing to Coder - will apply patch in next iteration: {verdict.patch}")
            pending_patch = verdict.patch
        else:
            log.info("Routing to Planner for re-planning")
            # Generate feedback for planner based on current performance issues
            feedback = f"Previous algorithm '{plan.algorithm}' showed inefficient performance with runtime {current_time:.2f}ms for large inputs. The current approach is not meeting the efficiency requirements. Choose a fundamentally different algorithmic approach that can achieve O(n log n) or better time complexity."
            plan = planner.run(problem, feedback=feedback)  # re-plan with feedback
            log.info(f"Planner re-plan completed. Updated plan: {plan.model_dump_json(indent=2)}")
        
        last_time = current_time
    
    log.warning("=== Pipeline FAILED - Max iterations reached or insufficient gain ===")
    return {"status": "failed", "last_verdict": verdict.model_dump()}