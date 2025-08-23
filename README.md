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

### Research Evaluation Endpoint

**POST** `/research/evaluate`

Start a research evaluation with your choice of scale:
- **Full evaluation**: 225 iterations (25 tasks × 3 seeds × 3 replans)
- **Mini evaluation**: 18 iterations (2 tasks × 3 seeds × 3 replans)

The evaluation runs in the background and returns immediately with tracking information.

#### Full Evaluation (225 iterations)

```bash
curl -X POST "http://localhost:8000/research/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "seeds": [42, 123, 456],
    "max_workers": 4,
    "output_dir": "research_results"
  }'
```

#### Mini Evaluation (18 iterations - Perfect for Testing!)

```bash
curl -X POST "http://localhost:8000/mini-research/evaluate" \
  -H "Content-Type: application/json" \
  -d '{
    "seeds": [42, 123, 456],
    "max_workers": 2,
    "output_dir": "mini_results"
  }'
```

#### Request Parameters

**Full Research Evaluation (`/research/evaluate`):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seeds` | `List[int]` | `[42, 123, 456]` | Random seeds for reproducibility |
| `max_workers` | `int` | `4` | Number of parallel workers |
| `output_dir` | `string` | `"research_results"` | Output directory for results |

**Mini Research Evaluation (`/mini-research/evaluate`):**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seeds` | `List[int]` | `[42, 123, 456]` | Random seeds for reproducibility |
| `max_workers` | `int` | `2` | Number of parallel workers |
| `output_dir` | `string` | `"mini_research_results"` | Output directory for results |

#### Response

```json
{
  "message": "Research evaluation started with ID: research_eval_mini_20250823_143022",
  "evaluation_id": "research_eval_mini_20250823_143022",
  "estimated_duration_minutes": 4.5,
  "total_runs": 18
}
```

### Research Status Endpoint

**GET** `/research/status/{evaluation_id}`

Check the status of a running research evaluation.

```bash
curl -X GET "http://localhost:8000/research/status/research_eval_20250124_143022"
```

#### Response (Running)

```json
{
  "evaluation_id": "research_eval_20250124_143022",
  "status": "running",
  "message": "Evaluation is still in progress",
  "output_directory": "research_results/research_eval_20250124_143022"
}
```

#### Response (Completed)

```json
{
  "evaluation_id": "research_eval_20250124_143022",
  "status": "completed",
  "message": "Evaluation completed successfully",
  "summary": {
    "total_runs": 225,
    "successful_runs": 187,
    "success_rate_percent": 83.1,
    "total_duration_minutes": 52.3,
    "avg_duration_per_run_seconds": 13.9
  },
  "results_files": {
    "detailed_results": "research_results/research_eval_20250124_143022/research_results_20250124_162245.json",
    "analysis": "research_results/research_eval_20250124_143022/research_analysis_20250124_162245.json"
  }
}
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
- **Mini-Run Mode**: Fast 18-iteration testing (2 tasks vs 25) for setup validation

## Quick Start Guide

### 1. Test Your Setup (Mini-Run)

Before running the full 225-iteration benchmark, test your setup with the mini-run:

```bash
# Start the API server
PYTHONPATH=src uvicorn swiftsolve.main:app --host 127.0.0.1 --port 8000 &

# Run mini evaluation (18 iterations, ~5 minutes)
curl -X POST "http://localhost:8000/mini-research/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'

# Or use the test script
python test_mini_run.py
```

**Mini-run includes:**
- 1 BigO(Bench) task: Binary Search (O(log n))
- 1 Codeforces task: CF1285A (O(n))
- Same comprehensive analysis as full run
- 12.5x faster for testing!

### 2. Full Research Evaluation

Once your setup is verified, run the complete benchmark:

```bash
# Full evaluation (225 iterations, ~60 minutes)
curl -X POST "http://localhost:8000/research/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 4}'
```

## CLI Usage

### Basic Pipeline
```bash
python src/swiftsolve/main.py --task_json src/swiftsolve/test.json
```

### Dry-Run Batch Mode
Test SwiftSolve with predefined tasks across difficulty levels:

```bash
# Install required dependency (if you didnt already)
pip install aiohttp

# List all available tasks (3 Easy, 5 Medium, 2 Hard)
python dry_run_batch.py --list-tasks

# Run first 5 tasks (default)
python dry_run_batch.py

# Run specific number of tasks with custom timeout
python dry_run_batch.py --tasks 3 --timeout 120

# Run all 10 tasks with custom API endpoint
python dry_run_batch.py --tasks 10 --host localhost --port 8080
```

**Features:**
- **No external datasets needed** - uses built-in tasks
- **Comprehensive reporting** - success rates, timing, difficulty breakdown
- **JSON output** - results saved to `dry_run_results/batch_TIMESTAMP.json`
- **Real-time progress** - live status updates during execution
- **Health checking** - validates API connectivity before starting

### Batch Evaluation
```bash
python -m src.swiftsolve.evaluation.batch_runner --benchmark --seeds 42 123 456
```

### Create Sample Datasets
```bash
python -m src.swiftsolve.evaluation.batch_runner --create-samples
```

### Test Mini-Run Feature
```bash
# Interactive test script for mini-run functionality
python test_mini_run.py
```

## Evaluation Modes

| Mode | Tasks | Iterations | Duration | Use Case |
|------|-------|------------|----------|----------|
| **Mini-Run** | 2 tasks | 18 iterations | ~5 minutes | Setup testing, development |
| **Full Run** | 25 tasks | 225 iterations | ~60 minutes | Research benchmarking |

The mini-run includes 1 BigO(Bench) task (Binary Search) and 1 Codeforces task (CF1285A) with the same comprehensive analysis pipeline as the full evaluation.
