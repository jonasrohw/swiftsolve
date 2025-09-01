# baseline/evaluation.py
"""
Baseline Evaluation Module
==========================

Implements the baseline evaluation pipeline that mirrors the research evaluation
but uses Claude 4 Opus directly instead of the SwiftSolve multi-agent system.

This serves as a robust baseline for comparison against SwiftSolve.
"""

import json
import time
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .pipeline import run_baseline_pipeline
from ..research.evaluation import ResearchDatasetCurator, ResearchRunResult
from ..schemas import ProblemInput
from ..utils.logger import get_logger

log = get_logger("BaselineEval")


@dataclass
class BaselineRunResult:
    """Results from a single baseline evaluation run."""
    task_id: str
    seed: int
    replan_id: int  # Keep for consistency, always 0 for baseline
    status: str
    duration_seconds: float
    final_code: Optional[str] = None
    iterations_used: int = 1  # Always 1 for baseline
    agent_failures: int = 0
    error_details: Optional[str] = None
    
    # Enhanced data collection (same as research evaluation)
    profile_report: Optional[Dict[str, Any]] = None
    constraints: Optional[Dict[str, int]] = None
    tle_flags: Optional[List[bool]] = None
    mle_flags: Optional[List[bool]] = None
    actual_iterations: int = 1  # Always 1 for baseline


class BaselineEvaluationRunner:
    """Runs baseline evaluation using Claude 4 Opus directly on the same dataset as research evaluation."""
    
    def __init__(self, output_dir: Path, max_workers: int = 4):
        """Initialize baseline evaluation runner."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        
        log.info(f"🤖 Baseline Evaluation Runner initialized")
        log.info(f"📁 Output directory: {self.output_dir}")
        log.info(f"⚡ Max workers: {self.max_workers}")
    
    def run_full_evaluation(self, seeds: List[int] = [42, 123, 456], mini_run: bool = False) -> Dict[str, Any]:
        """
        Run the baseline evaluation on the same dataset as research evaluation.
        
        Args:
            seeds: List of random seeds (default: 3 seeds)
            mini_run: If True, run mini version with 2 tasks
            
        Returns:
            Comprehensive evaluation results and statistics
        """
        # Generate evaluation ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "mini_baseline_eval" if mini_run else "baseline_eval"
        evaluation_id = f"{prefix}_{timestamp}"
        
        if mini_run:
            log.info("🚀 Starting MINI baseline evaluation (6 iterations)")
            log.info("=" * 60)
            tasks = ResearchDatasetCurator.create_mini_dataset()
        else:
            log.info("🚀 Starting FULL baseline evaluation (75 iterations)")
            log.info("=" * 60)
            tasks = ResearchDatasetCurator.create_curated_dataset()
        
        start_time = time.time()
        results = []
        
        log.info(f"📊 Dataset: {len(tasks)} tasks × {len(seeds)} seeds = {len(tasks) * len(seeds)} total runs")
        log.info(f"🤖 Using Claude 4 Opus directly (single attempt per problem, no replanning)")
        
        # Generate all job specifications (single attempt per task-seed combination)
        jobs = []
        for task in tasks:
            for seed in seeds:
                job = {
                    'task': task,
                    'seed': seed,
                    'replan_id': 0,  # Always 0 for baseline (no replanning)
                    'job_id': f"{task.task_id}_seed{seed}"
                }
                jobs.append(job)
        
        total_jobs = len(jobs)
        log.info(f"🎯 Total jobs to execute: {total_jobs}")
        log.info("🔄 Starting sequential execution...")
        
        for i, job in enumerate(jobs):
            try:
                result = self._run_single_job(job)
                results.append(result)
                
                # Progress logging
                completed = i + 1
                if completed % 10 == 0 or completed == total_jobs:
                    elapsed = time.time() - start_time
                    rate = completed / elapsed if elapsed > 0 else 0
                    eta = (total_jobs - completed) / rate if rate > 0 else 0
                    
                    log.info(f"📈 Progress: {completed}/{total_jobs} ({completed/total_jobs*100:.1f}%) "
                           f"| Rate: {rate:.1f} jobs/min | ETA: {eta/60:.1f}min")
                    
                    # Status breakdown for recent jobs
                    recent_results = results[-10:] if len(results) >= 10 else results
                    success_count = sum(1 for r in recent_results if r.status == "success")
                    success_rate = success_count / len(recent_results) * 100
                    log.info(f"   Recent success rate: {success_rate:.1f}%")
                
            except Exception as e:
                log.error(f"❌ Job {job['job_id']} failed: {e}")
                
                # Create failure result
                error_result = BaselineRunResult(
                    task_id=job['task'].task_id,
                    seed=job['seed'],
                    replan_id=job['replan_id'],
                    status="agent_failure",
                    duration_seconds=0.0,
                    error_details=str(e),
                    constraints={
                        "runtime_limit": job['task'].time_limit_ms,
                        "memory_limit": job['task'].memory_limit_mb
                    }
                )
                results.append(error_result)
        
        total_duration = time.time() - start_time
        log.info(f"✅ Baseline evaluation completed in {total_duration/60:.1f} minutes")
        
        # Generate comprehensive analysis
        analysis = self._analyze_results(results, total_duration)
        
        # Save results
        self._save_results(results, analysis, evaluation_id)
        
        return analysis
    
    def _run_single_job(self, job: Dict[str, Any]) -> BaselineRunResult:
        """Run a single baseline evaluation job."""
        task = job['task']
        seed = job['seed']
        replan_id = job['replan_id']
        
        start_time = time.time()
        
        try:
            # Create problem input from task metadata
            # For baseline, we don't modify the prompt based on replan_id
            # since Claude 4 Opus should handle replanning internally
            problem = ProblemInput(
                task_id=f"{task.task_id}_seed{seed}_replan{replan_id}",
                prompt=task.description,
                constraints={
                    "runtime_limit": task.time_limit_ms,
                    "memory_limit": task.memory_limit_mb
                },
                unit_tests=[{"input": tc.input, "output": tc.output} for tc in task.test_cases[:3]]
            )
            
            # Run baseline pipeline (Claude 4 Opus → Profiler)
            result = run_baseline_pipeline(problem)
            
            duration = time.time() - start_time
            
            # Parse result and extract relevant data (same format as research evaluation)
            status = self._parse_run_status(result)
            final_code = result.get('code') if isinstance(result, dict) else None
            
            # Store original constraints for TLE/MLE analysis
            original_constraints = {
                "runtime_limit": task.time_limit_ms,
                "memory_limit": task.memory_limit_mb
            }
            
            # Enhanced data extraction for research analysis
            profile_report = None
            tle_flags = None
            mle_flags = None
            
            if isinstance(result, dict) and 'profile' in result and result['profile']:
                # Extract ProfileReport data
                profile = result['profile']
                if hasattr(profile, 'model_dump'):
                    profile_report = profile.model_dump()
                elif isinstance(profile, dict):
                    profile_report = profile
                
                # Compute TLE/MLE flags if we have profile data
                if profile_report and 'runtime_ms' in profile_report and 'peak_memory_mb' in profile_report:
                    tle_flags = self._compute_tle_flags(
                        profile_report['runtime_ms'], 
                        original_constraints['runtime_limit']
                    )
                    mle_flags = self._compute_mle_flags(
                        profile_report['peak_memory_mb'], 
                        original_constraints['memory_limit']
                    )
            
            return BaselineRunResult(
                task_id=task.task_id,
                seed=seed,
                replan_id=replan_id,
                status=status,
                duration_seconds=duration,
                final_code=final_code,
                iterations_used=1,  # Always 1 for baseline
                agent_failures=0,  # Set based on actual failures if any
                profile_report=profile_report,
                constraints=original_constraints,
                tle_flags=tle_flags,
                mle_flags=mle_flags,
                actual_iterations=1  # Always 1 for baseline
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return BaselineRunResult(
                task_id=task.task_id,
                seed=seed,
                replan_id=replan_id,
                status="agent_failure",
                duration_seconds=duration,
                error_details=str(e),
                constraints={
                    "runtime_limit": task.time_limit_ms,
                    "memory_limit": task.memory_limit_mb
                },
                actual_iterations=1
            )
    
    def _parse_run_status(self, result: Any) -> str:
        """Parse pipeline result into standardized status."""
        if isinstance(result, dict):
            status_str = result.get('status', 'unknown')
            if status_str == 'success':
                return "success"
            elif status_str == 'agent_failure':
                return "agent_failure"
            elif status_str == 'failed':
                return "timeout"
            else:
                return "unknown"
        else:
            return "unknown"
    
    def _compute_tle_flags(self, runtime_ms: List[float], limit_ms: int) -> List[bool]:
        """Compute TLE flags for each input size."""
        return [
            runtime >= limit_ms or runtime == float('inf') or runtime is None
            for runtime in runtime_ms
        ]
    
    def _compute_mle_flags(self, memory_mb: List[float], limit_mb: int) -> List[bool]:
        """Compute MLE flags for each input size."""
        return [
            memory >= limit_mb or memory is None
            for memory in memory_mb
        ]
    
    def _analyze_results(self, results: List[BaselineRunResult], total_duration: float) -> Dict[str, Any]:
        """Generate comprehensive analysis of baseline evaluation results."""
        log.info("📊 Analyzing baseline evaluation results...")
        
        total_runs = len(results)
        successful_runs = [r for r in results if r.status == "success"]
        
        # Basic statistics
        success_rate = len(successful_runs) / total_runs * 100 if total_runs > 0 else 0
        avg_duration = sum(r.duration_seconds for r in results) / total_runs if total_runs > 0 else 0
        
        # Status breakdown
        status_counts = {}
        for result in results:
            status_counts[result.status] = status_counts.get(result.status, 0) + 1
        
        # Task-by-task analysis (no replanning in baseline)
        task_analysis = {}
        for task_id in set(r.task_id for r in results):
            task_results = [r for r in results if r.task_id == task_id]
            task_success = [r for r in task_results if r.status == "success"]
            
            task_analysis[task_id] = {
                "total_runs": len(task_results),
                "successful_runs": len(task_success),
                "success_rate": len(task_success) / len(task_results) * 100 if task_results else 0,
                "avg_duration": sum(r.duration_seconds for r in task_results) / len(task_results) if task_results else 0
            }
        
        analysis = {
            "evaluation_summary": {
                "total_runs": total_runs,
                "successful_runs": len(successful_runs),
                "success_rate_percent": success_rate,
                "total_duration_minutes": total_duration / 60,
                "avg_duration_per_run_seconds": avg_duration
            },
            "status_breakdown": status_counts,
            "task_analysis": task_analysis,
            "baseline_insights": {
                "agent_type": "Claude 4 Opus Direct (Single Attempt)",
                "dataset_source_performance": self._analyze_by_source(results),
                "iteration_consistency": "Always 1 iteration per run",
                "no_replanning": "Single attempt per task-seed combination"
            }
        }
        
        return analysis
    
    def _analyze_by_source(self, results: List[BaselineRunResult]) -> Dict[str, Dict[str, float]]:
        """Analyze performance by dataset source."""
        bigobench_results = [r for r in results if r.task_id.startswith('bigobench_')]
        codeforces_results = [r for r in results if r.task_id.startswith('cf_')]
        
        def calc_stats(result_list):
            if not result_list:
                return {"success_rate": 0.0, "avg_duration": 0.0, "count": 0}
            
            successful = [r for r in result_list if r.status == "success"]
            return {
                "success_rate": len(successful) / len(result_list) * 100,
                "avg_duration": sum(r.duration_seconds for r in result_list) / len(result_list),
                "count": len(result_list)
            }
        
        return {
            "bigobench": calc_stats(bigobench_results),
            "codeforces": calc_stats(codeforces_results)
        }
    
    def _save_results(self, results: List[BaselineRunResult], analysis: Dict[str, Any], evaluation_id: str):
        """Save baseline evaluation results and analysis to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results
        results_file = self.output_dir / f"baseline_results_{timestamp}.json"
        results_data = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_runs": len(results),
                "evaluation_type": "baseline_claude4_opus_single_attempt",
                "evaluation_id": evaluation_id,
                "status": "complete",
                "agent_description": "Claude 4 Opus direct solution generation (single attempt) followed by profiling"
            },
            "results": [self._serialize_result(r) for r in results]
        }
        
        with open(results_file, 'w') as f:
            json.dump(results_data, f, indent=2, default=str)
        
        # Save analysis
        analysis_file = self.output_dir / f"baseline_analysis_{timestamp}.json"
        with open(analysis_file, 'w') as f:
            json.dump(analysis, f, indent=2, default=str)
        
        log.info("💾 Baseline results saved:")
        log.info(f"   📊 Detailed results: {results_file}")
        log.info(f"   📈 Analysis: {analysis_file}")
    
    def _serialize_result(self, result: BaselineRunResult) -> Dict[str, Any]:
        """Serialize a baseline result for JSON storage."""
        base_result = {
            "task_id": result.task_id,
            "seed": result.seed,
            "replan_id": result.replan_id,
            "status": result.status,
            "duration_seconds": result.duration_seconds,
            "final_code": result.final_code,
            "iterations_used": result.iterations_used,
            "agent_failures": result.agent_failures,
            "error_details": result.error_details,
            "actual_iterations": result.actual_iterations
        }
        
        # Add enhanced research data if available
        if result.profile_report:
            base_result["profile_report"] = result.profile_report
            
        if result.constraints:
            base_result["constraints"] = result.constraints
            
        if result.tle_flags is not None:
            base_result["tle_analysis"] = {
                "tle_flags": result.tle_flags,
                "tle_count": sum(result.tle_flags),
                "tle_rate": sum(result.tle_flags) / len(result.tle_flags) if result.tle_flags else 0.0,
                "total_input_sizes": len(result.tle_flags)
            }
            
        if result.mle_flags is not None:
            base_result["mle_analysis"] = {
                "mle_flags": result.mle_flags,
                "mle_count": sum(result.mle_flags),
                "mle_rate": sum(result.mle_flags) / len(result.mle_flags) if result.mle_flags else 0.0,
                "total_input_sizes": len(result.mle_flags)
            }
        
        return base_result
