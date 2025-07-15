# schemas/plan.py
from pydantic import BaseModel, Field
from typing import Dict, List, Any

class ProblemInput(BaseModel):
    task_id: str
    prompt: str
    constraints: Dict[str, Any]  # runtime_limit, memory_limit, etc.
    unit_tests: List[Dict[str, str]]

class PlanMessage(BaseModel):
    task_id: str
    algorithm: str
    input_bounds: Dict[str, int]
    constraints: Dict[str, Any]
