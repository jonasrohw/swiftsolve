
Profiler Agent --- Full Technical Implementation Plan (v1.0.0)
============================================================

> **Purpose**  Convert a `CodeMessage` (C++ 17 source) into a `ProfileReport` that contains precise runtime and memory telemetry across logarithmically‑spaced input scales, executed inside an isolated Docker sandbox with strict resource limits.
>
> **Reader**  Senior Python/C++ developer; after reading, you can implement the agent end‑to‑end with zero follow‑up questions.

* * * * *

1  High‑Level Responsibilities
------------------------------

1.  **Prepare input cases** based on plan‑derived `input_bounds` (log‑scale + corner cases).

2.  **Compile** the C++ code with deterministic flags.

3.  **Execute** the binary under `/usr/bin/time -v` in a Docker container with cgroup & `resource.setrlimit` caps.

4.  **Parse** the time & memory output into numeric lists aligned with `input_sizes`.

5.  **Collect** (optional) hotspot information via `gprof` when `debug=true`.

6.  **Emit** a strict `ProfileReport` Pydantic model.

* * * * *

2  Public API
-------------

```
class Profiler(Agent):
    """Empirical runtime/memory measurement for a single CodeMessage."""

    def run(self, code: CodeMessage, *, debug: bool = False) -> ProfileReport:
        """Compile & execute, returning ProfileReport.

        Raises:
            SandboxError: on compilation or runtime error that persists after 1 retry.
        """
```

### 2.1  Configurable Constants *(utils.config)*

| Name | Default | Description |
| `sandbox_timeout_sec` |  `2` | Hard wall clock per run (seconds) |
| `sandbox_mem_mb` |  `512` | Resident‑set limit |
| `input_scales` | `[1e3,5e3,1e4,5e4,1e5]` | Logarithmic sizes |
| `extra_corner_cases` | `[0,1]` | Added at beginning of list |

* * * * *

3  Internal Architecture
------------------------

```
Profiler.run()
 ├─ _prepare_inputs()   # deterministic input strings
 ├─ _compile_cpp()      # g++ -O2 -std=c++17
 │    └─ returns path to binary
 ├─ for each n in input_sizes:
 │      └─ _execute_binary()   # wraps docker + /usr/bin/time -v
 │            ├─ stdout
 │            └─ _parse_time_output()
 ├─ if debug:
 │      └─ _collect_gprof()
 └─ Build ProfileReport → return
```

### 3.1  Module Break‑Down

| Module/Func | Purpose | I/O & Exceptions |
| `**_prepare_inputs**` | Generate deterministic worst‑case inputs. | → `List[str]` same length as `input_sizes` |
| `**_compile_cpp**` | Compile source to `main.out`; retry once on failure. | → `Path` to binary; raises `CompilationError` |
| `**_execute_binary**` | Run binary inside isolated container with `/usr/bin/time -v`. | → `(stdout:str, time_out:str)`; raises `RuntimeError` |
| `**_parse_time_output**` | Regex‑extract `Elapsed \(wall clock\)`, `Maximum resident set size`. | → `(runtime_ms:float, peak_mem_mb:float)` |
| `**_collect_gprof**` | Run `gprof -l binary` → map line numbers to cumulative time %. | → `Dict[str,str]` hotspots |

* * * * *

4  Docker Sandbox Details
-------------------------

### 4.1  Base Image

```
FROM ubuntu:20.04
RUN apt-get update && apt-get install -y build-essential gprof time
RUN useradd -m sandbox
USER sandbox
WORKDIR /sandbox
```

Image tag: `ghcr.io/swiftsolve/sandbox:20.04-gcc10`

### 4.2  Entrypoint Script `sandbox_entry.sh`

```
#!/usr/bin/env bash
ulimit -v $(( ${SANDBOX_MEM_MB} * 1024 ))   # RLIMIT_AS
ulimit -s 262144                             # 256 MB stack
exec /usr/bin/time -v "$@"
```

Mount path `/code` for source + binary.

### 4.3  Resource Enforcement

-   Container memory limit = `${SANDBOX_MEM_MB}m`.

-   `--pids-limit 64` to avoid fork bombs.

-   No network (`--network none`).

* * * * *

5  Input Generation Strategy
----------------------------

For an integer bound `n_max` extracted from `PlanMessage.input_bounds`:

```
sizes_log = [int(x) for x in [1e3, 5e3, 1e4, 5e4, 1e5] if x <= n_max]
input_sizes = [0,1] + sizes_log
```

### 5.1  Generic Generator *(placeholder)*

If task type unknown, feed `{n}\n` where task likely reads `n` and exits. **TODO**: once `datasets/task_format.py` matured, switch to task‑specific input constructors provided by dataset metadata.

* * * * *

6  Telemetry Parsing
--------------------

Regex patterns:

```
_RX_WALL  = re.compile(r"Elapsed \(wall clock\) time.*?:\s*(\d+:\d+\.\d+)")
_RX_RSS   = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")
```

Conversion:

```
mins,secs = wall.split(':'); runtime_ms = (int(mins)*60+float(secs))*1000
peak_mb = int(rss_kb)//1024
```

Edge cases: if regex missing → raise `ParseError` and mark run as failure.

* * * * *

7  Failure Handling & Retries
-----------------------------

| Stage | Retry Count | On Failure Action |
| Compilation | 1 | Re‑run `_compile_cpp`; if still fails → raise `SandboxError(code="compile")` |
| Execution | 0 (deterministic) | Capture stderr; if non‑zero exit or timeout → mark runtime ∞, memory ∞, continue loop; set hotspot `{"_crash":"SIGSEGV"}` |
| Parsing | 0 | Raise `ParseError` → controller counts as agent failure |

* * * * *

8  ProfileReport Construction
-----------------------------

```
report = ProfileReport(
    task_id=code.task_id,
    iteration=code.iteration,
    input_sizes=input_sizes,
    runtime_ms=runtimes,
    peak_memory_mb=memories,
    hotspots=hotspots,
)
```

Validation: `len(runtime_ms) == len(input_sizes) == len(peak_memory_mb)`.

* * * * *

9  Logging
----------

-   `Profiler` logger name: `Profiler`.

-   INFO: compile command, each input size runtime/mem.

-   WARNING: compile/runtime failures.

-   DEBUG (if `LOG_LEVEL=DEBUG`): full `/usr/bin/time -v` dump.

* * * * *

10  Unit & Integration Tests
----------------------------

| Test ID | Description | Tooling |
| P‑1 | Successful compile & run on "hello world". | Pytest, stub |
| P‑2 | Time/mem regex parsing gives correct floats. | Regex unit |
| P‑3 | Exceed memory limit triggers SandboxError. | Docker mem=64m |
| P‑4 | Crash binary produces ∞ runtimes and warning. | Faulty code |
| P‑5 | `debug=True` attaches hotspot dict keys. | gprof mock |

Coverage ≥ 90 % for `agents/profiler.py`.

* * * * *

11  Acceptance Criteria
-----------------------

1.  Given a syntactically correct `CodeMessage`, `Profiler.run()` returns a **valid** `ProfileReport` within `2 × len(input_sizes)` seconds total wall time.

2.  Report numbers differ < 5 % across two consecutive runs on same host (determinism).

3.  Memory is within ± 2 MB of `/usr/bin/time` manual run.

* * * * *

> **End of Profiler Agent Technical Plan**
