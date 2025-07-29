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
    for iter_idx in range(max_iter):
        log.info(f"=== Starting iteration {iter_idx + 1}/{max_iter} ===")
        
        # Coder phase
        log.info("--- Starting Coder ---")
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
        
        # Routing logic
        if verdict.target_agent == "CODER":
            log.info("Routing to Coder for patch")
            # simple patch prompt chaining
            code = coder.run(plan)  # TODO: pass patch
            log.info(f"Coder patch completed. Updated code: {code.model_dump_json(indent=2)}")
        else:
            log.info("Routing to Planner for re-planning")
            plan = planner.run(problem)  # re-plan
            log.info(f"Planner re-plan completed. Updated plan: {plan.model_dump_json(indent=2)}")
        
        gain = (last_time - profile.runtime_ms[-1]) / last_time
        log.info(f"Performance gain: {gain:.4f} (threshold: {get_settings().diminish_delta})")
        
        if gain < get_settings().diminish_delta:
            log.info("Performance gain below threshold, stopping")
            break
        last_time = profile.runtime_ms[-1]
    
    log.warning("=== Pipeline FAILED - Max iterations reached or insufficient gain ===")
    return {"status": "failed", "last_verdict": verdict.model_dump()}