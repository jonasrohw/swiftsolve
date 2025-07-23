# agents/coder.py
from openai import OpenAI
from .base import Agent
from ..schemas import PlanMessage, CodeMessage
from ..utils.config import get_settings
import json, textwrap

class Coder(Agent):
    def __init__(self):
        super().__init__("Coder")
        self.client = OpenAI(api_key=get_settings().openai_api_key)

    def run(self, plan: PlanMessage) -> CodeMessage:
        system_msg = """You are an expert ICPC competitive programmer.
        
Generate EXACTLY this JSON format:
{"code_cpp": "your_cpp_code_here"}

CRITICAL RULES:
- Write efficient ISO C++17 code ONLY
- Include all necessary headers (#include <iostream>, etc.)
- Use proper competitive programming template
- In the JSON, escape ALL special characters: use \\n for newlines, \\t for tabs, \\" for quotes
- Ensure valid JSON - test your response before sending
- NO explanation, just the JSON with properly escaped code
- Make sure the C++ code compiles without errors

Example valid JSON:
{"code_cpp": "#include <iostream>\\nusing namespace std;\\n\\nint main() {\\n    int a, b;\\n    cin >> a >> b;\\n    cout << a + b << endl;\\n    return 0;\\n}"}"""

        user_msg = f"Generate C++ code for this plan:\nAlgorithm: {plan.algorithm}\nInput bounds: {plan.input_bounds}\nConstraints: {plan.constraints}"
        
        resp = self.client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "system", "content": system_msg},
                      {"role": "user", "content": user_msg}],
            temperature=0.1,
            max_tokens=1024,
        )
        
        code_text = resp.choices[0].message.content.strip()
        # Extract JSON from markdown code blocks if present
        if "```" in code_text:
            code_text = code_text.split("```")[1]
            if code_text.startswith("json"):
                code_text = code_text[4:]
        code_text = code_text.strip()
        
        try:
            code_data = json.loads(code_text)
            # Fix newline encoding in the C++ code - handle multiple formats
            cpp_code = code_data["code_cpp"]
            cpp_code = cpp_code.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
            
            # Basic validation - ensure it has includes
            if "#include" not in cpp_code:
                self.log.warning("Generated code missing includes, adding basic ones")
                cpp_code = "#include <iostream>\n#include <vector>\n#include <algorithm>\nusing namespace std;\n\n" + cpp_code
                
            # Additional validation - check for common issues
            if "cout" in cpp_code and "endl" not in cpp_code and "\\n" not in cpp_code:
                self.log.warning("Generated code might be missing proper output formatting")
            
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
        return code