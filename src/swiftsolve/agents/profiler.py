# agents/profiler.py
from agents.base import Agent
from schemas.code import CodeMessage
from schemas.profile import ProfileReport
from sandbox.run_in_sandbox import compile_and_run
import statistics, json

from swiftsolve.utils.config import get_settings

_INPUT_SCALES = [1_000, 5_000, 10_000, 50_000, 100_000]

class Profiler(Agent):
    def __init__(self):
        super().__init__("Profiler")

    def _gen_dummy_input(self, n: int) -> str:
        return f"{n}\n"  # placeholder; replace with task-specific generator

    def run(self, code: CodeMessage) -> ProfileReport:
        runtimes, memories = [], []
        hotspots = {}
        for n in _INPUT_SCALES:
            stdout, stderr = compile_and_run(code.code_cpp,
                                             self._gen_dummy_input(n),
                                             timeout=get_settings().sandbox_timeout_sec)
            # parse `/usr/bin/time -v` output in stderr for mem & time
            # placeholder numbers:
            runtimes.append(float(len(stdout)))  # dummy
            memories.append(float(len(stderr)))  # dummy
        return ProfileReport(task_id=code.task_id,
                             input_sizes=_INPUT_SCALES,
                             runtime_ms=runtimes,
                             memory_mb=memories,
                             hotspots=hotspots)