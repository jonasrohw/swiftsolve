# SECURITY.md

Security & sandbox policy for the **native (non‑Docker)** SwiftSolve artifact. The goal is to execute *generated C++ programs* safely and predictably under strict resource limits while keeping the setup simple for reviewers.

> **Trust model.** Inputs are public programming tasks (IDs only). The framework generates and compiles its own C++ code; it does **not** fetch or execute third‑party binaries. LLM API calls require network; compiled programs are expected to be offline.

---

## 1) Execution model

* All compiled programs run as **child processes** of the Python runner in an isolated working directory under `runs/<timestamp>/`.
* No privileged operations are attempted; **no `sudo`**; the process runs as a normal user.
* The runner sanitizes environment variables inherited by child processes to avoid leaking credentials.

---

## 2) Resource limits (defaults)

Enforced via POSIX RLIMITs (Linux) and/or shell `ulimit` where supported. These match the paper’s evaluation settings.

* **CPU time (per program):** `2 s`
* **Resident memory (RSS):** `512 MB`
* **Address space (virtual memory):** `≤ 1.5 GB` (guardrail; optional)
* **Stack size:** `256 MB`
* **Max processes/threads:** small cap (e.g., `64`) to prevent fork bombs
* **Open files:** small cap (e.g., `256`)

> Exact values are configurable via CLI flags (e.g., `--sandbox-timeout-sec`, `--sandbox-mem-mb`) and mirrored in the paper.

### 2.1 Quick setup (shell)

```bash
# Optional: apply hard caps to the current shell before running
ulimit -t 2              # CPU seconds per process
ulimit -v 1572864        # virtual memory (kB) ≈ 1.5 GB
ulimit -m 524288         # RSS (kB) ≈ 512 MB (may be ignored on some kernels)
ulimit -s 262144         # stack (kB) = 256 MB
ulimit -n 256            # open files
ulimit -u 64             # max user processes
```

### 2.2 Linux `prlimit` example

```bash
# Apply per‑PID limits (here, to the current shell PID) before launching the run
prlimit --pid $$ \
  --cpu=2 \
  --as=1610612736 \
  --rss=536870912 \
  --stack=268435456 \
  --nproc=64 \
  --nofile=256
```

> The native runner also attempts to set RLIMITs programmatically using Python’s `resource.setrlimit()` on Linux. Kernel support may vary by distro.

---

## 3) Filesystem isolation

* Each run writes only under `./runs/...` and `./figures`/`./tables` when regenerating outputs.
* The runner does **not** write outside the repository directory.
* Temporary files created by the compiler are cleaned up when possible.

---

## 4) Networking policy

* **LLM API access**: required for agent calls (Planner/Coder/Analyst). These requests run in the **parent Python process**.
* **Compiled C++ programs**: are intended to be offline and should not open sockets. The framework does not pass credentials or network endpoints to child processes.
* **Stricter isolation (optional)**: run on an offline VM, or launch child programs with network disabled (e.g., Linux network namespace). If you need stronger isolation without containers, consider tools like `unshare -n`, `firejail --net=none`, or a host firewall rule to block egress only for child PIDs.

> The artifact does **not** require Docker. Containerization or VM isolation is optional and left to the operator’s policy.

---

## 5) Privileges & capabilities

* Processes run as an unprivileged user; **no setuid** binaries are invoked.
* We do not request Linux capabilities (`CAP_*`); on typical desktops/VMs, no ambient capabilities are present for regular users.
* We do not modify kernel parameters or load modules.

---

## 6) Input handling & path hygiene

* Problem **statements** are not bundled; only task **IDs** are used (see `DATA_LICENSES.md`).
* Paths passed to the compiler and runner are repository‑relative.
* The pipeline rejects paths containing `..` segments or absolute paths when preparing compilation or execution commands.

---

## 7) Logging & privacy

* Logs contain benchmark metadata and performance measurements; they **must not** include API keys, cookies, or problem statements.
* Timestamps are recorded in UTC. No user PII is collected.
* If you find a sensitive value in a log, delete the file and open an issue.

---

## 8) Misuse policy

* **Do not** use this system to submit answers to **live contests**.
* **Do not** increase limits to run untrusted third‑party binaries.
* Respect dataset/online‑judge ToS when fetching or interacting with problems.

---

## 9) Known limitations

* RLIMIT semantics differ across OSes; macOS ignores some memory caps. For canonical results and enforcement, prefer Linux.
* Without OS‑level network namespaces, a malicious program could attempt egress. We do not expect such behavior from generated code, but you can enforce offline execution via VM or host firewall if required.
* Some shells ignore `ulimit -m` on modern kernels; prefer RLIMITs via `prlimit` or Python `resource` on Linux.

---

## 10) Reporting security issues

Open a minimal, non‑sensitive issue in the repository describing the observed behavior (no PII, no secrets). We will follow up with remediation steps in a patched release after the review period.
