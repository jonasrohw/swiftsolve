# baseline/agent.py
"""
GPT-4 Baseline Agent
===================

A simple baseline agent that uses GPT-4 directly to solve programming problems.
This serves as a comparison baseline against the SwiftSolve multi-agent pipeline.
"""

from openai import OpenAI
from ..utils.config import get_settings
from ..utils.logger import get_logger
from ..schemas import ProblemInput, CodeMessage
from typing import Optional


class GPT4BaselineAgent:
    """A baseline agent that uses GPT-4 directly to solve coding problems."""
    
    def __init__(self):
        self.client = OpenAI(api_key=get_settings().openai_api_key)
        self.log = get_logger("GPT4Baseline")
        
    def solve(self, problem: ProblemInput, attempt: int = 1) -> CodeMessage:
        """
        Solve a programming problem using GPT-4 directly.
        
        Args:
            problem: The problem to solve
            attempt: Attempt number (for logging)
            
        Returns:
            CodeMessage containing the generated solution
        """
        self.log.info(f"🤖 GPT-4 Baseline solving task: {problem.task_id} (attempt {attempt})")
        
        # Build the prompt
        system_prompt = """You are an expert competitive programmer. You will be given a programming problem and must write a complete, efficient C++ solution.

CRITICAL REQUIREMENTS:
- Write complete, runnable C++ code using competitive programming standards
- Include all necessary headers (#include <iostream>, etc.)
- Use proper input/output handling with cin/cout
- Optimize for both time and space complexity
- Use efficient algorithms and data structures
- Follow C++17 standard
- Make sure the code compiles without syntax errors
- Handle edge cases appropriately

Output ONLY the C++ code, no explanations or comments outside the code."""

        user_prompt = f"""Problem: {problem.prompt}

Constraints: {problem.constraints}

Unit Tests:
{self._format_tests(problem.unit_tests)}

Write an efficient C++ solution that passes all test cases and handles the given constraints optimally."""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4.1",  # Using GPT-4 variant
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for consistent, focused solutions
                max_tokens=2000
            )
            
            code = response.choices[0].message.content.strip()
            
            # Clean the code (remove markdown if present)
            if code.startswith("```cpp") or code.startswith("```c++"):
                code = code.split("```")[1]
                if code.startswith("cpp\n") or code.startswith("c++\n"):
                    code = code.split("\n", 1)[1]
            elif code.startswith("```"):
                code = code.split("```")[1]
            
            code = code.strip()
            
            self.log.info(f"✅ GPT-4 generated solution ({len(code)} chars)")
            
            return CodeMessage(
                task_id=problem.task_id,
                iteration=0,  # Baseline always uses iteration 0
                code_cpp=code
            )
            
        except Exception as e:
            self.log.error(f"❌ GPT-4 failed to generate solution: {e}")
            raise Exception(f"GPT-4 baseline agent failed: {str(e)}")
    
    def _format_tests(self, unit_tests: list) -> str:
        """Format unit tests for the prompt."""
        if not unit_tests:
            return "No unit tests provided."
        
        formatted = []
        for i, test in enumerate(unit_tests, 1):
            formatted.append(f"Test {i}:")
            formatted.append(f"Input: {test.get('input', 'N/A')}")
            formatted.append(f"Expected Output: {test.get('output', 'N/A')}")
            formatted.append("")
        
        return "\n".join(formatted)
