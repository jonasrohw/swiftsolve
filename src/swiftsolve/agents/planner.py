# agents/planner.py
from anthropic import Anthropic, HUMAN_PROMPT, AI_PROMPT
from agents.base import Agent
from schemas.plan import PlanMessage, ProblemInput
from utils.config import get_settings
import json

class Planner(Agent):
    def __init__(self):
        super().__init__("Planner")
        self.client = Anthropic(api_key=get_settings().anthropic_api_key)

    def run(self, problem: ProblemInput) -> PlanMessage:
        prompt = (
            f"{HUMAN_PROMPT} You are a CP strategist. "
            f"Given the problem below, output a JSON dict with fields "
            f"`algorithm`, `input_bounds`, and `constraints`.\n\n"
            f"PROBLEM:\n{problem.prompt}\n{AI_PROMPT}"
        )
        resp = self.client.completions.create(
            model="claude-4-opus-2025-07-01",
            max_tokens=512,
            temperature=0.3,
            prompt=prompt,
        )
        plan_dict = resp.completion.strip("`").strip()
        try:
            plan = PlanMessage(**json.loads(plan_dict), task_id=problem.task_id)
        except Exception as e:
            self.log.error(f"Malformed plan: {e}\n{plan_dict}")
            raise
        return plan