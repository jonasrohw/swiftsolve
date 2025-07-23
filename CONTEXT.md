# CONTEXT.md

## Project Overview: SwiftSolve

**SwiftSolve** is a multi-agent code generation framework designed to synthesize **functionally correct and computationally efficient C++ code** from natural language problem statements. The system is built with **runtime and memory constraints** in mind, particularly targeting use cases such as **competitive programming**, **real-world runtime-critical applications**, and **Big-O-complexity-aware generation**.

The architecture is fully modular and follows a layered, orchestrated control loop with well-typed JSON protocols and sandboxed execution for profiling. It integrates both **static heuristics** and **dynamic profiling** to reduce LLM token waste, cut iteration costs, and produce scalable, efficient solutions.

---

## Technology Stack

### Languages & Frameworks

- **Python 3.11.13** — orchestration layer and agent logic
- **FastAPI 0.116.1** — RESTful API server
- **C++17** — target language for synthesized solutions
- **Pytest** — testing framework for agents and pipeline logic
- **Docker** — secure sandboxed execution for profiling

### Libraries

- `openai==1.95.1` — for calling GPT-4.1 and GPT-4o
- `anthropic==0.57.1` — for calling Claude 4 Opus
- `pydantic==2.9.2` — for schema validation and message typing
- `uvicorn==0.35.0` — ASGI server for FastAPI
- `httpx`, `rich`, `python-dotenv` — for HTTP requests, logging, and env loading

---

## Directory Structure (Required)

```
swiftsolve/
├── pyproject.toml
├── README.md
├── .gitignore
├── .python-version
├── requirements.txt
└── src/
    └── swiftsolve/
        ├── main.py
        ├── api/
        │   └── routes.py
        ├── agents/
        │   ├── base.py
        │   ├── planner.py
        │   ├── coder.py
        │   ├── profiler.py
        │   └── analyst.py
        ├── controller/
        │   ├── solve_loop.py
        │   └── router.py
        ├── sandbox/
        │   ├── docker_utils.py
        │   └── run_in_sandbox.py
        ├── static_pruner/
        │   └── pruner.py
        ├── schemas/
        │   └── __init__.py  # Unified schema definitions
        ├── datasets/
        │   ├── parse_bigobench.py
        │   ├── parse_codeforces.py
        │   └── task_format.py
        ├── evaluation/
        │   ├── metrics.py
        │   └── stats.py
        ├── utils/
        │   ├── logger.py
        │   └── config.py
        └── tests/
            ├── test_agents.py
            └── test_pruner.py
```

---

## System Architecture & Agent Responsibilities

### 1. **Planner** (`Claude 4 Opus`)

- **Input**: Natural language task description.
- **Output**: Structured `PlanMessage` JSON with:
  - `algorithm`: brief strategy
  - `input_bounds`: variable ranges
  - `constraints`: problem-specific constraints (e.g., time/mem)
- **LLM API**: `anthropic==0.57.1`

### 2. **Static Pruner**

- Lightweight heuristic filter using regex + AST on plan descriptions.
- Rejects plans that are clearly inefficient:
  - Loop depth > 2 with `n >= 1e5`
  - Sort-inside-loop with `n >= 1e3`
  - Unbounded recursion with `n >= 1e4`
- **Fail-fast** to avoid wasting LLM calls.

### 3. **Coder** (`GPT-4.1` or `GPT-4o`)

- **Input**: JSON-formatted plan
- **Output**: ISO C++17 solution string in a `CodeMessage`
- **LLM API**: `openai==1.95.1`
- **Hooks**: May include logging calls (e.g., `std::chrono`) for benchmarking.

### 4. **Sandbox Profiler**

- **Environment**: Docker container with Ubuntu 20.04, g++, time, gprof
- **Execution**:
  - Mount code
  - Compile using: `g++ -O2 -std=c++17`
  - Run via `timeout`, measure wall time + peak RSS
- **Output**: `ProfileReport` with input size vs runtime/memory curves

### 5. **Complexity Analyst** (`GPT-4.1` or heuristic fallback)

- **Input**: ProfileReport JSON
- **Output**: `VerdictMessage`:
  - Efficiency boolean (pass/fail)
  - Optional `target_agent`: PLANNER or CODER
  - Optional `patch`: string fix for next round

---

## Execution Flow (Solve Loop)

```mermaid
graph TD
    A[Natural Language Prompt]
    A --> B[Planner (Claude)]
    B --> C[Static Pruner]
    C --> D[Coder (GPT-4)]
    D --> E[Profiler (Sandbox)]
    E --> F[Analyst (GPT-4)]
    F -->|Efficient| G[Final Output]
    F -->|Needs Fix| B
    F -->|Patch Code| D
```

Termination conditions:

- Passes all constraints
- < 5% improvement in time/memory
- Max 3 iterations
- Max 2 agent failures

---

## API Server (FastAPI)

- **POST /solve**
  - **Input**: `ProblemInput`
  - **Output**: `RunResult`
  - Runs the full Planner → Coder → Profiler → Analyst pipeline

Run locally:

```bash
uvicorn src.swiftsolve.main:make_app --reload
```

---

## CLI Entry Point

```bash
python src/swiftsolve/main.py --task_json input/task_001.json
```

Input format (JSON):

```json
{
  "task_id": "B001",
  "prompt": "Find the longest increasing subsequence.",
  "constraints": {"runtime_limit": 2000, "memory_limit": 512},
  "unit_tests": [
    {"input": "5\n1 2 3 4 5", "expected": "5"},
    {"input": "6\n5 3 4 8 6 7", "expected": "4"}
  ]
}
```

---

## Output Logging & Metrics

- All intermediate messages are stored at:
  ```
  ```

logs/{task\_id}/iter\_{i}/message.json

```
- Results for batch runs go to:
```

results/{task\_id}/seed\_{s}/iter\_{i}/

````
- Evaluation metrics:
  - `pass@1`, `pass@k`
  - `eff@k_runtime`, `eff@k_memory`
  - `TLE/MLE` rates
  - Iteration count

---

## Environment Setup

```bash
# Create virtualenv with Python 3.11.13
pyenv install 3.11.13
pyenv virtualenv 3.11.13 swiftsolve
pyenv local swiftsolve

# Install dependencies
pip install -r requirements.txt

# Create .env file with:
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...
````

---

## Testing

```bash
pytest -q src/swiftsolve/tests
```

Write tests for:

- All agents (mocked responses)
- Pruner rejection edge cases
- JSON schema validation

---

## Requirements Recap

| Component     | Version             |
| ------------- | ------------------- |
| Python        | 3.11.13             |
| FastAPI       | 0.116.1             |
| Pydantic      | 2.9.2               |
| OpenAI SDK    | 1.95.1              |
| Anthropic SDK | 0.57.1              |
| Uvicorn       | 0.35.0              |
| Docker        | 24.0+               |
| GCC           | 10.x (Ubuntu 20.04) |

---

## Final Notes

- Claude handles planning, GPT-4 handles coding and (optionally) analysis.
- Static pruner prevents wasteful prompts.
- Profiling happens in a secure container.
- Structured JSON protocols ensure agent modularity.

This file serves as the **single source of truth** for the technical architecture. It is sufficient to onboard any contributor into the codebase and begin development or debugging work without ambiguity.

---

