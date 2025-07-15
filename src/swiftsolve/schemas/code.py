# schemas/code.py
from pydantic import BaseModel

class CodeMessage(BaseModel):
    task_id: str
    code_cpp: str
