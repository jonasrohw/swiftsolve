# REPRODUCIBILITY.md

SwiftSolve (anonymous artifact) — **native, non‑Docker** reproduction guide. This document provides one‑command paths to rerun the **mini** (18 iters) and **full** (225 iters) benchmarks and to regenerate all figures from your logs.

> **Scope.** Canonical environment is **Linux (Ubuntu 22.04)**, **Python 3.12.x**, **g++ ≥ 12**. macOS works pragmatically (Homebrew GCC), but the ground‑truth numbers we disclose in the paper refer to the Linux setup below.

---

## 0) Prerequisites

* Python **3.12+** (required)
* GCC/G++ **12+** with C++17
* Network access for LLM APIs (the generated C++ binaries **do not** use network)
* API keys in env: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`

> **Compiler flags used in the profiler**: `-O3 -std=c++17 -march=native -ffast-math`

### Install on Ubuntu 22.04

```bash
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3-pip g++-12 curl git
```

### Create the Python environment

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip freeze > requirements.lock
```

### Set environment variables

```bash
# LLM provider keys (required)
export OPENAI_API_KEY=<<<FILL_ME>>>
export ANTHROPIC_API_KEY=<<<FILL_ME>>>

# Determinism and single-threaded math backends
export PYTHONHASHSEED=0
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1
export TZ=UTC
export LANG=C.UTF-8
export LC_ALL=C.UTF-8

# Project imports
export PYTHONPATH="${PWD}/src"
```

---

## 1) Seeds and Task Indices (IDs only)

This repo ships **IDs/indices** (no problem text):

* `configs/seeds.txt`

  ```
  42
  123
  456
  ```
* `configs/bigobench.json` — 16 tasks (IDs you provided)
* `configs/codeforces.json` — 10 tasks (IDs you provided)

These files are consumed by the batch runner. You may override seeds at the CLI.

---

## 2) Mini‑run (18 iterations) — sanity check

**Goal:** validate installation and end‑to‑end pipeline (2 tasks × 3 seeds × ≤3 replans).

```bash
source .venv/bin/activate
export PYTHONPATH="${PWD}/src"

# Either use the convenience test script...
python test_mini_run.py \
  --seeds 42 123 456 \
  --max-workers 2 \
  --sandbox-timeout-sec 2 \
  --sandbox-mem-mb 512 \
  --outdir runs/mini_$(date -u +%Y%m%d_%H%M%S)

# ...or invoke the batch runner explicitly (equivalent behavior)
python -m src.swiftsolve.evaluation.batch_runner \
  --mini \
  --bigobench-config configs/bigobench.json \
  --codeforces-config configs/codeforces.json \
  --seeds 42 123 456 \
  --max-workers 2 \
  --sandbox-timeout-sec 2 \
  --sandbox-mem-mb 512 \
  --output-dir runs/mini_$(date -u +%Y%m%d_%H%M%S)
```

**Outputs**

* Per‑attempt JSON logs under `runs/mini_*/logs/…` (schema v1.0.0; see ARTIFACTS.md)
* Run summary: `runs/mini_*/summary.json`

---

## 3) Full benchmark (225 iterations)

**Goal:** reproduce paper‑level results (25 tasks × 3 seeds × ≤3 replans).

```bash
source .venv/bin/activate
export PYTHONPATH="${PWD}/src"

python -m src.swiftsolve.evaluation.batch_runner \
  --benchmark \
  --bigobench-config configs/bigobench.json \
  --codeforces-config configs/codeforces.json \
  --seeds 42 123 456 \
  --max-workers 4 \
  --sandbox-timeout-sec 2 \
  --sandbox-mem-mb 512 \
  --output-dir runs/full_$(date -u +%Y%m%d_%H%M%S)
```

**Outputs**

* Logs in `runs/full_*/logs/…` and `runs/full_*/summary.json`

> If you are API‑rate limited, lower `--max-workers` to 1–2; the runner backs off and retries.

---

## 4) Regenerating Figures

All figure scripts live in **`figures/`** and write `figures/fig_k.png`.

### 4.1 Figure 1 (Duration histogram)

The current `figures/fig_1.py` (or `fig1.py`) may read a specific filename (e.g., `research_results_20250824_192037.json`). If so, symlink your newest full‑run results to the expected name before running:

```bash
# Find your latest full-run results JSON (pattern may vary by your runner)
LATEST_JSON=$(ls -1 runs/full_*/research_results_*.json | tail -n 1)
ln -sf "$LATEST_JSON" research_results_20250824_192037.json

# Generate Figure 1
python figures/fig_1.py   # or: python figures/fig1.py
```

> **Recommendation (post‑review):** update `fig_1.py` to accept `--input <path>` and `--out <path>`; for now, the symlink preserves reproducibility.

### 4.2 Figures 2–4

```bash
python figures/fig_2.py   # writes figures/fig_2.png
python figures/fig_3.py   # writes figures/fig_3.png
python figures/fig_4.py   # writes figures/fig_4.png
```

If your scripts support explicit flags, you can pass `--runs "runs/full_*" --out figures/fig_k.png`.

---

## 5) (Optional) Exporting Tables/CSVs

If your repo includes a table export utility:

```bash
python -m src.swiftsolve.analysis.make_tables --runs "runs/full_*" --out tables/
```

If not, ship the CSVs alongside the figure scripts, or keep the pre‑rendered plots; see **ARTIFACTS.md** for the files you chose to bundle.

---

## 6) Statistical Reporting

Unless noted otherwise, we report **mean ± 95% CI** across seeds.
Significance: paired *t*-tests for continuous metrics; McNemar for binary outcomes.
Holm–Bonferroni correction across tasks.
Exact seeds and sample sizes are in `configs/seeds.txt` and the logs.

---

## 7) Checksums (for ARTIFACTS.md)

Record SHA256 and sizes for any **shipped** artifacts (e.g., figure PNGs, config JSONs):

```bash
# Linux
sha256sum figures/fig_1.png figures/fig_2.png figures/fig_3.png figures/fig_4.png
stat -c%s  figures/fig_1.png

# macOS
shasum -a 256 figures/fig_1.png figures/fig_2.png figures/fig_3.png figures/fig_4.png
stat -f%z  figures/fig_1.png
```

Paste the values into **ARTIFACTS.md**.

---

## 8) Troubleshooting

* **API rate limits:** reduce `--max-workers` to 1–2. The runner retries with backoff.
* **Compiler mismatch:** ensure `g++ --version` reports 12+ and your PATH points to GCC, not Apple Clang.
* **Non‑Linux runtimes:** Homebrew `gcc` works, but timings may differ from Ubuntu reference.
* **Figure 1 missing input:** re‑create the symlink to your latest `research_results_*.json` as shown in §4.1.
