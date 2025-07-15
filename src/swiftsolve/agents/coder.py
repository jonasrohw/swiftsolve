# agents/coder.py
from openai import OpenAI
from agents.base import Agent
from schemas.plan import PlanMessage
from schemas.code import CodeMessage
from utils.config import get_settings
import json, textwrap

class Coder(Agent):
    def __init__(self):
        super().__init__("Coder")
        self.client = OpenAI(api_key=get_settings().openai_api_key)

    def run(self, plan: PlanMessage) -> CodeMessage:
        system_msg = (
            "You are an expert ICPC medalist. "
            "Write efficient ISO C++17 code ONLY, no explanation."
        )
        user_msg = (
            f"Generate code for the following plan as JSON {{\"code_cpp\": \"...\"}}:\n"
            f"{plan.model_dump_json()}"
        )
        resp = self.client.chat.completions.create(
            model="gpt-4o-2025-07-01",
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.2,
            max_tokens=1024,
        )
        code_json = resp.choices[0].message.content.strip("`")
        code = CodeMessage(**json.loads(code_json), task_id=plan.task_id)
        return code