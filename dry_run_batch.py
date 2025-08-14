#!/usr/bin/env python3
"""
SwiftSolve Dry-Run Batch Mode

A standalone program that runs SwiftSolve on a predefined set of tasks with varying difficulties.
No external datasets required - includes 10 hardcoded tasks: 3 easy, 5 medium, 2 hard.

Usage:
    python dry_run_batch.py [--tasks N] [--host HOST] [--port PORT] [--timeout SECONDS]

Examples:
    python dry_run_batch.py --tasks 5                    # Run first 5 tasks
    python dry_run_batch.py --tasks 10                   # Run all 10 tasks
    python dry_run_batch.py --tasks 3 --timeout 120     # Run 3 tasks with 2min timeout each
"""

import argparse
import asyncio
import json
import time
from datetime import datetime
from typing import List, Dict, Any
import aiohttp
import sys
from pathlib import Path


# Predefined task set: 3 Easy + 5 Medium + 2 Hard
TASK_SET = [
    # === EASY TASKS (3) ===
    {
        "task_id": "EASY_ADD_TWO_NUMBERS",
        "difficulty": "EASY",
        "prompt": "Read two integers and output their sum. Input format: Two integers on separate lines. Output format: Single integer (the sum).",
        "constraints": {"runtime_limit": 1000, "memory_limit": 256},
        "unit_tests": [
            {"input": "5\n3", "output": "8"},
            {"input": "10\n-2", "output": "8"},
            {"input": "0\n0", "output": "0"},
            {"input": "1000000\n999999", "output": "1999999"}
        ]
    },
    {
        "task_id": "EASY_FIND_MAXIMUM",
        "difficulty": "EASY", 
        "prompt": "Find the maximum element in an array of integers. Input format: First line contains n, second line contains n space-separated integers. Output format: Single integer (the maximum).",
        "constraints": {"runtime_limit": 2000, "memory_limit": 512},
        "unit_tests": [
            {"input": "3\n1 3 2", "output": "3"},
            {"input": "5\n1 3 2 8 5", "output": "8"},
            {"input": "1\n42", "output": "42"},
            {"input": "4\n-5 -1 -10 -3", "output": "-1"}
        ]
    },
    {
        "task_id": "EASY_COUNT_VOWELS",
        "difficulty": "EASY",
        "prompt": "Count the number of vowels (a, e, i, o, u) in a string. Input format: Single line with a string. Output format: Single integer (vowel count).",
        "constraints": {"runtime_limit": 1000, "memory_limit": 256},
        "unit_tests": [
            {"input": "hello", "output": "2"},
            {"input": "programming", "output": "3"},
            {"input": "xyz", "output": "0"},
            {"input": "aeiou", "output": "5"}
        ]
    },

    # === MEDIUM TASKS (5) ===
    {
        "task_id": "MEDIUM_BINARY_SEARCH",
        "difficulty": "MEDIUM",
        "prompt": "Implement binary search on a sorted array. Find the index of target element (0-based). Input format: First line contains n and target, second line contains n sorted integers. Output format: Index of target, or -1 if not found.",
        "constraints": {"runtime_limit": 2000, "memory_limit": 512},
        "unit_tests": [
            {"input": "5 3\n1 2 3 4 5", "output": "2"},
            {"input": "5 6\n1 2 3 4 5", "output": "-1"},
            {"input": "4 1\n1 3 5 7", "output": "0"},
            {"input": "6 7\n1 3 5 7 9 11", "output": "3"}
        ]
    },
    {
        "task_id": "MEDIUM_MERGE_INTERVALS",
        "difficulty": "MEDIUM",
        "prompt": "Merge overlapping intervals. Input format: First line contains n, then n lines each with two integers (start, end). Output format: Merged intervals, one per line.",
        "constraints": {"runtime_limit": 3000, "memory_limit": 512},
        "unit_tests": [
            {"input": "4\n1 3\n2 6\n8 10\n15 18", "output": "1 6\n8 10\n15 18"},
            {"input": "2\n1 4\n4 5", "output": "1 5"},
            {"input": "1\n1 4", "output": "1 4"}
        ]
    },
    {
        "task_id": "MEDIUM_QUICKSORT",
        "difficulty": "MEDIUM", 
        "prompt": "Sort an array using quicksort algorithm. Input format: First line contains n, second line contains n integers. Output format: Sorted integers, space-separated.",
        "constraints": {"runtime_limit": 4000, "memory_limit": 512},
        "unit_tests": [
            {"input": "5\n3 1 4 1 5", "output": "1 1 3 4 5"},
            {"input": "3\n9 2 7", "output": "2 7 9"},
            {"input": "1\n42", "output": "42"},
            {"input": "6\n6 5 4 3 2 1", "output": "1 2 3 4 5 6"}
        ]
    },
    {
        "task_id": "MEDIUM_FIBONACCI_MOD",
        "difficulty": "MEDIUM",
        "prompt": "Calculate the nth Fibonacci number modulo 1000000007. Use efficient algorithm for large n. Input format: Single integer n. Output format: nth Fibonacci number mod 1000000007.",
        "constraints": {"runtime_limit": 2000, "memory_limit": 256},
        "unit_tests": [
            {"input": "10", "output": "55"},
            {"input": "100", "output": "354224848"},
            {"input": "1000", "output": "517691607"},
            {"input": "0", "output": "0"}
        ]
    },
    {
        "task_id": "MEDIUM_LONGEST_SUBSTRING",
        "difficulty": "MEDIUM",
        "prompt": "Find the length of the longest substring without repeating characters. Input format: Single line with a string. Output format: Length of longest unique substring.",
        "constraints": {"runtime_limit": 3000, "memory_limit": 512},
        "unit_tests": [
            {"input": "abcabcbb", "output": "3"},
            {"input": "bbbbb", "output": "1"},
            {"input": "pwwkew", "output": "3"},
            {"input": "abcdef", "output": "6"}
        ]
    },

    # === HARD TASKS (2) ===
    {
        "task_id": "HARD_EDIT_DISTANCE",
        "difficulty": "HARD",
        "prompt": "Calculate minimum edit distance (Levenshtein distance) between two strings using dynamic programming. Operations: insert, delete, substitute. Input format: Two lines with strings. Output format: Minimum edit distance.",
        "constraints": {"runtime_limit": 5000, "memory_limit": 1024},
        "unit_tests": [
            {"input": "kitten\nsitting", "output": "3"},
            {"input": "horse\nros", "output": "3"},
            {"input": "intention\nexecution", "output": "5"},
            {"input": "abc\nabc", "output": "0"}
        ]
    },
    {
        "task_id": "HARD_MAXIMUM_FLOW",
        "difficulty": "HARD",
        "prompt": "Find maximum flow in a flow network using Ford-Fulkerson algorithm. Input format: First line: n (nodes) m (edges), then m lines with u v capacity. Source=0, Sink=n-1. Output format: Maximum flow value.",
        "constraints": {"runtime_limit": 8000, "memory_limit": 1024},
        "unit_tests": [
            {"input": "4 5\n0 1 10\n0 2 8\n1 2 5\n1 3 10\n2 3 10", "output": "18"},
            {"input": "3 2\n0 1 5\n1 2 3", "output": "3"},
            {"input": "2 1\n0 1 100", "output": "100"}
        ]
    }
]


class DryRunBatch:
    def __init__(self, host: str = "127.0.0.1", port: int = 8000, timeout: int = 180):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self.session = None
        self.results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.timeout))
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def health_check(self) -> bool:
        """Check if SwiftSolve API is running."""
        try:
            async with self.session.get(f"{self.base_url}/healthz") as response:
                if response.status == 200:
                    health_data = await response.json()
                    print(f"✅ SwiftSolve API is healthy: {health_data}")
                    return True
                else:
                    print(f"❌ Health check failed: HTTP {response.status}")
                    return False
        except Exception as e:
            print(f"❌ Cannot connect to SwiftSolve API: {e}")
            return False
    
    async def run_single_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single task and return results."""
        task_id = task["task_id"]
        difficulty = task["difficulty"]
        
        print(f"\n🚀 Running {task_id} [{difficulty}]...")
        start_time = time.time()
        
        # Remove difficulty field for API call (not part of ProblemInput schema)
        api_task = {k: v for k, v in task.items() if k != "difficulty"}
        
        try:
            async with self.session.post(
                f"{self.base_url}/solve",
                json=api_task,
                headers={"Content-Type": "application/json"}
            ) as response:
                
                end_time = time.time()
                duration = end_time - start_time
                
                if response.status == 200:
                    result = await response.json()
                    status = result.get("status", "unknown")
                    
                    if status == "success":
                        print(f"✅ {task_id} SUCCEEDED in {duration:.1f}s")
                        
                        # Extract performance metrics from profile if available
                        profile = result.get("profile")
                        if profile and isinstance(profile, dict):
                            runtimes = profile.get("runtime_ms", [])
                            memory = profile.get("peak_memory_mb", [])
                            max_runtime = max(runtimes) if runtimes else 0
                            max_memory = max(memory) if memory else 0
                            print(f"   📊 Max runtime: {max_runtime:.1f}ms, Max memory: {max_memory:.1f}MB")
                        
                    else:
                        print(f"❌ {task_id} FAILED: {status}")
                        if "error" in result:
                            print(f"   Error: {result['error']}")
                    
                    return {
                        "task_id": task_id,
                        "difficulty": difficulty,
                        "status": status,
                        "duration_seconds": duration,
                        "api_response": result
                    }
                        
                else:
                    error_text = await response.text()
                    print(f"❌ {task_id} HTTP ERROR {response.status}: {error_text}")
                    return {
                        "task_id": task_id,
                        "difficulty": difficulty,
                        "status": "http_error",
                        "duration_seconds": duration,
                        "error": f"HTTP {response.status}: {error_text}"
                    }
                    
        except asyncio.TimeoutError:
            print(f"⏰ {task_id} TIMEOUT after {self.timeout}s")
            return {
                "task_id": task_id,
                "difficulty": difficulty,
                "status": "timeout",
                "duration_seconds": self.timeout,
                "error": f"Timeout after {self.timeout}s"
            }
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 {task_id} EXCEPTION: {e}")
            return {
                "task_id": task_id,
                "difficulty": difficulty,
                "status": "exception",
                "duration_seconds": duration,
                "error": str(e)
            }
    
    async def run_batch(self, num_tasks: int) -> List[Dict[str, Any]]:
        """Run batch of tasks sequentially."""
        if num_tasks > len(TASK_SET):
            print(f"⚠️ Requested {num_tasks} tasks, but only {len(TASK_SET)} available. Running all {len(TASK_SET)}.")
            num_tasks = len(TASK_SET)
        
        tasks_to_run = TASK_SET[:num_tasks]
        
        print(f"\n🎯 DRY-RUN BATCH MODE: Running {num_tasks} tasks")
        print(f"📋 Task breakdown: {self._count_difficulties(tasks_to_run)}")
        print(f"🌐 Target API: {self.base_url}")
        print(f"⏱️ Timeout per task: {self.timeout}s")
        
        # Health check first
        if not await self.health_check():
            print("❌ Aborting batch run - API not available")
            return []
        
        batch_start = time.time()
        results = []
        
        for i, task in enumerate(tasks_to_run, 1):
            print(f"\n{'='*60}")
            print(f"Task {i}/{num_tasks}: {task['task_id']} [{task['difficulty']}]")
            print(f"{'='*60}")
            
            result = await self.run_single_task(task)
            results.append(result)
            
            # Brief pause between tasks to avoid overwhelming the API
            if i < len(tasks_to_run):
                await asyncio.sleep(1)
        
        batch_duration = time.time() - batch_start
        
        # Generate summary
        self._print_summary(results, batch_duration)
        
        return results
    
    def _count_difficulties(self, tasks: List[Dict]) -> str:
        """Count tasks by difficulty."""
        counts = {"EASY": 0, "MEDIUM": 0, "HARD": 0}
        for task in tasks:
            difficulty = task.get("difficulty", "UNKNOWN")
            counts[difficulty] = counts.get(difficulty, 0) + 1
        return f"{counts['EASY']} Easy, {counts['MEDIUM']} Medium, {counts['HARD']} Hard"
    
    def _print_summary(self, results: List[Dict], batch_duration: float):
        """Print comprehensive batch summary."""
        print(f"\n{'='*80}")
        print(f"📊 BATCH SUMMARY - {len(results)} tasks in {batch_duration:.1f}s")
        print(f"{'='*80}")
        
        # Status counts
        status_counts = {}
        difficulty_stats = {"EASY": [], "MEDIUM": [], "HARD": []}
        total_duration = 0
        
        for result in results:
            status = result["status"]
            difficulty = result["difficulty"]
            duration = result["duration_seconds"]
            
            status_counts[status] = status_counts.get(status, 0) + 1
            difficulty_stats[difficulty].append(result)
            total_duration += duration
        
        # Overall stats
        print(f"🎯 Status breakdown:")
        for status, count in status_counts.items():
            percentage = (count / len(results)) * 100
            print(f"   {status.upper()}: {count}/{len(results)} ({percentage:.1f}%)")
        
        print(f"\n⏱️ Timing:")
        print(f"   Total duration: {total_duration:.1f}s")
        print(f"   Average per task: {total_duration/len(results):.1f}s")
        print(f"   Batch overhead: {batch_duration - total_duration:.1f}s")
        
        # Difficulty breakdown
        print(f"\n📈 Performance by difficulty:")
        for difficulty in ["EASY", "MEDIUM", "HARD"]:
            tasks = difficulty_stats[difficulty]
            if not tasks:
                continue
            
            successes = sum(1 for t in tasks if t["status"] == "success")
            success_rate = (successes / len(tasks)) * 100 if tasks else 0
            avg_time = sum(t["duration_seconds"] for t in tasks) / len(tasks)
            
            print(f"   {difficulty}: {successes}/{len(tasks)} success ({success_rate:.1f}%), avg {avg_time:.1f}s")
        
        # Detailed results
        print(f"\n📋 Detailed results:")
        for result in results:
            status_emoji = "✅" if result["status"] == "success" else "❌"
            print(f"   {status_emoji} {result['task_id']:<25} [{result['difficulty']:<6}] "
                  f"{result['status']:<12} {result['duration_seconds']:>6.1f}s")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create dry-run results directory
        results_dir = Path("dry_run_results")
        results_dir.mkdir(exist_ok=True)
        
        filename = results_dir / f"batch_{timestamp}.json"
        
        summary_data = {
            "timestamp": datetime.now().isoformat(),
            "batch_duration_seconds": batch_duration,
            "total_tasks": len(results),
            "status_counts": status_counts,
            "results": results
        }
        
        with open(filename, 'w') as f:
            json.dump(summary_data, f, indent=2, default=str)
        
        print(f"\n💾 Results saved to: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="SwiftSolve Dry-Run Batch Mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dry_run_batch.py --tasks 5                    # Run first 5 tasks
  python dry_run_batch.py --tasks 10                   # Run all 10 tasks  
  python dry_run_batch.py --tasks 3 --timeout 120     # Run 3 tasks with 2min timeout each
  python dry_run_batch.py --host localhost --port 8080 # Custom API endpoint
        """
    )
    
    parser.add_argument(
        "--tasks", "-n", 
        type=int, 
        default=5,
        help="Number of tasks to run (1-10, default: 5)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1", 
        help="SwiftSolve API host (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", 
        type=int,
        default=8000,
        help="SwiftSolve API port (default: 8000)"
    )
    parser.add_argument(
        "--timeout",
        type=int, 
        default=180,
        help="Timeout per task in seconds (default: 180)"
    )
    parser.add_argument(
        "--list-tasks",
        action="store_true",
        help="List all available tasks and exit"
    )
    
    args = parser.parse_args()
    
    # List tasks option
    if args.list_tasks:
        print("📋 Available tasks in dry-run batch:")
        print(f"{'ID':<30} {'Difficulty':<8} {'Description':<50}")
        print("="*90)
        for i, task in enumerate(TASK_SET, 1):
            desc = task["prompt"][:47] + "..." if len(task["prompt"]) > 50 else task["prompt"]
            print(f"{i:2}. {task['task_id']:<27} {task['difficulty']:<8} {desc}")
        print(f"\nTotal: {len(TASK_SET)} tasks ({DryRunBatch('', 0)._count_difficulties(TASK_SET)})")
        return
    
    # Validate arguments
    if args.tasks < 1:
        print("❌ Error: --tasks must be at least 1")
        sys.exit(1)
    
    if args.tasks > len(TASK_SET):
        print(f"⚠️ Warning: Requested {args.tasks} tasks, but only {len(TASK_SET)} available")
    
    # Run batch
    async def run():
        async with DryRunBatch(args.host, args.port, args.timeout) as batch:
            await batch.run_batch(args.tasks)
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\n⚠️ Batch run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()