# ENVIRONMENT.md

Canonical, **non‑Docker** environment specification for SwiftSolve (anonymous artifact). Results reported in the paper refer to this environment unless otherwise noted.

> **Summary:** Linux (Ubuntu 22.04), Python **3.12.x**, **g++ ≥ 12** (C++17), CPU‑only.

---

## 1) Platform & Hardware

* **OS (canonical):** Ubuntu 22.04 LTS (or equivalent recent Linux)
* **CPU:** 2 vCPU minimum; **4 vCPU recommended** for the full sweep
* **RAM:** 8 GB recommended (≥ 4 GB minimum)
* **GPU:** not used
* **TZ/Locale:** UTC, `C.UTF-8`

If you run on macOS, install Homebrew GCC and set `CXX=g++-13` (or newer). Timings may differ from Linux reference.

---

## 2) Language & Toolchain

* **Python:** 3.12.x (project requires ≥ 3.12)
* **C++ compiler (required):** GNU **g++ 12+** with C++17 support
* **Profiler compile flags:** `-O3 -std=c++17 -march=native -ffast-math`

Install on Ubuntu 22.04:

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip g++-12
```

macOS (non‑canonical but supported):

```bash
# Install Homebrew GCC
brew install gcc
# Prefer GCC over Apple Clang for C++17 + flags
export CXX=g++-13
```

Verify versions:

```bash
python3.12 --version     # expect 3.12.x
python3.12 -c "import sys; print(sys.version)"
g++ --version            # expect gcc (not Apple clang), ≥ 12
```

---

## 3) Python Environment Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.lock   # pin exact deps used for your run
```

Recommended key packages (versions may vary; see `requirements.lock`):

* fastapi, uvicorn, pydantic‑v2
* numpy, scipy, matplotlib
* httpx/aiohttp (if used), python‑dotenv (optional)

---

## 4) Environment Variables

### 4.1 Determinism & single‑threaded math

```bash
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TZ=UTC
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
```

### 4.2 LLM provider keys

```bash
export OPENAI_API_KEY=<<<FILL_ME>>>
export ANTHROPIC_API_KEY=<<<FILL_ME>>>
```

### 4.3 Module path

```bash
export PYTHONPATH="${PWD}/src"
```

---

## 5) Seeds, Tasks, and Limits

* **Seeds:** `configs/seeds.txt` contains

  ```
  42
  123
  456
  ```

  (You may override seeds via CLI flags.)

* **Task indices (IDs only):**

  * `configs/bigobench.json` — 16 tasks (e.g., `BIGOBENCH_1718`, `BIGOBENCH_1414`, …)
  * `configs/codeforces.json` — 10 tasks (e.g., `CF1284A`, `CF1285A`, …)

* **Resource limits (default):**

  * CPU time per compiled program: **2 s**
  * Resident memory (RSS): **512 MB**
  * Stack size: **256 MB**
  * Max replans per task‑seed: **≤ 3**
  * Default concurrency: **4 workers** (tune with `--max-workers`)

> Limits are enforced in the native runner via OS RLIMITs where available; see `SECURITY.md`.

---

## 6) LLM Models & Roles (as used in paper)

* **Planner:** `claude-4-opus-20250514`
* **Coder:** `gpt-4.1`
* **Analyst:** `gpt-4.1`
* **Baseline:** `claude-4-opus-20250514`

Model IDs are logged in run metadata where relevant; rotate to current API equivalents if those IDs are sunset by providers.
---

## 7) Validation Checklist

* [ ] `python3.12 --version` prints 3.12.x
* [ ] `g++ --version` shows **gcc** ≥ 12 (not Apple clang)
* [ ] `pip install -r requirements.txt` succeeds; `requirements.lock` exported
* [ ] `OPENAI_API_KEY` & `ANTHROPIC_API_KEY` set
* [ ] `PYTHONPATH=${PWD}/src` set
* [ ] `configs/bigobench.json`, `configs/codeforces.json`, `configs/seeds.txt` present
* [ ] Mini run completes and writes `runs/mini_*/summary.json`

---

## 8) Notes

* We do **not** redistribute third‑party problem statements; see `DATA_LICENSES.md`.
* Compiled C++ programs do **not** use network; only LLM API calls require internet access.
* For strict isolation or corporate environments, you may run in a VM with outbound access limited to LLM endpoints.
