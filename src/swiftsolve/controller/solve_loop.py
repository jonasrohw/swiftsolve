from ..agents.planner import Planner
from ..agents.coder import Coder
from ..agents.profiler import Profiler
from ..agents.analyst import Analyst
from ..static_pruner import pruner
from ..schemas import ProblemInput, VerdictMessage, CodeMessage
from ..utils.config import get_settings
from ..utils.logger import get_logger

log = get_logger("SolveLoop")
planner, coder, profiler, analyst = Planner(), Coder(), Profiler(), Analyst()

def run_pipeline(problem: ProblemInput):
    max_iter = get_settings().max_iterations
    plan = planner.run(problem)
    if not pruner.validate(plan):
        return {"status": "static_prune_failed"}

    last_time = float("inf")
    for iter_idx in range(max_iter):
        code = coder.run(plan)
        profile = profiler.run(code)
        verdict: VerdictMessage = analyst.run(profile, problem.constraints)

        if verdict.efficient:
            return {"status": "success", "code": code.code_cpp, "profile": profile}
        if verdict.target_agent == "CODER":
            # simple patch prompt chaining
            code = coder.run(plan)  # TODO: pass patch
        else:
            plan = planner.run(problem)  # re-plan
        gain = (last_time - profile.runtime_ms[-1]) / last_time
        if gain < get_settings().diminish_delta:
            break
        last_time = profile.runtime_ms[-1]
    return {"status": "failed", "last_verdict": verdict.model_dump()}