# agents/analyst.py
from agents.base import Agent
from schemas.profile import ProfileReport
from schemas.verdict import VerdictMessage
from utils.config import get_settings
from openai import OpenAI
import json, math

class Analyst(Agent):
    def __init__(self):
        super().__init__("Analyst")
        self.client = OpenAI(api_key=get_settings().openai_api_key)

    def _curve_fit(self, report: ProfileReport) -> str:
        # naive heuristic: log-log slope ≈ complexity class
        xs = [math.log10(x) for x in report.input_sizes]
        ys = [math.log10(t) for t in report.runtime_ms]
        slope = (ys[-1] - ys[0]) / (xs[-1] - xs[0])
        if slope < 0.2: return "O(1)"
        if slope < 0.8: return "O(log n)"
        if slope < 1.2: return "O(n)"
        if slope < 1.7: return "O(n log n)"
        if slope < 2.5: return "O(n^2)"
        return "super-quadratic"

    def run(self, report: ProfileReport, constraints: dict) -> VerdictMessage:
        time_complexity = self._curve_fit(report)
        efficient = time_complexity in {"O(1)", "O(log n)", "O(n)", "O(n log n)"}
        perf_gain = 0.0  # compute real gain vs last iter outside
        return VerdictMessage(task_id=report.task_id,
                              efficient=efficient,
                              target_agent=("CODER" if not efficient else None),
                              patch="Inline the outer loop" if not efficient else None,
                              perf_gain=perf_gain)