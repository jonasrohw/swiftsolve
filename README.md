# SwiftSolve

A multi-agent code generation framework that synthesizes functionally correct and computationally efficient C++ code from natural language problem statements.

## Build Instructions

Set the `PYTHONPATH` environment variable to wherever the SwiftSolve directory is located.
For example, if you cloned the repo into your home directory:

```sh
export PYTHONPATH="${HOME}/swiftsolve/src/swiftsolve"
```

Provide API keys using `OPENAI_API_KEY` and `ANTHROPIC_API_KEY`.

## Environment Setup

1. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```
or if you're on Windows,

```bash
venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
export OPENAI_API_KEY=your_openai_key_here
export ANTHROPIC_API_KEY=your_anthropic_key_here
```

## Running the API Server

Start the FastAPI server:

```bash
source venv/bin/activate
PYTHONPATH=src uvicorn swiftsolve.main:app --host 127.0.0.1 --port 8000 --reload
```

The server will be available at `http://localhost:8000`

**Note**: The `PYTHONPATH=src` is required to resolve relative imports correctly.

## API Usage

### Health Check Endpoint

**GET** `/healthz`

Check if the server is running and get version information.

```bash
curl -X GET "http://localhost:8000/healthz"
```

### Solve Endpoint

**POST** `/solve`

Submit a programming problem and get an optimized C++ solution with real performance profiling.

#### Request Format

```bash
curl -X POST "http://localhost:8000/solve" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "test1",
    "prompt": "Add two integers and output their sum",
    "constraints": {"runtime_limit": 2000},
    "unit_tests": [
      {"input": "5 3", "output": "8"},
      {"input": "10 20", "output": "30"}
    ]
  }'
```

#### Response Format

```json
{
  "status": "success",
  "code": "#include <iostream>\nusing namespace std;\n\nint main() {\n    int a, b;\n    cin >> a >> b;\n    cout << a + b << endl;\n    return 0;\n}",
  "profile": {
    "type": "profile_report",
    "task_id": "test1",
    "iteration": 0,
    "timestamp_utc": "2025-07-23T21:25:37.087958Z",
    "schema_version": "1.0.0",
    "input_sizes": [1000, 5000, 10000, 50000, 100000],
    "runtime_ms": [1.1, 1.1, 1.1, 1.1, 1.1],
    "peak_memory_mb": [1.0, 1.0, 1.0, 1.0, 1.0],
    "hotspots": {}
  }
}
```

#### Request Parameters

- `task_id` (string): Unique identifier for the task
- `prompt` (string): Natural language description of the problem
- `constraints` (object): Execution constraints
  - `runtime_limit` (int): Maximum runtime in milliseconds
  - `memory_limit` (int): Maximum memory in megabytes
- `unit_tests` (array): Test cases to validate the solution
  - `input` (string): Input data for the test
  - `output` (string): Expected output

## Architecture

SwiftSolve uses a comprehensive multi-agent pipeline with iterative optimization:

### Core Agents
1. **Planner** (Claude) - Creates algorithmic plans from natural language
2. **Static Pruner** - Filters out obviously inefficient approaches  
3. **Coder** (GPT-4.1) - Generates C++ code from the plan
4. **Profiler** - Compiles and benchmarks code with real GNU time measurements
5. **Analyst** - Evaluates efficiency using heuristics + LLM fallback for ambiguous cases

### Advanced Features
- **Iterative Feedback Loop**: Analyst provides patches to Coder or feedback to Planner
- **Crash Handling**: Pipeline aborts gracefully after 2 agent failures
- **Real Performance Profiling**: Actual runtime/memory measurements across input scales
- **LLM Fallback**: GPT-4.1 analyzes ambiguous performance curves when heuristics fail

### Research & Evaluation Infrastructure
- **Dataset Support**: BigO(Bench) and Codeforces task parsers
- **Evaluation Metrics**: pass@k, eff@k_runtime, eff@k_memory, TLE/MLE rates
- **Batch Runner**: Systematic benchmarking with multiprocessing and progress tracking
- **Statistical Analysis**: Comprehensive reporting with plots and CSV exports

## CLI Usage

### Basic Pipeline
```bash
python src/swiftsolve/main.py --task_json src/swiftsolve/test.json
```

### Batch Evaluation
```bash
python -m src.swiftsolve.evaluation.batch_runner --benchmark --seeds 42 123 456
```

### Create Sample Datasets
```bash
python -m src.swiftsolve.evaluation.batch_runner --create-samples
```
