# static_pruner/pruner.py
import ast, re
from ..schemas import PlanMessage
from ..utils.logger import get_logger

log = get_logger("StaticPruner")
_BAD_SORT_LOOP = re.compile(r"for .* in .*:.*sort\(.*\)", re.S)

def validate(plan: PlanMessage) -> bool:
    """
    Basic heuristics — return False to REJECT plan before LLM spend.
    """
    log.info(f"Static pruner validating plan: {plan.model_dump_json(indent=2)}")
    
    algo = plan.algorithm.lower()
    n = plan.input_bounds.get("n", 0)
    
    log.info(f"Algorithm: {algo}")
    log.info(f"Input bound n: {n}")
    
    # Check for while loop issues
    if "while" in algo and "while" in algo.count("while") > 2 and n >= 1e5:
        log.warning(f"Rejecting plan: too many while loops ({algo.count('while')}) with large n ({n})")
        return False
    
    # Check for recursion issues
    if "recursion" in algo and n >= 1e4:
        log.warning(f"Rejecting plan: recursion with large n ({n})")
        return False
    
    # Check for sort-in-loop issues
    if _BAD_SORT_LOOP.search(algo) and n >= 1e3:
        log.warning(f"Rejecting plan: sort in loop pattern detected with n ({n})")
        return False
    
    log.info("Static pruner approved plan")
    return True