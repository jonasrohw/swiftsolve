# agents/analyst.py
from .base import Agent
from ..schemas import ProfileReport, VerdictMessage
from ..utils.config import get_settings
from openai import OpenAI
import json, math

class Analyst(Agent):
    def __init__(self):
        super().__init__("Analyst")
        self.client = OpenAI(api_key=get_settings().openai_api_key)

    def _curve_fit(self, report: ProfileReport):
        self.log.info(f"Starting curve fitting for profile report: {report.model_dump_json(indent=2)}")
        
        # Robust curve fitting with error handling
        try:
            # Filter out invalid runtime values (0 or negative)
            valid_runtimes = [t for t in report.runtime_ms if t > 0]
            if not valid_runtimes:
                self.log.warning("No valid runtimes found for curve fitting")
                return "O(1)"  # Default assumption
                
            self.log.info(f"Valid runtimes: {valid_runtimes}")
                
            ys = [math.log10(t) for t in valid_runtimes]
            xs = [math.log10(n) for n in report.input_sizes[:len(valid_runtimes)]]
            
            self.log.info(f"Log-log data points: xs={xs}, ys={ys}")
            
            if len(xs) < 2:
                self.log.warning("Not enough data points for curve fitting")
                return "O(1)"  # Not enough data points
                
            # Simple linear regression
            n = len(xs)
            slope = (n * sum(x*y for x,y in zip(xs,ys)) - sum(xs) * sum(ys)) / (n * sum(x*x for x in xs) - sum(xs)**2)
            
            self.log.info(f"Calculated slope: {slope}")
            
            # Classify complexity based on slope
            if slope < 0.5:
                complexity = "O(1)"
            elif slope < 1.5:
                complexity = "O(n)"
            elif slope < 2.5:
                complexity = "O(n^2)"
            else:
                complexity = "O(n^k)"
            
            self.log.info(f"Classified complexity: {complexity}")
            return complexity
            
        except Exception as e:
            self.log.error(f"Curve fitting failed: {e}")
            return "O(?)"  # Unknown complexity

    def run(self, report: ProfileReport, constraints: dict) -> VerdictMessage:
        self.log.info(f"Analyst starting with report: {report.model_dump_json(indent=2)}")
        self.log.info(f"Constraints: {constraints}")
        
        time_complexity = self._curve_fit(report)
        efficient = time_complexity in {"O(1)", "O(log n)", "O(n)", "O(n log n)"}
        perf_gain = 0.0  # compute real gain vs last iter outside
        
        self.log.info(f"Analysis results: complexity={time_complexity}, efficient={efficient}")
        
        from ..schemas import TargetAgent
        
        # Generate intelligent patches based on detected complexity
        if not efficient:
            target_agent = TargetAgent.CODER
            patch = self._generate_optimization_patch(time_complexity, report)
        else:
            target_agent = None
            patch = None
        
        self.log.info(f"Routing decision: target_agent={target_agent}, patch={patch}")
        
        verdict = VerdictMessage(task_id=report.task_id,
                              iteration=report.iteration,
                              efficient=efficient,
                              target_agent=target_agent,
                              patch=patch,
                              perf_gain=perf_gain)
        
        self.log.info(f"Analyst completed. Verdict: {verdict.model_dump_json(indent=2)}")
        return verdict
    
    def _generate_optimization_patch(self, complexity: str, report: ProfileReport) -> str:
        """Generate specific optimization suggestions based on detected complexity."""
        self.log.info(f"Generating optimization patch for complexity: {complexity}")
        
        # Check memory usage pattern for additional hints
        memory_growth = "high" if len(report.peak_memory_mb) > 1 and report.peak_memory_mb[-1] / report.peak_memory_mb[0] > 5 else "low"
        
        if complexity == "O(n^2)":
            if memory_growth == "high":
                patch = "Replace nested loops with hash map lookup. Use unordered_map<int, int> to store values and their indices, then iterate once to find complements in O(1) time."
            else:
                patch = "Optimize nested loop structure. Consider using sorting + two pointers technique, or hash map for O(n) lookups instead of O(n^2) nested iteration."
        elif complexity == "O(n^k)" or "n^" in complexity:
            patch = "Reduce algorithmic complexity. Current solution appears exponential/polynomial. Consider: 1) Dynamic programming to eliminate redundant calculations, 2) Memoization, 3) Greedy algorithm, or 4) Different data structure (hash map, set, priority queue)."
        elif complexity == "O(n log n)" and memory_growth == "high":
            patch = "Optimize memory usage while maintaining O(n log n) time. Consider in-place operations, iterative instead of recursive approaches, or streaming algorithms to reduce space complexity."
        elif complexity == "O(n)" and memory_growth == "high":
            patch = "Reduce memory allocation. Current O(n) solution uses excessive memory. Consider: 1) Process data in chunks, 2) Reuse containers, 3) Use primitive arrays instead of vectors where possible, 4) Eliminate unnecessary data structures."
        else:
            # Generic optimization for unknown/complex patterns
            patch = f"Optimize {complexity} algorithm. Current implementation is inefficient. Consider: 1) Better data structures (hash maps, sets), 2) Eliminate redundant operations, 3) Use standard library algorithms, 4) Reduce memory allocations."
        
        self.log.info(f"Generated optimization patch: {patch}")
        return patch