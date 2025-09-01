# baseline/agent.py
"""
Claude 4 Opus Baseline Agent
============================

A simple baseline agent that uses Claude 4 Opus directly to solve programming problems.
This serves as a comparison baseline against the SwiftSolve multi-agent pipeline.
"""

import anthropic
from ..utils.config import get_settings
from ..utils.logger import get_logger
from ..schemas import ProblemInput, CodeMessage
from typing import Optional


class ClaudeOpusBaselineAgent:
    """A baseline agent that uses Claude 4 Opus directly to solve coding problems."""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)
        self.log = get_logger("ClaudeOpusBaseline")
        
    def solve(self, problem: ProblemInput, attempt: int = 1) -> CodeMessage:
        """
        Solve a programming problem using Claude 4 Opus directly.
        
        Args:
            problem: The problem to solve
            attempt: Attempt number (for logging)
            
        Returns:
            CodeMessage containing the generated solution
        """
        self.log.info(f"🤖 Claude 4 Opus Baseline solving task: {problem.task_id} (attempt {attempt})")
        
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

IMPORTANT: Your response must contain ONLY the C++ code. Do not include any explanations, comments outside the code, or markdown formatting. Start directly with #include statements and end with the closing brace of main()."""

        user_prompt = f"""Problem: {problem.prompt}

Constraints: {problem.constraints}

Unit Tests:
{self._format_tests(problem.unit_tests)}

Write an efficient C++ solution that passes all test cases and handles the given constraints optimally.

Remember: Output ONLY the C++ code. No explanations, no markdown, no comments outside the code."""

        try:
            response = self.client.messages.create(
                model="claude-4-opus-20250514",  # Using Claude 4 Opus
                max_tokens=2000,
                temperature=0.1,  # Low temperature for consistent, focused solutions
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            code = response.content[0].text.strip()
            
            # Clean the code (remove markdown and explanatory text)
            lines = code.split('\n')
            cleaned_lines = []
            in_code_block = False
            found_include = False
            
            for line in lines:
                # Skip markdown code block markers
                if line.strip().startswith("```"):
                    in_code_block = not in_code_block
                    continue
                
                # Skip explanatory text before code starts
                if not found_include and not line.strip().startswith("#include"):
                    continue
                
                # Found the start of actual code
                if line.strip().startswith("#include"):
                    found_include = True
                
                # Add the line if we're in code
                if found_include:
                    cleaned_lines.append(line)
            
            code = '\n'.join(cleaned_lines).strip()
            
            # Additional cleanup - remove any remaining markdown
            if code.startswith("```cpp") or code.startswith("```c++"):
                code = code.split("```")[1]
                if code.startswith("cpp\n") or code.startswith("c++\n"):
                    code = code.split("\n", 1)[1]
            elif code.startswith("```"):
                code = code.split("```")[1]
            
            code = code.strip()
            
            # Validate that we have actual C++ code
            if not code or len(code) < 50:
                raise Exception("Generated code is too short or empty")
            
            if not any(line.strip().startswith("#include") for line in code.split('\n')):
                raise Exception("Generated code doesn't contain #include statements")
            
            if "int main(" not in code and "int main (" not in code:
                raise Exception("Generated code doesn't contain main function")
            
            self.log.info(f"✅ Claude 4 Opus generated solution ({len(code)} chars)")
            
            return CodeMessage(
                task_id=problem.task_id,
                iteration=0,  # Baseline always uses iteration 0
                code_cpp=code
            )
            
        except Exception as e:
            self.log.error(f"❌ Claude 4 Opus failed to generate solution: {e}")
            raise Exception(f"Claude 4 Opus baseline agent failed: {str(e)}")
    
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
