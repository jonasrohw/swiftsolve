# sandbox/run_in_sandbox.py
import shutil, subprocess, tempfile, os, json, pathlib, shlex
from ..utils.logger import get_logger

log = get_logger("Sandbox")

#TODO: Increase stack size, to something ~256 MB

# Last 2 flags help the compiler to perform auto-vectorization
COMPILE_FLAGS = ["-O3", "-std=c++17", "-march=native", "-ffast-math"]

def compile_and_run(code: str, input_data: str, timeout: int) -> tuple[str]:
    """
    Generates optimized code, good for checking total runtime.
    """

    with tempfile.TemporaryDirectory() as tmp:
        src_path = pathlib.Path(tmp) / "main.cpp"
        bin_path = pathlib.Path(tmp) / "a.out"
        src_path.write_text(code, encoding="utf-8")
        compile_cmd = [shutil.which("g++")] + COMPILE_FLAGS + [str(src_path), "-o", str(bin_path)]
        log.info(" ".join(shlex.quote(c) for c in compile_cmd))
        
        try:
            subprocess.run(compile_cmd, check=True, capture_output=True)
            run_cmd = ["timeout", f"{timeout}", str(bin_path)] if shutil.which("timeout") else [str(bin_path)]
            res = subprocess.run(
                run_cmd, input=input_data.encode(), capture_output=True, timeout=timeout
            )
            return str(res.stdout.decode()), str(res.stderr.decode())
        except subprocess.CalledProcessError as e:
            log.error(f"Compilation failed: {e.stderr.decode() if e.stderr else 'Unknown error'}")
            return "", f"Compilation failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
        except Exception as e:
            log.error(f"Execution failed: {e}")
            return "", f"Execution failed: {e}"

def compile_and_profile(code: str, input_data: str) -> str:
    """
    Generates code with debug and profiling information, don't use this to check runtime.
    Returns a string containing profiling information.
    """

    with tempfile.TemporaryDirectory() as tmp:
        src_path = pathlib.Path(tmp) / "main.cpp"
        bin_path = pathlib.Path(tmp) / "a.out"
        src_path.write_text(code, encoding="utf-8")
        compile_cmd = [shutil.which("g++")] + COMPILE_FLAGS + ["-pg", "-g"] + [str(src_path), "-o", str(bin_path)]
        log.info(" ".join(shlex.quote(c) for c in compile_cmd))
        subprocess.run(compile_cmd, check=True)
        run_cmd = [str(bin_path)]
        subprocess.run(run_cmd, input=input_data.encode(), capture_output=True)
        prof_cmd = [shutil.which("gprof"), "-l", bin_path]
        proc = subprocess.run(prof_cmd, capture_output=True)
        (pathlib.Path.cwd() / "gmon.out").unlink(True)
        return str(proc.stdout.decode())