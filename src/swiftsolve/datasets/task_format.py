"""
Task Format Schema and Validation

This module defines the standardized task format for SwiftSolve datasets.
All tasks (BigO(Bench), Codeforces, etc.) must conform to this schema.

Based on CONTEXT.md section 1.10 and repository layout section 3.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Dict, Any, Optional
from enum import Enum


class DifficultyLevel(str, Enum):
    """Standardized difficulty levels across datasets."""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    

class ComplexityClass(str, Enum):
    """Expected algorithmic complexity classes."""
    CONSTANT = "O(1)"
    LOGARITHMIC = "O(log n)"
    LINEAR = "O(n)"
    LINEARITHMIC = "O(n log n)"
    QUADRATIC = "O(n^2)"
    CUBIC = "O(n^3)"
    POLYNOMIAL = "O(n^k)"
    EXPONENTIAL = "O(2^n)"
    FACTORIAL = "O(n!)"


class TestCase(BaseModel):
    """Individual test case with input and expected output."""
    input: str = Field(..., description="Input data as string")
    output: str = Field(..., description="Expected output as string")
    explanation: Optional[str] = Field(None, description="Optional explanation of the test case")


class TaskMetadata(BaseModel):
    """Comprehensive task specification."""
    task_id: str = Field(..., description="Unique identifier (e.g., CF1285C, BIGOBENCH_001)")
    title: str = Field(..., description="Human-readable task title")
    source: str = Field(..., description="Dataset source (bigobench, codeforces)")
    difficulty: DifficultyLevel = Field(..., description="Standardized difficulty level")
    
    # Problem specification
    description: str = Field(..., description="Problem statement in natural language")
    input_format: str = Field(..., description="Description of input format")
    output_format: str = Field(..., description="Description of output format")
    
    # Constraints and limits
    input_bounds: Dict[str, int] = Field(..., description="Input size bounds (e.g., {'n': 100000})")
    time_limit_ms: int = Field(..., description="Time limit in milliseconds")
    memory_limit_mb: int = Field(..., description="Memory limit in megabytes")
    
    # Expected solution properties
    expected_complexity: ComplexityClass = Field(..., description="Expected optimal time complexity")
    expected_approach: str = Field(..., description="Expected algorithmic approach (e.g., 'hash map', 'two pointers')")
    
    # Test cases
    test_cases: List[TestCase] = Field(..., min_items=3, description="Test cases including examples and edge cases")
    
    # Dataset-specific metadata
    source_url: Optional[str] = Field(None, description="Original problem URL")
    source_rating: Optional[int] = Field(None, description="Original difficulty rating (e.g., Codeforces rating)")
    tags: List[str] = Field(default_factory=list, description="Problem tags (e.g., ['graph', 'dfs', 'binary-search'])")
    
    @validator('task_id')
    def validate_task_id(cls, v):
        """Ensure task_id follows naming convention."""
        if not v or len(v) < 3:
            raise ValueError("task_id must be at least 3 characters")
        return v
    
    @validator('input_bounds')
    def validate_input_bounds(cls, v):
        """Ensure input bounds are positive."""
        for key, value in v.items():
            if not isinstance(value, int) or value <= 0:
                raise ValueError(f"Input bound {key} must be a positive integer")
        return v
    
    @validator('time_limit_ms')
    def validate_time_limit(cls, v):
        """Ensure reasonable time limit."""
        if v <= 0 or v > 60000:  # 0-60 seconds
            raise ValueError("Time limit must be between 1ms and 60000ms")
        return v
    
    @validator('memory_limit_mb')
    def validate_memory_limit(cls, v):
        """Ensure reasonable memory limit."""
        if v <= 0 or v > 2048:  # 0-2GB
            raise ValueError("Memory limit must be between 1MB and 2048MB")
        return v


def validate_task_file(task_data: Dict[str, Any]) -> TaskMetadata:
    """
    Validate a task file against the schema.
    
    Args:
        task_data: Raw task data from JSON file
        
    Returns:
        Validated TaskMetadata instance
        
    Raises:
        ValidationError: If task data is invalid
    """
    return TaskMetadata.model_validate(task_data)


def create_problem_input(task: TaskMetadata) -> Dict[str, Any]:
    """
    Convert TaskMetadata to ProblemInput format for SwiftSolve pipeline.
    
    Args:
        task: Validated task metadata
        
    Returns:
        Dict suitable for ProblemInput schema
    """
    return {
        "task_id": task.task_id,
        "description": task.description,
        "input_format": task.input_format,
        "output_format": task.output_format,
        "constraints": {
            "runtime_limit": task.time_limit_ms,
            "memory_limit": task.memory_limit_mb
        },
        "examples": [
            {
                "input": tc.input,
                "output": tc.output,
                "explanation": tc.explanation
            }
            for tc in task.test_cases[:3]  # Include first 3 as examples
        ]
    }


# Sample task for testing
SAMPLE_TASK = TaskMetadata(
    task_id="SAMPLE_TWOSUM",
    title="Two Sum",
    source="sample",
    difficulty=DifficultyLevel.EASY,
    description="Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
    input_format="First line: n (array size)\nSecond line: n integers (array elements)\nThird line: target integer",
    output_format="Two space-separated integers (0-indexed positions) or '-1 -1' if no solution",
    input_bounds={"n": 100000},
    time_limit_ms=2000,
    memory_limit_mb=512,
    expected_complexity=ComplexityClass.LINEAR,
    expected_approach="hash map",
    test_cases=[
        TestCase(
            input="4\n2 7 11 15\n9",
            output="0 1",
            explanation="nums[0] + nums[1] = 2 + 7 = 9"
        ),
        TestCase(
            input="3\n3 2 4\n6",
            output="1 2",
            explanation="nums[1] + nums[2] = 2 + 4 = 6"
        ),
        TestCase(
            input="2\n3 3\n6",
            output="0 1",
            explanation="nums[0] + nums[1] = 3 + 3 = 6"
        ),
        TestCase(
            input="2\n1 2\n4",
            output="-1 -1",
            explanation="No two numbers sum to 4"
        )
    ],
    tags=["array", "hash-table", "two-pointers"]
)