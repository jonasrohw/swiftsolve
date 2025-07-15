# schemas/verdict.py
from pydantic import BaseModel
from typing import Optional

class VerdictMessage(BaseModel):
    task_id: str
    efficient: bool
    target_agent: Optional[str] = None  # "PLANNER" | "CODER"
    patch: Optional[str] = None
    perf_gain: float = 0.0
