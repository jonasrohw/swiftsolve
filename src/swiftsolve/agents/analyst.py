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
            valid_runtimes = [t for t in report.runtime_ms if t > 0 and t != float('inf')]
            if not valid_runtimes:
                self.log.warning("No valid runtimes found for curve fitting")
                return "O(1)"  # Default assumption
                
            self.log.info(f"Valid runtimes: {valid_runtimes}")
            
            if len(valid_runtimes) < 3:
                self.log.warning("Not enough data points for reliable curve fitting")
                return "O(1)"  # Not enough data points
                
            ys = [math.log10(t) for t in valid_runtimes]
            xs = [math.log10(n) for n in report.input_sizes[:len(valid_runtimes)]]
            
            self.log.info(f"Log-log data points: xs={xs}, ys={ys}")
                
            # Simple linear regression
            n = len(xs)
            slope = (n * sum(x*y for x,y in zip(xs,ys)) - sum(xs) * sum(ys)) / (n * sum(x*x for x in xs) - sum(xs)**2)
            
            # Calculate R-squared for goodness of fit
            y_mean = sum(ys) / len(ys)
            y_pred = [slope * x + (sum(ys) - slope * sum(xs)) / n for x in xs]
            ss_res = sum((y_actual - y_pred_val) ** 2 for y_actual, y_pred_val in zip(ys, y_pred))
            ss_tot = sum((y - y_mean) ** 2 for y in ys)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            self.log.info(f"Calculated slope: {slope:.3f}, R²: {r_squared:.3f}")
            
            # Check if curve is ambiguous and needs LLM analysis
            is_ambiguous = self._is_curve_ambiguous(slope, r_squared, valid_runtimes, report.input_sizes[:len(valid_runtimes)])
            
            if is_ambiguous:
                self.log.warning("Curve is ambiguous, falling back to LLM analysis")
                return self._llm_complexity_analysis(report)
            
            # Classify complexity based on slope (heuristic classification)
            if slope < 0.5:
                complexity = "O(1)"
            elif slope < 1.5:
                complexity = "O(n)"
            elif slope < 2.5:
                complexity = "O(n^2)"
            else:
                complexity = "O(n^k)"
            
            self.log.info(f"Heuristic classified complexity: {complexity}")
            return complexity
            
        except Exception as e:
            self.log.error(f"Curve fitting failed: {e}")
            # Fallback to LLM analysis when heuristic fails
            try:
                return self._llm_complexity_analysis(report)
            except Exception as llm_e:
                self.log.error(f"LLM fallback also failed: {llm_e}")
                return "O(?)"  # Unknown complexity
    
    def _is_curve_ambiguous(self, slope: float, r_squared: float, runtimes: list, input_sizes: list) -> bool:
        """Detect if the performance curve is ambiguous and needs LLM analysis."""
        self.log.info(f"Checking curve ambiguity: slope={slope:.3f}, R²={r_squared:.3f}")
        
        # Criteria for ambiguous curves:
        
        # 1. Poor fit (low R-squared)
        if r_squared < 0.7:
            self.log.info("Poor fit detected (R² < 0.7)")
            return True
        
        # 2. Slope in ambiguous range (between clear categories)
        ambiguous_ranges = [
            (0.4, 0.6),   # Between O(1) and O(n)
            (1.3, 1.7),   # Between O(n) and O(n^2) - wider range
            (2.3, 2.7),   # Between O(n^2) and O(n^k) - wider range
        ]
        for low, high in ambiguous_ranges:
            if low <= slope <= high:
                self.log.info(f"Slope {slope:.3f} in ambiguous range [{low}, {high}]")
                return True
        
        # 3. Highly irregular or noisy data
        if len(runtimes) >= 4:
            # Check for non-monotonic behavior (significant ups and downs)
            increases = 0
            decreases = 0
            for i in range(1, len(runtimes)):
                if runtimes[i] > runtimes[i-1] * 1.1:  # Significant increase
                    increases += 1
                elif runtimes[i] < runtimes[i-1] * 0.9:  # Significant decrease
                    decreases += 1
            
            # If we have both significant increases and decreases, it's noisy
            if increases > 0 and decreases > 0:
                self.log.info(f"Noisy data detected: {increases} increases, {decreases} decreases")
                return True
        
        # 4. Extreme slope values that might indicate measurement errors
        if slope < -0.5 or slope > 10:
            self.log.info(f"Extreme slope {slope:.3f} detected")
            return True
        
        # 5. Very small input size range (hard to determine complexity)
        if len(input_sizes) >= 2:
            size_ratio = max(input_sizes) / min(input_sizes)
            if size_ratio < 10:  # Less than 10x range
                self.log.info(f"Small input size range: {size_ratio:.1f}x")
                return True
        
        self.log.info("Curve appears unambiguous")
        return False
    
    def _llm_complexity_analysis(self, report: ProfileReport) -> str:
        """Use GPT-4.1 to analyze ambiguous performance curves."""
        self.log.info("Starting LLM complexity analysis for ambiguous curve")
        
        # Prepare the performance data for LLM analysis
        data_summary = []
        for i, (size, runtime, memory) in enumerate(zip(report.input_sizes, report.runtime_ms, report.peak_memory_mb)):
            if runtime > 0 and runtime != float('inf'):
                data_summary.append(f"n={size}: {runtime:.2f}ms, {memory:.2f}MB")
        
        system_msg = """You are an expert algorithm complexity analyst. Analyze performance data to determine time complexity.

Your task: Given runtime measurements across different input sizes, determine the most likely time complexity class.

Output EXACTLY one of these complexity classes:
- O(1)
- O(log n)  
- O(n)
- O(n log n)
- O(n^2)
- O(n^3)
- O(2^n)
- O(n!)

Consider:
1. How runtime scales with input size
2. Patterns in the growth rate
3. Possible measurement noise or irregularities
4. Common algorithmic complexities

Be conservative - if unsure between two complexities, choose the simpler one."""

        user_msg = f"""Analyze this performance data:

{chr(10).join(data_summary)}

The measurements show runtime in milliseconds for different input sizes (n).

What is the most likely time complexity class? Consider that:
- Measurements may contain some noise
- Real-world performance can deviate from theoretical complexity
- Look for the overall trend rather than minor fluctuations

Response format: Just the complexity class (e.g., "O(n^2)")"""

        self.log.info(f"Sending LLM request with data: {data_summary}")
        
        try:
            resp = self.client.chat.completions.create(
                model="gpt-4.1",  # Using gpt-4.1 as specified in CONTEXT.md
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg}
                ],
                temperature=0.1,
                max_tokens=50,  # Short response expected
            )
            
            complexity = resp.choices[0].message.content.strip()
            self.log.info(f"LLM analyzed complexity: {complexity}")
            
            # Validate and normalize the response
            valid_complexities = ["O(1)", "O(log n)", "O(n)", "O(n log n)", "O(n^2)", "O(n^3)", "O(2^n)", "O(n!)"]
            
            # Handle variations in LLM response format
            for valid in valid_complexities:
                if valid.lower() in complexity.lower() or valid.replace(" ", "") in complexity.replace(" ", ""):
                    self.log.info(f"LLM complexity normalized to: {valid}")
                    return valid
            
            # If we can't parse it, try to extract the core pattern
            if "n^2" in complexity or "n²" in complexity:
                return "O(n^2)"
            elif "n log n" in complexity or "nlogn" in complexity:
                return "O(n log n)"
            elif "log n" in complexity or "logn" in complexity:
                return "O(log n)"
            elif complexity.count("n") == 1 and "^" not in complexity:
                return "O(n)"
            elif "1" in complexity or "constant" in complexity.lower():
                return "O(1)"
            else:
                self.log.warning(f"Could not parse LLM response: {complexity}")
                return "O(?)"
                
        except Exception as e:
            self.log.error(f"LLM complexity analysis failed: {e}")
            return "O(?)"

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