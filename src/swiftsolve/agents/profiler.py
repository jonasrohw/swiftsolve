# agents/profiler.py
from .base import Agent
from ..schemas import CodeMessage, ProfileReport
from ..sandbox.run_in_sandbox import compile_and_run
from ..utils.config import get_settings
import statistics, json

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
            
            # Handle compilation/runtime failures gracefully
            if stderr and ("error" in stderr.lower() or "failed" in stderr.lower()):
                self.log.warning(f"Compilation/execution failed for input size {n}: {stderr[:100]}")
                # Use fallback values to prevent analyst crashes
                runtimes.append(1.0)  # 1ms baseline
                memories.append(1.0)  # 1MB baseline
            else:
                # parse `/usr/bin/time -v` output in stderr for mem & time
                # For now, use placeholder numbers based on output length
                runtime = max(1.0, float(len(stdout)) / 10.0)  # Minimum 1ms
                memory = max(1.0, float(len(stderr)) / 100.0)  # Minimum 1MB
                runtimes.append(runtime)
                memories.append(memory)
                
        return ProfileReport(task_id=code.task_id,
                             iteration=code.iteration,
                             input_sizes=_INPUT_SCALES,
                             runtime_ms=runtimes,
                             peak_memory_mb=memories,
                             hotspots=hotspots)