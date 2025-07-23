# static_pruner/pruner.py
import ast, re
from ..schemas import PlanMessage

_BAD_SORT_LOOP = re.compile(r"for .* in .*:.*sort\(.*\)", re.S)

def validate(plan: PlanMessage) -> bool:
    """
    Basic heuristics — return False to REJECT plan before LLM spend.
    """
    algo = plan.algorithm.lower()
    n = plan.input_bounds.get("n", 0)
    if "while" in algo and "while" in algo.count("while") > 2 and n >= 1e5:
        return False
    if "recursion" in algo and n >= 1e4:
        return False
    if _BAD_SORT_LOOP.search(algo) and n >= 1e3:
        return False
    return True