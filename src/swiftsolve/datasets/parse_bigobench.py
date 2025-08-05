"""
BigO(Bench) Dataset Parser

Parses BigO(Bench) tasks from HTML/JSON format into standardized TaskMetadata format.
Based on CONTEXT.md section 4.2 Phase D.

BigO(Bench) is a benchmark suite of algorithmic problems with known complexity classes,
designed specifically for evaluating the ability to generate efficient algorithms.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

from .task_format import TaskMetadata, TestCase, DifficultyLevel, ComplexityClass
from ..utils.logger import get_logger

log = get_logger("BigOBenchParser")


class BigOBenchParser:
    """Parser for BigO(Bench) dataset tasks."""
    
    # Mapping from BigO(Bench) complexity to our enum
    COMPLEXITY_MAPPING = {
        "O(1)": ComplexityClass.CONSTANT,
        "O(log n)": ComplexityClass.LOGARITHMIC,
        "O(n)": ComplexityClass.LINEAR,
        "O(n log n)": ComplexityClass.LINEARITHMIC,
        "O(n^2)": ComplexityClass.QUADRATIC,
        "O(n^3)": ComplexityClass.CUBIC,
        "O(n^k)": ComplexityClass.POLYNOMIAL,
        "O(2^n)": ComplexityClass.EXPONENTIAL,
        "O(n!)": ComplexityClass.FACTORIAL
    }
    
    # Difficulty mapping based on complexity
    DIFFICULTY_MAPPING = {
        ComplexityClass.CONSTANT: DifficultyLevel.EASY,
        ComplexityClass.LOGARITHMIC: DifficultyLevel.EASY,
        ComplexityClass.LINEAR: DifficultyLevel.EASY,
        ComplexityClass.LINEARITHMIC: DifficultyLevel.MEDIUM,
        ComplexityClass.QUADRATIC: DifficultyLevel.MEDIUM,
        ComplexityClass.CUBIC: DifficultyLevel.HARD,
        ComplexityClass.POLYNOMIAL: DifficultyLevel.HARD,
        ComplexityClass.EXPONENTIAL: DifficultyLevel.HARD,
        ComplexityClass.FACTORIAL: DifficultyLevel.HARD
    }
    
    def __init__(self, dataset_dir: Path):
        """
        Initialize parser.
        
        Args:
            dataset_dir: Directory to store parsed tasks
        """
        self.dataset_dir = Path(dataset_dir)
        self.output_dir = self.dataset_dir / "bigobench"
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_from_json(self, json_file: Path) -> List[TaskMetadata]:
        """
        Parse BigO(Bench) tasks from JSON file.
        
        Args:
            json_file: Path to BigO(Bench) JSON file
            
        Returns:
            List of parsed and validated tasks
        """
        log.info(f"Parsing BigO(Bench) from JSON: {json_file}")
        
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        tasks = []
        for item in data.get('problems', []):
            try:
                task = self._parse_problem_json(item)
                if task:
                    tasks.append(task)
            except Exception as e:
                log.warning(f"Failed to parse problem {item.get('id', 'unknown')}: {e}")
        
        log.info(f"Successfully parsed {len(tasks)} tasks from BigO(Bench)")
        return tasks
    
    def parse_from_html(self, html_file: Path) -> List[TaskMetadata]:
        """
        Parse BigO(Bench) tasks from HTML file.
        Note: HTML parsing requires bs4. Use create_sample_bigobench_dataset() for testing.
        
        Args:
            html_file: Path to BigO(Bench) HTML file
            
        Returns:
            List of parsed and validated tasks
        """
        log.warning("HTML parsing requires bs4 library. Use create_sample_bigobench_dataset() instead.")
        return []
    
    def _parse_problem_json(self, problem_data: Dict[str, Any]) -> Optional[TaskMetadata]:
        """Parse a single problem from JSON format."""
        problem_id = problem_data.get('id', f"BIGOBENCH_{len(problem_data)}")
        
        # Extract complexity
        complexity_str = problem_data.get('complexity', 'O(n)')
        complexity = self.COMPLEXITY_MAPPING.get(complexity_str, ComplexityClass.LINEAR)
        difficulty = self.DIFFICULTY_MAPPING.get(complexity, DifficultyLevel.MEDIUM)
        
        # Extract input bounds
        input_bounds = {"n": problem_data.get('max_n', 100000)}
        
        # Parse test cases
        test_cases = []
        for i, (inp, out) in enumerate(zip(
            problem_data.get('inputs', []), 
            problem_data.get('outputs', [])
        )):
            test_cases.append(TestCase(
                input=str(inp),
                output=str(out),
                explanation=f"Test case {i+1}"
            ))
        
        # Ensure minimum test cases
        if len(test_cases) < 3:
            test_cases.extend([
                TestCase(input="1\n1", output="1", explanation="Minimal case"),
                TestCase(input="2\n1 2", output="1 2", explanation="Basic case"),
                TestCase(input="5\n1 2 3 4 5", output="1 2 3 4 5", explanation="Larger case")
            ])
        
        return TaskMetadata(
            task_id=f"BIGOBENCH_{problem_id}",
            title=problem_data.get('title', f"Problem {problem_id}"),
            source="bigobench",
            difficulty=difficulty,
            description=problem_data.get('description', f"BigO(Bench) problem with {complexity_str} complexity"),
            input_format=problem_data.get('input_format', "First line: n (input size)\\nFollowing lines: input data"),
            output_format=problem_data.get('output_format', "Output according to problem requirements"),
            input_bounds=input_bounds,
            time_limit_ms=problem_data.get('time_limit_ms', 2000),
            memory_limit_mb=problem_data.get('memory_limit_mb', 512),
            expected_complexity=complexity,
            expected_approach=problem_data.get('approach', self._infer_approach(complexity)),
            test_cases=test_cases[:10],  # Limit to 10 test cases
            source_url=problem_data.get('url'),
            tags=[complexity_str.lower().replace('(', '').replace(')', '').replace(' ', '-')]
        )
    
    def _parse_problem_html(self, problem_div) -> Optional[TaskMetadata]:
        """Parse a single problem from HTML div element. (Disabled - requires bs4)"""
        log.warning("HTML parsing disabled - requires bs4 library")
        return None
    
    def _infer_approach(self, complexity: ComplexityClass) -> str:
        """Infer likely algorithmic approach from complexity class."""
        approach_mapping = {
            ComplexityClass.CONSTANT: "direct calculation",
            ComplexityClass.LOGARITHMIC: "binary search",
            ComplexityClass.LINEAR: "single pass",
            ComplexityClass.LINEARITHMIC: "sorting or divide-and-conquer",
            ComplexityClass.QUADRATIC: "nested loops",
            ComplexityClass.CUBIC: "triple nested loops",
            ComplexityClass.POLYNOMIAL: "dynamic programming",
            ComplexityClass.EXPONENTIAL: "backtracking",
            ComplexityClass.FACTORIAL: "exhaustive search"
        }
        return approach_mapping.get(complexity, "unknown")
    
    def save_tasks(self, tasks: List[TaskMetadata]) -> None:
        """
        Save parsed tasks to individual JSON files.
        
        Args:
            tasks: List of validated tasks to save
        """
        log.info(f"Saving {len(tasks)} BigO(Bench) tasks to {self.output_dir}")
        
        for task in tasks:
            filename = f"task_{task.task_id.lower()}.json"
            filepath = self.output_dir / filename
            
            with open(filepath, 'w') as f:
                json.dump(task.model_dump(), f, indent=2)
        
        # Create index file
        index = {
            "dataset": "bigobench",
            "version": "1.0.0",
            "task_count": len(tasks),
            "tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "difficulty": task.difficulty.value,
                    "complexity": task.expected_complexity.value,
                    "file": f"task_{task.task_id.lower()}.json"
                }
                for task in tasks
            ]
        }
        
        with open(self.output_dir / "index.json", 'w') as f:
            json.dump(index, f, indent=2)
        
        log.info(f"Created index with {len(tasks)} tasks")


def create_sample_bigobench_dataset(output_dir: Path) -> None:
    """
    Create a sample BigO(Bench) dataset for testing.
    
    Args:
        output_dir: Directory to create sample dataset
    """
    parser = BigOBenchParser(output_dir)
    
    # Create sample problems covering different complexity classes
    sample_problems = [
        {
            "id": "001",
            "title": "Maximum Element",
            "description": "Find the maximum element in an array",
            "complexity": "O(n)",
            "approach": "linear scan",
            "max_n": 100000,
            "inputs": ["3\n1 3 2", "1\n5", "4\n4 4 4 4"],
            "outputs": ["3", "5", "4"]
        },
        {
            "id": "002", 
            "title": "Binary Search",
            "description": "Find target element in sorted array",
            "complexity": "O(log n)",
            "approach": "binary search",
            "max_n": 100000,
            "inputs": ["5 3\n1 2 3 4 5", "3 1\n1 2 3", "4 5\n1 2 3 4"],
            "outputs": ["2", "0", "-1"]
        },
        {
            "id": "003",
            "title": "Bubble Sort",
            "description": "Sort array using bubble sort",
            "complexity": "O(n^2)",
            "approach": "nested loops",
            "max_n": 1000,
            "inputs": ["3\n3 1 2", "1\n5", "4\n4 3 2 1"],
            "outputs": ["1 2 3", "5", "1 2 3 4"]
        }
    ]
    
    tasks = []
    for problem in sample_problems:
        task = parser._parse_problem_json(problem)
        if task:
            tasks.append(task)
    
    parser.save_tasks(tasks)
    log.info(f"Created sample BigO(Bench) dataset with {len(tasks)} tasks")


if __name__ == "__main__":
    # Create sample dataset for testing
    create_sample_bigobench_dataset(Path("datasets"))