# schemas/profile.py
from pydantic import BaseModel, Field, List

class ProfileReport(BaseModel):
    task_id: str
    input_sizes: List[int]
    runtime_ms: List[float]
    memory_mb: List[float]
    hotspots: dict
