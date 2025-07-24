# SwiftSolve – Comprehensive Technical Specification (v1.0.0)

> **Read this once – build correctly forever.**  Any deviation without an approved change‑request (CR) will be rejected at review.
>
> Latest update: 2025‑07‑24  ▪  Schema version: 1.0.0  ▪  Maintainer: VEAB

---

## 1  Project Context  📰

### 1.1  Problem Statement

Large Language Models (LLMs) can already pass ≥ 90 % of unit tests on many coding benchmarks, yet they frequently blow past strict runtime (TLE) and memory (MLE) limits in competitive‑programming and latency‑sensitive production systems.  SwiftSolve closes that gap by **co‑optimising correctness and Big‑O efficiency** through a modular, agentic pipeline.

### 1.2  High‑Level Storyboard

1. A user (human or orchestrator) POSTs a natural‑language problem description to `/solve` or feeds a JSON task to the CLI runner.
2. The **Planner** (Claude 4 Opus) converts prose into a structured algorithmic sketch.
3. A **Static Pruner** shields the system from obviously inefficient plans (e.g. `O(n²)` sort‑in‑loop patterns).
4. The **Coder** (GPT‑4.1) turns the approved plan into ISO C++ 17 source.
5. The **Profiler** compiles and executes the code inside a deterministic Docker sandbox, capturing wall‑time + RSS across logarithmic input scales.
6. The **Complexity Analyst** analyses the telemetry, fits empirical complexity, checks constraints, and either: \* declares success, or \* routes a JSON patch to the Coder (local fix) or the Planner (algorithmic overhaul).
7. All artefacts are persisted as JSON under `logs/<task_id>/iter_<i>/` for full replay.

### 1.3  Design Principles

| Principle           | Rationale                                                  |
| ------------------- | ---------------------------------------------------------- |
| **Modularity**      | Swap Planner/Coder models independently                    |
| **Determinism**     | Seed control + cached prompts + Docker sandbox             |
| **Cost Awareness**  | Static pruning + early termination to minimise token spend |
| **Reproducibility** | Every artefact logged with schema version & UTC timestamp  |
| **Security**        | Untrusted C++ runs inside cgroup‑limited container         |

### 1.4  Agent Contract Summary

| Agent    | Model / Tool        | Function                           | In → Out                           |
| -------- | ------------------- | ---------------------------------- | ---------------------------------- |
| Planner  | Claude 4 Opus       | Algorithm strategy synthesis       | `ProblemInput` → `PlanMessage`     |
| S‑Pruner | regex + AST         | Heuristic plan rejection           | `PlanMessage` → bool               |
| Coder    | GPT‑4.1              | C++ 17 code generation             | `PlanMessage` → `CodeMessage`      |
| Profiler | g++ + /usr/bin/time | Empirical runtime & memory capture | `CodeMessage` → `ProfileReport`    |
| Analyst  | GPT‑4.1 + heuristic  | Complexity fit & routing decision  | `ProfileReport` → `VerdictMessage` |

### 1.5  End‑to‑End Control Flow (verbose)

1. **Validation** – Incoming JSON must satisfy `ProblemInput` schema; otherwise FastAPI 422.
2. **Plan Generation** – Planner prompt contains: problem text, required JSON keys, max tokens 512.  Response must parse under `PlanMessage.model_validate()`.
3. **Static Prune** – If `validate(plan)==False`  → return `RunResult(status=STATIC_PRUNE_FAILED)`.
4. **Iterative Loop** (`iter = 0..max_iter−1`)
   1. Call **Coder**; response parsed into `CodeMessage`.  Failure? retry once → else `RunResult(status=FAILED)`.
   2. **Profiler** compiles with `g++ -O2 -std=c++17`.  Resource caps: wall = `runtime_limit+250` ms, RSS ≤ 512 MB, stack 256 MB.  Parse `/usr/bin/time -v`.
   3. **Analyst** receives `ProfileReport`, fits log‑log slope, classifies complexity & memory class; returns `VerdictMessage`.
   4. Check `verdict.efficient`.  If true → success.  Else route:
      - `target_agent==CODER` → patch prompt; Coder reruns.
      - else → Planner revise prompt; go to 4.1.
   5. Stop if `perf_gain < diminish_delta` or `iter==max_iter−1` or ≥ 2 agent crashes.
5. Assemble `RunResult`, write to `logs_uri`, return via API.

### 1.6  JSON Communication Spec (excerpt)

```jsonc
// PlanMessage (envelope + payload)
{
  "type": "plan",
  "task_id": "CF1285C",
  "iteration": 0,
  "timestamp_utc": "2025‑07‑24T20:41:11Z",
  "schema_version": "1.0.0",
  "algorithm": "two‑pointer sliding window",
  "input_bounds": {"n": 100000},
  "constraints": {"runtime_limit": 2000, "memory_limit": 512}
}
```

*All six message types (**`PlanMessage`**, **`CodeMessage`**, **`ProfileReport`**, **`VerdictMessage`**, **`ProblemInput`**, **`RunResult`**) are fully defined in **`schemas/__init__.py`** and ****must not**** be duplicated elsewhere.*

### 1.7  Static Pruner Rulebook

- **Loop depth** > 2 & `n ≥ 1e5`  → reject.
- **Sort‑in‑loop** & `n ≥ 1e3`      → reject.
- **Unbounded recursion** & `n ≥ 1e4` → reject.
- Configurable via `static_pruner/pruner.toml` hot‑reload.

### 1.8  Sandbox Constraints

- Namespace: non‑root, seccomp `docker/default` + no net.
- `resource.setrlimit`:
  - `RLIMIT_AS` = 512 MB
  - `RLIMIT_STACK` = 256 MB
  - `RLIMIT_FSIZE` = 50 MB (stdout/stderr cap)
- Crash codes propagated to controller as `RunStatus.SANDBOX_ERROR`.

### 1.9  Evaluation Metrics

| Metric          | Definition                                       |
| --------------- | ------------------------------------------------ |
| pass\@k         | ≥ 1 of top‑k programs passes official unit tests |
| eff\@k\_runtime | ≥ 1 of top‑k passes time limit                   |
| eff\@k\_memory  | ≥ 1 of top‑k stays < memory limit                |
| TLE/MLE rate    | % of executions exceeding runtime or memory cap  |
| Iteration count | Mean #loops until `efficient==true`              |

### 1.10  Datasets

- **BigO(Bench)** – 50 tasks across O(1)–O(n²).
- **Codeforces Div‑2** – 25 tasks (800–1800 rating).
- Stored under `datasets/<source>/task_<id>.json` following `task_format.py`.

### 1.11  Security & Privacy

No user code is stored beyond telemetry; LLM prompts are cached encrypted at rest (AES‑GCM) if `CACHE_ENCRYPT_KEY` is set.

### 1.12  OpenAPI Exposure

- `/solve` – POST – body `ProblemInput`, response `RunResult`.
- `/healthz` – GET – returns 200 + git hash + schema version.

---

## 2  Tech Stack  🛠️

### 2.1  Languages & Runtimes

- Python 3.11.13 (orchestrator)
- C++ 17 (generated code)
- Bash + GNU coreutils (sandbox scripts)

### 2.2  Key Libraries

| Domain   | Package                           | Version         | Notes                    |
| -------- | --------------------------------- | --------------- | ------------------------ |
| API      | FastAPI, Uvicorn[standard]        | 0.116.1         | ASGI + Hot reload        |
| LLM SDKs | openai, anthropic                 | 1.95.1 · 0.57.1 | Model calls              |
| Schema   | Pydantic v2.x + pydantic‑settings | 2.9.2           | Validation + env config  |
| Testing  | pytest, pytest‑asyncio            | 8.1.0 · 0.23.5  | Unit & async tests       |
| Lint     | Ruff, Mypy, Pre‑commit            | latest          | CI static analysis       |
| Logging  | Rich, loguru (optional)           | 13.7.1          | Colour logs + tracebacks |
| Data     | pandas, plotnine, orjson          | pinned          | Evaluation & plotting    |

### 2.3  Infrastructure

- Docker 24.x  ➜ Ubuntu 20.04 base image.
- Terraform 1.8.x  ➜ GKE Autopilot cluster.
- GitHub Actions CI  ➜ 3.11/3.12 matrix, push & PR.

### 2.4  Environment Variables

| Variable            | Purpose                                |
| ------------------- | -------------------------------------- |
| `OPENAI_API_KEY`    | GPT‑4.1 access                          |
| `ANTHROPIC_API_KEY` | Claude 4 Opus access                   |
| `LOG_LEVEL`         | Default `INFO`, override to `DEBUG`    |
| `CACHE_ENCRYPT_KEY` | 32‑byte key for encrypted prompt cache |

### 2.5  Version Pinning Rules

- Semantic pin (`==`) for prod deps in `requirements.txt`.
- Dev‑only tools (`ruff`, `mypy`) in `requirements-dev.txt`.
- `pyproject.toml` sets `requires-python == 3.11.13`.

---

## 3  Repository Layout & File Descriptions  📁

```text
src/swiftsolve/
├── main.py               # FastAPI + CLI entry
├── api/routes.py         # /solve, /healthz
├── controller/
│   ├── solve_loop.py     # Core orchestration
│   └── router.py         # FastAPI wrapper (planned)
├── agents/
│   ├── base.py           # Agent ABC + retry/caching hooks
│   ├── planner.py        # Claude client, prompt templates
│   ├── coder.py          # GPT‑4.1 client, code‑json extraction
│   ├── profiler.py       # Sandbox wrapper + telemetry parse
│   └── analyst.py        # Complexity fit + patch routing
├── static_pruner/pruner.py # Regex + AST heuristics
├── sandbox/
│   ├── run_in_sandbox.py   # g++ compile & exec with limits
│   └── docker_utils.py     # image build & push (WIP)
├── schemas/__init__.py     # Unified Pydantic v2 models
├── datasets/
│   ├── parse_bigobench.py  # HTML/JSON → task format
│   ├── parse_codeforces.py # Scrape + IO normalisation
│   └── task_format.py      # Shared spec & validation
├── evaluation/
│   ├── metrics.py          # pass@k, eff@k_* calculators
│   └── stats.py            # DataFrame aggregation & plots
├── utils/
│   ├── config.py           # pydantic‑settings Settings()
│   └── logger.py           # Colour + rotating logs
└── tests/
    ├── test_agents.py      # Planner/Coder mocks
    ├── test_pruner.py      # Heuristic edge cases
    ├── test_schema.py      # JSON round‑trip & forbid extras
    └── test_sandbox.py     # Compile & run smoke test
```

Every file **must** include docstring headers explaining purpose, inputs, and side‑effects.

---

## 4  Task Mega‑Spec  📋

The following hierarchy represents **all work items** required for SwiftSolve v1.0.  Completed items are prefixed ✔.

### 4.1  Phase A – Foundations

- **A1 Environment Setup**
  - A1.1 Create pyenv 3.11.13 and poetry project.
  - A1.2 Add `requirements.txt` & `requirements-dev.txt`.
  - A1.3 Configure pre‑commit (ruff, black, mypy, isort).
- **A2 Schema Layer**
  - A2.1 Design envelope & message enums.
  - ✔ A2.2 Implement `schemas/__init__.py` with Pydantic v2.
  - A2.3 Add `test_schema.py` (field presence, forbid extras).
- **A3 Logging & Config**
  - ✔ A3.1 `utils.logger` colour + rotating handler.
  - ✔ A3.2 `utils.config` Settings singleton via pydantic‑settings.

### 4.2  Phase B – Core Loop (MVP)

- **B1 Planner Agent**
  - B1.1 Prompt template design (JSON‑only output).
  - B1.2 Claude client wrapper with retry & cache (Sqlite + orjson).
  - B1.3 Unit tests: valid JSON, fallback plan.
- **B2 Static Pruner**
  - ✔ B2.1 Regex + AST rule implementation.
  - B2.2 `pruner.toml` external rule config.
  - B2.3 Benchmark false‑positive rate on 100 plans.
- **B3 Coder Agent**
  - B3.1 JSON‑only code prompt; ensure includes & I/O.
  - B3.2 Escape‑sequence cleaning; compile smoke test.
  - B3.3 Inject optional chrono & memory hooks on `debug` flag.
- **B4 Solve Loop v0**
  - B4.1 Integrate Planner → Pruner → Coder chain.
  - B4.2 FastAPI `/solve` returns stub `RunResult`.

### 4.3  Phase C – Profiler & Analyst

- **C1 Sandbox Runtime**
  - C1.1 Dockerfile (Ubuntu 20.04, g++‑10, time, gprof).
  - C1.2 `run_in_sandbox.py` compile→run→time→RSS.
  - C1.3 `resource.setrlimit` caps; stack 256 MB.
- **C2 Profiler Agent**
  - C2.1 Generate logarithmic input scales.
  - C2.2 Parse `/usr/bin/time -v` (regex).
  - C2.3 Produce `ProfileReport`.
- **C3 Complexity Analyst**
  - C3.1 Heuristic slope fit (log‑log).
  - C3.2 GPT‑4.1 fallback for ambiguous curves.
  - C3.3 Patch routing logic (`TargetAgent`).
- **C4 Termination Logic**
  - C4.1 Implement `perf_gain` check vs `diminish_delta`.
  - C4.2 Loop abort on 2 agent failures.

### 4.4  Phase D – Dataset & Metrics

- **D1 Dataset Parsers**
  - D1.1 HTML scrape BigO(Bench) tasks.
  - D1.2 REST scrape Codeforces tasks.
  - D1.3 Validate against `task_format.py`.
- **D2 Batch Runner**
  - D2.1 CLI flags: `--benchmark`, `--seeds`, `--replans`.
  - D2.2 Multiprocess pool, progress bar (tqdm).
  - D2.3 Store artefacts under `results/<task>/seed_<s>/`.
- **D3 Metrics & Plots**
  - D3.1 Calc pass\@k, eff\@k\_\*, TLE/MLE.
  - D3.2 Plot runtime curves (plotnine) per class.
  - D3.3 Generate Markdown + CSV summary.

### 4.5  Phase E – Deployment & Publication

- **E1 Infrastructure as Code**
  - E1.1 Terraform modules for GKE Autopilot.
  - E1.2 GCS bucket + Cloud NAT egress.
- **E2 Scaling Run**
  - E2.1 Run 12 000 cycles; monitor cost.
  - E2.2 Download results + run evaluation.
- **E3 Paper & Artefact**
  - E3.1 Write methodology, experiments, ablations.
  - E3.2 Insert tables: eff\@1, iteration counts.
  - E3.3 Prepare artefact for NeurIPS reproducibility checklist.

---

Note that for testing, we will be using gpt-4.1-mini and claude-sonnet-4 for budgeting reasons.