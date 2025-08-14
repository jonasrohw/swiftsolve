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
    
    # Crash handling: track agent failures (CONTEXT.md line 257)
    agent_failures = 0
    max_failures = 2
    
    # Planner phase
    log.info("--- Starting Planner ---")
    log.info(f"🔄 HANDOFF: ProblemInput → Planner")
    try:
        plan = planner.run(problem)
        log.info(f"✅ HANDOFF: Planner → Pipeline [SUCCESS]")
        log.info(f"Plan: {plan.model_dump_json(indent=2)}")
    except Exception as e:
        agent_failures += 1
        log.error(f"Planner failed (attempt {agent_failures}/{max_failures}): {e}")
        if agent_failures >= max_failures:
            log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
            return {"status": "agent_failure", "error": "Planner failed", "details": str(e)}
        return {"status": "agent_failure", "error": "Planner failed", "details": str(e)}
    
    # Static pruner phase
    log.info("--- Starting Static Pruner ---")
    log.info(f"🔄 HANDOFF: Planner → StaticPruner")
    try:
        if not pruner.validate(plan):
            log.warning("Static pruner rejected plan")
            return {"status": "static_prune_failed"}
        log.info("Static pruner approved plan")
    except Exception as e:
        agent_failures += 1
        log.error(f"Static Pruner failed (attempt {agent_failures}/{max_failures}): {e}")
        if agent_failures >= max_failures:
            log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
            return {"status": "agent_failure", "error": "Static Pruner failed", "details": str(e)}
        return {"status": "agent_failure", "error": "Static Pruner failed", "details": str(e)}

    last_time = float("inf")
    pending_patch = None  # Track patches to apply in next iteration
    
    for iter_idx in range(max_iter):
        log.info(f"=== Starting iteration {iter_idx + 1}/{max_iter} ===")
        
        # Coder phase - apply pending patch if any
        log.info("--- Starting Coder ---")
        log.info(f"🔄 HANDOFF: Plan → Coder [patch={bool(pending_patch)}]")
        try:
            if pending_patch:
                log.info(f"🩹 Applying patch: {pending_patch}")
                code = coder.run(plan, patch=pending_patch)
                pending_patch = None  # Clear the patch after applying
            else:
                code = coder.run(plan)
            log.info(f"✅ HANDOFF: Coder → Pipeline [SUCCESS]")
            log.info(f"Code: {code.model_dump_json(indent=2)}")
        except Exception as e:
            agent_failures += 1
            log.error(f"Coder failed (attempt {agent_failures}/{max_failures}): {e}")
            if agent_failures >= max_failures:
                log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
                return {"status": "agent_failure", "error": "Coder failed", "details": str(e)}
            continue  # Skip this iteration and try again
        
        # Profiler phase
        log.info("--- Starting Profiler ---")
        log.info(f"🔄 HANDOFF: Code → Profiler")
        try:
            profile = profiler.run(code)
            log.info(f"✅ HANDOFF: Profiler → Pipeline [SUCCESS]")
            log.info(f"Profile: {profile.model_dump_json(indent=2)}")
        except Exception as e:
            agent_failures += 1
            log.error(f"Profiler failed (attempt {agent_failures}/{max_failures}): {e}")
            if agent_failures >= max_failures:
                log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
                return {"status": "agent_failure", "error": "Profiler failed", "details": str(e)}
            continue  # Skip this iteration and try again
        
        # Analyst phase
        log.info("--- Starting Analyst ---")
        log.info(f"🔄 HANDOFF: Profile → Analyst")
        try:
            verdict: VerdictMessage = analyst.run(profile, problem.constraints)
            log.info(f"✅ HANDOFF: Analyst → Pipeline [SUCCESS]")
            log.info(f"Verdict: {verdict.model_dump_json(indent=2)}")
        except Exception as e:
            agent_failures += 1
            log.error(f"Analyst failed (attempt {agent_failures}/{max_failures}): {e}")
            if agent_failures >= max_failures:
                log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
                return {"status": "agent_failure", "error": "Analyst failed", "details": str(e)}
            continue  # Skip this iteration and try again

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
            try:
                # Generate feedback for planner based on current performance issues
                feedback = f"Previous algorithm '{plan.algorithm}' showed inefficient performance with runtime {current_time:.2f}ms for large inputs. The current approach is not meeting the efficiency requirements. Choose a fundamentally different algorithmic approach that can achieve O(n log n) or better time complexity."
                log.info(f"🔄 HANDOFF: Feedback → Planner [RE-PLANNING]")
                plan = planner.run(problem, feedback=feedback)  # re-plan with feedback
                log.info(f"✅ HANDOFF: Planner → Pipeline [RE-PLAN SUCCESS]")
                log.info(f"Updated plan: {plan.model_dump_json(indent=2)}")
            except Exception as e:
                agent_failures += 1
                log.error(f"Planner re-planning failed (attempt {agent_failures}/{max_failures}): {e}")
                if agent_failures >= max_failures:
                    log.error("=== PIPELINE ABORTED - Maximum agent failures reached ===")
                    return {"status": "agent_failure", "error": "Planner re-planning failed", "details": str(e)}
                continue  # Skip this iteration and try again
        
        last_time = current_time
    
    log.warning("=== Pipeline FAILED - Max iterations reached or insufficient gain ===")
    return {"status": "failed", "last_verdict": verdict.model_dump()}