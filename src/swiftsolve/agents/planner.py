# agents/planner.py
from anthropic import Anthropic
from .base import Agent
from ..schemas import PlanMessage, ProblemInput
from ..utils.config import get_settings
import json
import json

class Planner(Agent):
    def __init__(self):
        super().__init__("Planner")
        self.client = Anthropic(api_key=get_settings().anthropic_api_key)

    def run(self, problem: ProblemInput) -> PlanMessage:
        system_msg = """You are a competitive programming strategist. 
        
Output EXACTLY this JSON format:
{
    "algorithm": "brief_algorithm_name",
    "input_bounds": {"n": 100000, "m": 50000},
    "constraints": {"runtime_limit": 2000, "memory_limit": 512}
}

Rules:
- algorithm: short string describing the approach
- input_bounds: simple key-value pairs where values are INTEGER limits
- constraints: simple key-value pairs with INTEGER values only
- NO nested objects, NO strings in values, NO arrays"""

        user_msg = f"PROBLEM:\n{problem.prompt}\n\nGenerate the JSON plan:"
        
        resp = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=512,
            temperature=0.1,
            system=system_msg,
            messages=[{"role": "user", "content": user_msg}]
        )
        
        plan_text = resp.content[0].text.strip()
        # Extract JSON from markdown code blocks if present
        if "```" in plan_text:
            plan_text = plan_text.split("```")[1]
            if plan_text.startswith("json"):
                plan_text = plan_text[4:]
        plan_text = plan_text.strip()
        
        try:
            plan_data = json.loads(plan_text)
            
            # Ensure input_bounds has integer values
            input_bounds = {}
            for key, value in plan_data.get("input_bounds", {}).items():
                if isinstance(value, dict):
                    # Convert complex bounds to simple integer
                    input_bounds[key] = 100000  # default safe limit
                else:
                    input_bounds[key] = int(value)
            
            # Ensure constraints is a dict with integer values  
            constraints = {}
            constraint_data = plan_data.get("constraints", {})
            if isinstance(constraint_data, list):
                # Convert list to dict
                constraints = {"runtime_limit": 2000, "memory_limit": 512}
            else:
                for key, value in constraint_data.items():
                    constraints[key] = int(value)
            
            plan = PlanMessage(
                task_id=problem.task_id,
                iteration=0,
                algorithm=plan_data["algorithm"],
                input_bounds=input_bounds,
                constraints=constraints
            )
        except Exception as e:
            self.log.error(f"Malformed plan: {e}\n{plan_text}")
            # Fallback to default plan
            plan = PlanMessage(
                task_id=problem.task_id,
                iteration=0,
                algorithm="linear_solution",
                input_bounds={"n": 100000},
                constraints={"runtime_limit": 2000, "memory_limit": 512}
            )
        return plan