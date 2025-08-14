"""
Evaluation Metrics

Implements the evaluation metrics specified in CONTEXT.md section 1.9:
- pass@k: ≥ 1 of top-k programs passes official unit tests
- eff@k_runtime: ≥ 1 of top-k passes time limit  
- eff@k_memory: ≥ 1 of top-k stays < memory limit
- TLE/MLE rate: % of executions exceeding runtime or memory cap
- Iteration count: Mean #loops until efficient==true

Used for systematic benchmarking and research evaluation.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from ..schemas import ProblemInput, RunResult
from ..utils.logger import get_logger

log = get_logger("EvaluationMetrics")


class RunStatus(str, Enum):
    """Possible run outcomes."""
    SUCCESS = "success"
    FAILED = "failed"
    STATIC_PRUNE_FAILED = "static_prune_failed"
    AGENT_FAILURE = "agent_failure"
    TIMEOUT = "timeout"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    TLE = "time_limit_exceeded"
    MLE = "memory_limit_exceeded"


@dataclass
class RunMetrics:
    """Metrics for a single pipeline run."""
    task_id: str
    run_id: int
    status: RunStatus
    success: bool  # Whether solution is correct
    efficient_runtime: bool  # Whether solution passes time limit
    efficient_memory: bool  # Whether solution stays under memory limit
    iteration_count: int  # Number of iterations until convergence
    final_runtime_ms: Optional[float]  # Final runtime measurement
    final_memory_mb: Optional[float]  # Final memory measurement
    runtime_limit_ms: int  # Task time limit
    memory_limit_mb: int  # Task memory limit
    agent_failures: int  # Number of agent failures during run
    

class EvaluationMetrics:
    """Calculator for SwiftSolve evaluation metrics."""
    
    def __init__(self):
        """Initialize metrics calculator."""
        self.results: List[RunMetrics] = []
    
    def add_run_result(self, task_id: str, run_id: int, result: Dict[str, Any], 
                      runtime_limit: int, memory_limit: int) -> None:
        """
        Add a pipeline run result for evaluation.
        
        Args:
            task_id: Unique task identifier
            run_id: Run number for this task
            result: Pipeline result dictionary
            runtime_limit: Task time limit in ms
            memory_limit: Task memory limit in MB
        """
        status = RunStatus(result.get('status', 'failed'))
        
        # Determine success (correctness)
        success = status == RunStatus.SUCCESS
        
        # Extract performance metrics
        profile = result.get('profile', {})
        runtime_ms = None
        memory_mb = None
        
        if profile:
            runtime_ms = profile.get('runtime_ms', [None])[-1]  # Last measurement
            memory_mb = profile.get('peak_memory_mb', [None])[-1]
        
        # Determine efficiency
        efficient_runtime = True
        efficient_memory = True
        
        if runtime_ms is not None:
            efficient_runtime = runtime_ms <= runtime_limit
        if memory_mb is not None:
            efficient_memory = memory_mb <= memory_limit
        
        # Count iterations (estimate from result)
        iteration_count = 1  # Default
        if 'iteration' in result:
            iteration_count = result['iteration'] + 1
        elif 'last_verdict' in result:
            # Try to extract from verdict
            verdict = result.get('last_verdict', {})
            iteration_count = verdict.get('iteration', 0) + 1
        
        # Count agent failures
        agent_failures = 1 if status == RunStatus.AGENT_FAILURE else 0
        
        metrics = RunMetrics(
            task_id=task_id,
            run_id=run_id,
            status=status,
            success=success,
            efficient_runtime=efficient_runtime,
            efficient_memory=efficient_memory,
            iteration_count=iteration_count,
            final_runtime_ms=runtime_ms,
            final_memory_mb=memory_mb,
            runtime_limit_ms=runtime_limit,
            memory_limit_mb=memory_limit,
            agent_failures=agent_failures
        )
        
        self.results.append(metrics)
        log.debug(f"Added metrics for {task_id} run {run_id}: {metrics}")
    
    def calculate_pass_at_k(self, k: int) -> float:
        """
        Calculate pass@k metric: fraction of tasks where ≥1 of top-k runs passed.
        
        Args:
            k: Number of attempts per task to consider
            
        Returns:
            pass@k score between 0.0 and 1.0
        """
        if not self.results:
            return 0.0
        
        # Group results by task
        tasks = {}
        for result in self.results:
            if result.task_id not in tasks:
                tasks[result.task_id] = []
            tasks[result.task_id].append(result)
        
        passed_tasks = 0
        total_tasks = len(tasks)
        
        for task_id, task_results in tasks.items():
            # Take top-k results (by run_id order)
            top_k_results = sorted(task_results, key=lambda x: x.run_id)[:k]
            
            # Check if any passed
            if any(r.success for r in top_k_results):
                passed_tasks += 1
        
        return passed_tasks / total_tasks if total_tasks > 0 else 0.0
    
    def calculate_eff_at_k_runtime(self, k: int) -> float:
        """
        Calculate eff@k_runtime: fraction of tasks where ≥1 of top-k runs met time limit.
        
        Args:
            k: Number of attempts per task to consider
            
        Returns:
            eff@k_runtime score between 0.0 and 1.0
        """
        if not self.results:
            return 0.0
        
        tasks = {}
        for result in self.results:
            if result.task_id not in tasks:
                tasks[result.task_id] = []
            tasks[result.task_id].append(result)
        
        efficient_tasks = 0
        total_tasks = len(tasks)
        
        for task_id, task_results in tasks.items():
            top_k_results = sorted(task_results, key=lambda x: x.run_id)[:k]
            
            # Check if any met runtime efficiency
            if any(r.success and r.efficient_runtime for r in top_k_results):
                efficient_tasks += 1
        
        return efficient_tasks / total_tasks if total_tasks > 0 else 0.0
    
    def calculate_eff_at_k_memory(self, k: int) -> float:
        """
        Calculate eff@k_memory: fraction of tasks where ≥1 of top-k runs met memory limit.
        
        Args:
            k: Number of attempts per task to consider
            
        Returns:
            eff@k_memory score between 0.0 and 1.0
        """
        if not self.results:
            return 0.0
        
        tasks = {}
        for result in self.results:
            if result.task_id not in tasks:
                tasks[result.task_id] = []
            tasks[result.task_id].append(result)
        
        efficient_tasks = 0
        total_tasks = len(tasks)
        
        for task_id, task_results in tasks.items():
            top_k_results = sorted(task_results, key=lambda x: x.run_id)[:k]
            
            # Check if any met memory efficiency
            if any(r.success and r.efficient_memory for r in top_k_results):
                efficient_tasks += 1
        
        return efficient_tasks / total_tasks if total_tasks > 0 else 0.0
    
    def calculate_tle_mle_rate(self) -> Tuple[float, float]:
        """
        Calculate TLE/MLE rates: % of executions exceeding runtime or memory cap.
        
        Returns:
            Tuple of (TLE_rate, MLE_rate) as percentages between 0.0 and 100.0
        """
        if not self.results:
            return 0.0, 0.0
        
        total_runs = len(self.results)
        tle_count = 0
        mle_count = 0
        
        for result in self.results:
            if result.status == RunStatus.TLE or not result.efficient_runtime:
                tle_count += 1
            if result.status == RunStatus.MLE or not result.efficient_memory:
                mle_count += 1
        
        tle_rate = (tle_count / total_runs) * 100.0
        mle_rate = (mle_count / total_runs) * 100.0
        
        return tle_rate, mle_rate
    
    def calculate_mean_iterations(self) -> float:
        """
        Calculate mean iteration count until efficient==true.
        
        Returns:
            Mean number of iterations across all successful runs
        """
        if not self.results:
            return 0.0
        
        successful_runs = [r for r in self.results if r.success]
        if not successful_runs:
            return 0.0
        
        total_iterations = sum(r.iteration_count for r in successful_runs)
        return total_iterations / len(successful_runs)
    
    def calculate_agent_failure_rate(self) -> float:
        """
        Calculate agent failure rate: % of runs that failed due to agent errors.
        
        Returns:
            Failure rate as percentage between 0.0 and 100.0
        """
        if not self.results:
            return 0.0
        
        total_runs = len(self.results)
        failure_runs = sum(1 for r in self.results if r.status == RunStatus.AGENT_FAILURE)
        
        return (failure_runs / total_runs) * 100.0
    
    def generate_summary(self, k_values: List[int] = [1, 3, 5]) -> Dict[str, Any]:
        """
        Generate comprehensive evaluation summary.
        
        Args:
            k_values: List of k values to calculate metrics for
            
        Returns:
            Dictionary containing all evaluation metrics
        """
        if not self.results:
            return {"error": "No results available for evaluation"}
        
        # Calculate metrics for different k values
        pass_at_k = {f"pass@{k}": self.calculate_pass_at_k(k) for k in k_values}
        eff_runtime_at_k = {f"eff@{k}_runtime": self.calculate_eff_at_k_runtime(k) for k in k_values}
        eff_memory_at_k = {f"eff@{k}_memory": self.calculate_eff_at_k_memory(k) for k in k_values}
        
        # Calculate other metrics
        tle_rate, mle_rate = self.calculate_tle_mle_rate()
        mean_iterations = self.calculate_mean_iterations()
        agent_failure_rate = self.calculate_agent_failure_rate()
        
        # Task and run statistics
        unique_tasks = len(set(r.task_id for r in self.results))
        total_runs = len(self.results)
        successful_runs = sum(1 for r in self.results if r.success)
        
        # Performance statistics
        runtime_stats = self._calculate_runtime_stats()
        memory_stats = self._calculate_memory_stats()
        
        summary = {
            "evaluation_summary": {
                "total_tasks": unique_tasks,
                "total_runs": total_runs,
                "successful_runs": successful_runs,
                "success_rate": (successful_runs / total_runs) * 100.0 if total_runs > 0 else 0.0
            },
            "pass_metrics": pass_at_k,
            "efficiency_metrics": {
                **eff_runtime_at_k,
                **eff_memory_at_k
            },
            "limit_exceeded_rates": {
                "tle_rate_percent": tle_rate,
                "mle_rate_percent": mle_rate
            },
            "convergence_metrics": {
                "mean_iterations_to_success": mean_iterations,
                "agent_failure_rate_percent": agent_failure_rate
            },
            "performance_statistics": {
                "runtime_ms": runtime_stats,
                "memory_mb": memory_stats
            }
        }
        
        return summary
    
    def _calculate_runtime_stats(self) -> Dict[str, float]:
        """Calculate runtime statistics for successful runs."""
        runtimes = [r.final_runtime_ms for r in self.results 
                   if r.success and r.final_runtime_ms is not None]
        
        if not runtimes:
            return {"count": 0}
        
        return {
            "count": len(runtimes),
            "mean": float(np.mean(runtimes)),
            "median": float(np.median(runtimes)),
            "std": float(np.std(runtimes)),
            "min": float(np.min(runtimes)),
            "max": float(np.max(runtimes)),
            "p95": float(np.percentile(runtimes, 95))
        }
    
    def _calculate_memory_stats(self) -> Dict[str, float]:
        """Calculate memory statistics for successful runs."""
        memories = [r.final_memory_mb for r in self.results 
                   if r.success and r.final_memory_mb is not None]
        
        if not memories:
            return {"count": 0}
        
        return {
            "count": len(memories),
            "mean": float(np.mean(memories)),
            "median": float(np.median(memories)),
            "std": float(np.std(memories)),
            "min": float(np.min(memories)),
            "max": float(np.max(memories)),
            "p95": float(np.percentile(memories, 95))
        }
    
    def save_results(self, output_file: Path) -> None:
        """
        Save detailed results to JSON file.
        
        Args:
            output_file: Path to save results
        """
        results_data = {
            "evaluation_metadata": {
                "total_results": len(self.results),
                "unique_tasks": len(set(r.task_id for r in self.results)),
                "timestamp": "2025-01-01T00:00:00Z"  # Would use actual timestamp
            },
            "results": [
                {
                    "task_id": r.task_id,
                    "run_id": r.run_id,
                    "status": r.status.value,
                    "success": r.success,
                    "efficient_runtime": r.efficient_runtime,
                    "efficient_memory": r.efficient_memory,
                    "iteration_count": r.iteration_count,
                    "final_runtime_ms": r.final_runtime_ms,
                    "final_memory_mb": r.final_memory_mb,
                    "runtime_limit_ms": r.runtime_limit_ms,
                    "memory_limit_mb": r.memory_limit_mb,
                    "agent_failures": r.agent_failures
                }
                for r in self.results
            ],
            "summary": self.generate_summary()
        }
        
        with open(output_file, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        log.info(f"Saved evaluation results to {output_file}")
    
    def load_results(self, input_file: Path) -> None:
        """
        Load results from JSON file.
        
        Args:
            input_file: Path to load results from
        """
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        self.results = []
        for r in data.get('results', []):
            metrics = RunMetrics(
                task_id=r['task_id'],
                run_id=r['run_id'],
                status=RunStatus(r['status']),
                success=r['success'],
                efficient_runtime=r['efficient_runtime'],
                efficient_memory=r['efficient_memory'],
                iteration_count=r['iteration_count'],
                final_runtime_ms=r.get('final_runtime_ms'),
                final_memory_mb=r.get('final_memory_mb'),
                runtime_limit_ms=r['runtime_limit_ms'],
                memory_limit_mb=r['memory_limit_mb'],
                agent_failures=r['agent_failures']
            )
            self.results.append(metrics)
        
        log.info(f"Loaded {len(self.results)} evaluation results from {input_file}")


def create_sample_evaluation() -> EvaluationMetrics:
    """Create sample evaluation data for testing."""
    metrics = EvaluationMetrics()
    
    # Simulate results for 3 tasks with multiple runs each
    tasks = ["SAMPLE_001", "SAMPLE_002", "SAMPLE_003"]
    
    for task_id in tasks:
        for run_id in range(3):  # 3 runs per task
            # Simulate varying success rates and efficiency
            success = run_id < 2  # First 2 runs succeed
            runtime_ms = 1500 if success else 3000  # Some exceed limits
            memory_mb = 400 if success else 600
            
            result = {
                "status": "success" if success else "failed",
                "profile": {
                    "runtime_ms": [runtime_ms],
                    "peak_memory_mb": [memory_mb]
                },
                "iteration": run_id + 1
            }
            
            metrics.add_run_result(
                task_id=task_id,
                run_id=run_id,
                result=result,
                runtime_limit=2000,
                memory_limit=512
            )
    
    return metrics


if __name__ == "__main__":
    # Create and test sample evaluation
    metrics = create_sample_evaluation()
    summary = metrics.generate_summary()
    
    print("Sample Evaluation Summary:")
    print(json.dumps(summary, indent=2))