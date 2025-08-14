# agents/coder.py
from openai import OpenAI
from .base import Agent
from ..schemas import PlanMessage, CodeMessage
from ..utils.config import get_settings
from typing import Optional
import json, textwrap

class Coder(Agent):
    def __init__(self):
        super().__init__("Coder")
        self.client = OpenAI(api_key=get_settings().openai_api_key)

    def run(self, plan: PlanMessage, patch: Optional[str] = None) -> CodeMessage:
        if patch:
            self.log.info(f"🩹 Applying patch: {patch}")
        
        # Build system message based on whether we have a patch
        if patch:
            system_msg = """You are an expert ICPC competitive programmer applying a performance optimization patch.

PATCH TO APPLY: {patch}

Write the completed program as a string.

CRITICAL RULES:
- Write efficient ISO C++17 code ONLY
- MUST apply the optimization specified in the patch above
- Include all necessary headers (#include <iostream>, etc.)
- Use proper competitive programming template
- Make sure the C++ code compiles WITHOUT SYNTAX ERRORS
- Pay special attention to matching quotes, semicolons, and braces
- Focus on the specific optimization mentioned in the patch

Example valid response for the problem a + b:
#include <iostream>
using namespace std;
int main() {
    int a;
    int b;
    cin >> a >> b;
    cout << a + b << '\\n';
}

Note that this is not the 
""".format(patch)
        else:
            system_msg = """You are an expert ICPC competitive programmer.
Write the completed program as a string.

CRITICAL RULES:
- Write efficient ISO C++17 code ONLY
- Include all necessary headers (#include <iostream>, etc.)
- Use proper competitive programming template
- Make sure the C++ code compiles WITHOUT SYNTAX ERRORS
- Pay special attention to matching quotes, semicolons, and braces

Example valid response for the problem a + b:
#include <iostream>
using namespace std;
int main() {
    int a;
    int b;
    cin >> a >> b;
    cout << a + b << '\\n';
}
"""

        # Build user message based on whether we have a patch
        if patch:
            user_msg = f"""Apply the optimization patch to solve this problem:

Problem Statement: {plan.problem_statement}

ORIGINAL PLAN:
Algorithm: {plan.algorithm}
Input bounds: {plan.input_bounds}
Constraints: {plan.constraints}

OPTIMIZATION PATCH TO APPLY:
{patch}

Generate optimized C++ code that implements the algorithm while applying the specific optimization mentioned in the patch."""
        else:
            user_msg = f"Generate C++ code for this plan:\nProblem Statement: {plan.problem_statement}\nAlgorithm: {plan.algorithm}\nInput bounds: {plan.input_bounds}\nConstraints: {plan.constraints}"
        
        self.log.info(f"🤖 LLM REQUEST to gpt-4.1:")
        self.log.info(f"System: {system_msg[:200]}...")
        self.log.info(f"User: {user_msg[:200]}...")

        self.log.info(f"System: {system_msg}...")
        self.log.info(f"User: {user_msg}...")

        resp = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.1,
            max_tokens=1024,
        )
        
        code_text = resp.choices[0].message.content.strip()
        self.log.info(f"📥 LLM RESPONSE from gpt-4.1: {code_text}")
        
        # Extract JSON from markdown code blocks if present
        if "```" in code_text:
            code_text = code_text.split("```")[1]
            if code_text.startswith("json"):
                code_text = code_text[4:]
        code_text = code_text.strip()
        

        
        try:
            # code_data = json.loads(code_text)
            cpp_code = code_text
            
            # Fix newline encoding in the C++ code - handle multiple formats
            # cpp_code = code_data["code_cpp"]
            # Only decode newlines that are NOT inside string literals
            # First, replace escaped quotes to protect them
            # cpp_code = cpp_code.replace('\\"', '###ESCAPED_QUOTE###')
            # Now safely decode the structural escapes
            # cpp_code = cpp_code.replace('\\n', '\n').replace('\\t', '\t')
            # Restore escaped quotes
            # cpp_code = cpp_code.replace('###ESCAPED_QUOTE###', '"')
            
            self.log.info(f"Decoded C++ code:\n{cpp_code}")
            
            # Basic validation - ensure it has includes
            if "#include" not in cpp_code:
                self.log.warning("Generated code missing includes, adding basic ones")
                cpp_code = "#include <iostream>\n#include <vector>\n#include <algorithm>\nusing namespace std;\n\n" + cpp_code
                
            # Additional validation - check for common syntax issues
            if "cout" in cpp_code and "endl" not in cpp_code and "\\n" not in cpp_code:
                self.log.warning("Generated code might be missing proper output formatting")
            
            # Check for unterminated strings and fix common cout issues
            if 'cout << ' in cpp_code:
                lines = cpp_code.split('\n')
                for i, line in enumerate(lines):
                    # Fix specific patterns that cause issues
                    if 'cout << ' in line:
                        # Replace problematic newline patterns with endl
                        if '" << "\\n"' in line:
                            lines[i] = line.replace('" << "\\n"', '" << endl')
                        elif '<< "\\n"' in line:
                            lines[i] = line.replace('<< "\\n"', '<< endl')
                        elif "'" in line and "\\n" in line:
                            # Replace single quotes with double quotes for newlines
                            lines[i] = line.replace("'\\n'", "endl")
                        elif "'" in line and line.count("'") % 2 != 0:
                            # Fix unterminated single quotes
                            self.log.warning(f"Fixing unterminated single quote in line {i+1}: {line}")
                            lines[i] = line.replace("'", "").replace("cout << max_val <<", "cout << max_val << endl") + ";"
                        elif '"' in line and line.count('"') % 2 != 0:
                            # Fix unterminated double quotes  
                            self.log.warning(f"Fixing unterminated double quote in line {i+1}: {line}")
                            lines[i] = line.replace('"', '').replace("cout << max_val <<", "cout << max_val << endl") + ";"
                cpp_code = '\n'.join(lines)
            
            code = CodeMessage(
                task_id=plan.task_id,
                iteration=plan.iteration,
                code_cpp=cpp_code
            )
            

            
        except Exception as e:
            self.log.error(f"Malformed code response: {e}\n{code_text}")
            # Fallback to simple template
            fallback_code = """#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    // Simple solution template
    int n;
    cin >> n;
    cout << n << endl;
    return 0;
}"""
            code = CodeMessage(
                task_id=plan.task_id,
                iteration=plan.iteration,
                code_cpp=fallback_code
            )
            self.log.warning("⚠️ Using fallback code due to parsing error")
        
        self.log.info("Coder completed successfully")
        return code