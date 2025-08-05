"""
Batch Runner for Systematic Benchmarking

Implements the batch runner specified in CONTEXT.md section 4.2 Phase D:
- CLI flags: --benchmark, --seeds, --replans
- Multiprocess pool, progress bar (tqdm)
- Store artifacts under results/<task>/seed_<s>/

Enables large-scale evaluation runs for research benchmarking.
"""

import argparse
import json
import time
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import cpu_count
import traceback

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Warning: tqdm not available. Progress bars will not be shown.")

from ..controller.solve_loop import run_pipeline
from ..schemas import ProblemInput
from ..datasets.task_format import TaskMetadata, create_problem_input
from ..evaluation.metrics import EvaluationMetrics
from ..utils.logger import get_logger
from ..utils.config import get_settings

log = get_logger("BatchRunner")


class BatchRunner:
    """Batch runner for systematic SwiftSolve evaluation."""
    
    def __init__(self, output_dir: Path, max_workers: Optional[int] = None):
        """
        Initialize batch runner.
        
        Args:
            output_dir: Directory to store results
            max_workers: Maximum number of parallel workers (default: CPU count)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers or min(cpu_count(), 8)  # Limit to 8 for stability
        
        log.info(f"Initialized batch runner with {self.max_workers} workers")
        log.info(f"Results will be stored in: {self.output_dir}")
    
    def load_tasks(self, dataset_dirs: List[Path]) -> List[TaskMetadata]:
        """
        Load tasks from dataset directories.
        
        Args:
            dataset_dirs: List of dataset directories to load from
            
        Returns:
            List of loaded task metadata
        """
        tasks = []
        
        for dataset_dir in dataset_dirs:
            log.info(f"Loading tasks from {dataset_dir}")
            
            # Look for index.json first
            index_file = dataset_dir / "index.json"
            if index_file.exists():
                tasks.extend(self._load_from_index(dataset_dir, index_file))
            else:
                # Fallback: scan for individual task files
                tasks.extend(self._load_from_files(dataset_dir))
        
        log.info(f"Loaded {len(tasks)} total tasks")
        return tasks
    
    def _load_from_index(self, dataset_dir: Path, index_file: Path) -> List[TaskMetadata]:
        """Load tasks using index file."""
        tasks = []
        
        try:
            with open(index_file, 'r') as f:
                index = json.load(f)
            
            for task_info in index.get('tasks', []):
                task_file = dataset_dir / task_info['file']
                if task_file.exists():
                    try:
                        with open(task_file, 'r') as f:
                            task_data = json.load(f)
                        task = TaskMetadata.model_validate(task_data)
                        tasks.append(task)
                    except Exception as e:
                        log.warning(f"Failed to load task {task_file}: {e}")
                        
        except Exception as e:
            log.error(f"Failed to load index {index_file}: {e}")
        
        return tasks
    
    def _load_from_files(self, dataset_dir: Path) -> List[TaskMetadata]:
        """Load tasks by scanning for JSON files."""
        tasks = []
        
        for task_file in dataset_dir.glob("task_*.json"):
            try:
                with open(task_file, 'r') as f:
                    task_data = json.load(f)
                task = TaskMetadata.model_validate(task_data)
                tasks.append(task)
            except Exception as e:
                log.warning(f"Failed to load task {task_file}: {e}")
        
        return tasks
    
    def run_benchmark(self, tasks: List[TaskMetadata], seeds: List[int], 
                     runs_per_task: int = 1, timeout_per_run: int = 300) -> Dict[str, Any]:
        """
        Run benchmark evaluation on tasks.
        
        Args:
            tasks: List of tasks to evaluate
            seeds: List of random seeds for reproducibility
            runs_per_task: Number of runs per task per seed
            timeout_per_run: Timeout per individual run in seconds
            
        Returns:
            Summary of benchmark results
        """
        log.info(f"Starting benchmark: {len(tasks)} tasks × {len(seeds)} seeds × {runs_per_task} runs")
        
        # Create all job specifications
        jobs = []
        for task in tasks:
            for seed in seeds:
                for run_id in range(runs_per_task):
                    job = {
                        'task': task,
                        'seed': seed,
                        'run_id': run_id,
                        'timeout': timeout_per_run
                    }
                    jobs.append(job)
        
        total_jobs = len(jobs)
        log.info(f"Total jobs to execute: {total_jobs}")
        
        # Execute jobs in parallel
        results = []
        failed_jobs = []
        
        progress_bar = None
        if TQDM_AVAILABLE:
            progress_bar = tqdm(total=total_jobs, desc="Running benchmark")
        
        try:
            with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all jobs
                future_to_job = {
                    executor.submit(self._run_single_job, job): job 
                    for job in jobs
                }
                
                # Collect results
                for future in as_completed(future_to_job):
                    job = future_to_job[future]
                    
                    try:
                        result = future.result()
                        if result:
                            results.append(result)
                            self._save_individual_result(result)
                        else:
                            failed_jobs.append(job)
                    except Exception as e:
                        log.error(f"Job failed: {job['task'].task_id} seed={job['seed']} run={job['run_id']}: {e}")
                        failed_jobs.append(job)
                    
                    if progress_bar:
                        progress_bar.update(1)
        
        finally:
            if progress_bar:
                progress_bar.close()
        
        # Generate summary
        summary = {
            'total_jobs': total_jobs,
            'successful_jobs': len(results),
            'failed_jobs': len(failed_jobs),
            'success_rate': len(results) / total_jobs * 100 if total_jobs > 0 else 0,
            'unique_tasks': len(set(r['task_id'] for r in results)),
            'seeds_used': seeds,
            'runs_per_task': runs_per_task
        }
        
        log.info(f"Benchmark completed: {summary['successful_jobs']}/{total_jobs} jobs successful")
        return summary
    
    def _run_single_job(self, job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Execute a single benchmark job.
        
        Args:
            job: Job specification with task, seed, run_id, timeout
            
        Returns:
            Job result or None if failed
        """
        task = job['task']
        seed = job['seed']
        run_id = job['run_id']
        
        # Set random seed for reproducibility
        random.seed(seed)
        
        try:
            # Convert task to problem input
            problem_input_data = create_problem_input(task)
            problem = ProblemInput.model_validate(problem_input_data)
            
            # Run pipeline
            start_time = time.time()
            result = run_pipeline(problem)
            end_time = time.time()
            
            # Package result
            job_result = {
                'task_id': task.task_id,
                'seed': seed,
                'run_id': run_id,
                'result': result,
                'execution_time_sec': end_time - start_time,
                'timestamp': time.time(),
                'task_metadata': {
                    'difficulty': task.difficulty.value,
                    'expected_complexity': task.expected_complexity.value,
                    'time_limit_ms': task.time_limit_ms,
                    'memory_limit_mb': task.memory_limit_mb
                }
            }
            
            return job_result
            
        except Exception as e:
            log.error(f"Job execution failed: {task.task_id} seed={seed} run={run_id}: {e}")
            log.debug(traceback.format_exc())
            return None
    
    def _save_individual_result(self, result: Dict[str, Any]) -> None:
        """
        Save individual result to file.
        
        Args:
            result: Job result to save
        """
        task_id = result['task_id']
        seed = result['seed']
        run_id = result['run_id']
        
        # Create directory structure: results/<task>/seed_<s>/
        task_dir = self.output_dir / task_id
        seed_dir = task_dir / f"seed_{seed}"
        seed_dir.mkdir(parents=True, exist_ok=True)
        
        # Save result
        result_file = seed_dir / f"run_{run_id}.json"
        with open(result_file, 'w') as f:
            json.dump(result, f, indent=2)
    
    def generate_evaluation_report(self, k_values: List[int] = [1, 3, 5]) -> Path:
        """
        Generate comprehensive evaluation report from all results.
        
        Args:
            k_values: List of k values for pass@k and eff@k metrics
            
        Returns:
            Path to generated report
        """
        log.info("Generating evaluation report from all results")
        
        # Collect all results
        metrics = EvaluationMetrics()
        
        for result_file in self.output_dir.rglob("run_*.json"):
            try:
                with open(result_file, 'r') as f:
                    data = json.load(f)
                
                # Extract information for metrics
                task_id = data['task_id']
                run_id = data['run_id']
                result = data['result']
                task_meta = data['task_metadata']
                
                metrics.add_run_result(
                    task_id=task_id,
                    run_id=run_id,
                    result=result,
                    runtime_limit=task_meta['time_limit_ms'],
                    memory_limit=task_meta['memory_limit_mb']
                )
                
            except Exception as e:
                log.warning(f"Failed to process result file {result_file}: {e}")
        
        # Generate and save evaluation summary
        summary = metrics.generate_summary(k_values)
        
        report_file = self.output_dir / "evaluation_summary.json"
        with open(report_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        # Save detailed results
        metrics.save_results(self.output_dir / "detailed_results.json")
        
        log.info(f"Generated evaluation report: {report_file}")
        return report_file


def create_sample_datasets(dataset_dir: Path) -> None:
    """Create sample datasets for testing batch runner."""
    from ..datasets.parse_bigobench import create_sample_bigobench_dataset
    from ..datasets.parse_codeforces import create_sample_codeforces_dataset
    
    log.info(f"Creating sample datasets in {dataset_dir}")
    
    create_sample_bigobench_dataset(dataset_dir)
    create_sample_codeforces_dataset(dataset_dir)
    
    log.info("Sample datasets created")


def main():
    """Main CLI entry point for batch runner."""
    parser = argparse.ArgumentParser(description="SwiftSolve Batch Benchmarking Runner")
    
    parser.add_argument("--benchmark", action="store_true", 
                       help="Run benchmark evaluation")
    parser.add_argument("--datasets", nargs="+", default=["datasets/bigobench", "datasets/codeforces"],
                       help="Dataset directories to load tasks from")
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 123, 456],
                       help="Random seeds for reproducibility")
    parser.add_argument("--runs", type=int, default=1,
                       help="Number of runs per task per seed")
    parser.add_argument("--workers", type=int, default=None,
                       help="Number of parallel workers")
    parser.add_argument("--timeout", type=int, default=300,
                       help="Timeout per run in seconds")
    parser.add_argument("--output", default="results",
                       help="Output directory for results")
    parser.add_argument("--create-samples", action="store_true",
                       help="Create sample datasets for testing")
    
    args = parser.parse_args()
    
    if args.create_samples:
        create_sample_datasets(Path("datasets"))
        return
    
    if not args.benchmark:
        print("Use --benchmark to run evaluation or --create-samples to create test data")
        return
    
    # Initialize batch runner
    runner = BatchRunner(Path(args.output), max_workers=args.workers)
    
    # Load tasks
    dataset_paths = [Path(d) for d in args.datasets]
    tasks = runner.load_tasks(dataset_paths)
    
    if not tasks:
        log.error("No tasks loaded. Check dataset paths or use --create-samples first.")
        return
    
    # Run benchmark
    log.info(f"Starting benchmark with {len(tasks)} tasks")
    summary = runner.run_benchmark(
        tasks=tasks,
        seeds=args.seeds,
        runs_per_task=args.runs,
        timeout_per_run=args.timeout
    )
    
    print(f"\nBenchmark Summary:")
    print(f"  Total Jobs: {summary['total_jobs']}")
    print(f"  Successful: {summary['successful_jobs']}")
    print(f"  Failed: {summary['failed_jobs']}")
    print(f"  Success Rate: {summary['success_rate']:.1f}%")
    print(f"  Unique Tasks: {summary['unique_tasks']}")
    
    # Generate evaluation report
    report_file = runner.generate_evaluation_report()
    print(f"  Evaluation Report: {report_file}")


if __name__ == "__main__":
    main()