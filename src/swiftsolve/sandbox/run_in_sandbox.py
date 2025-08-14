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
    log.info(f"Starting compilation and execution with timeout: {timeout}s")
    log.info(f"Input data: {repr(input_data)}")
    log.info(f"Code length: {len(code)} characters")

    with tempfile.TemporaryDirectory() as tmp:
        src_path = pathlib.Path(tmp) / "main.cpp"
        bin_path = pathlib.Path(tmp) / "a.out"
        
        log.info(f"Writing code to: {src_path}")
        src_path.write_text(code, encoding="utf-8")
        
        compile_cmd = [shutil.which("g++")] + COMPILE_FLAGS + [str(src_path), "-o", str(bin_path)]
        log.info(f"Compilation command: {' '.join(shlex.quote(c) for c in compile_cmd)}")
        
        try:
            log.info("Starting compilation...")
            compile_result = subprocess.run(compile_cmd, check=True, capture_output=True)
            log.info("Compilation successful")
            
            run_cmd = ["timeout", f"{timeout}", str(bin_path)] if shutil.which("timeout") else [str(bin_path)]
            log.info(f"Execution command: {' '.join(shlex.quote(c) for c in run_cmd)}")
            
            log.info("Starting execution...")
            res = subprocess.run(
                run_cmd, input=input_data.encode(), capture_output=True, timeout=timeout
            )
            
            stdout = str(res.stdout.decode())
            stderr = str(res.stderr.decode())
            
            log.info(f"Execution completed with return code: {res.returncode}")
            log.info(f"stdout: {repr(stdout)}")
            log.info(f"stderr: {repr(stderr)}")
            
            return stdout, stderr
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Compilation failed: {e.stderr.decode() if e.stderr else 'Unknown error'}"
            log.error(error_msg)
            log.error(f"Return code: {e.returncode}")
            if e.stdout:
                log.error(f"stdout: {e.stdout.decode()}")
            if e.stderr:
                log.error(f"stderr: {e.stderr.decode()}")
            return "", error_msg
            
        except subprocess.TimeoutExpired as e:
            error_msg = f"Execution timed out after {timeout}s"
            log.error(error_msg)
            return "", error_msg
            
        except Exception as e:
            error_msg = f"Execution failed: {e}"
            log.error(error_msg)
            log.error(f"Exception type: {type(e).__name__}")
            return "", error_msg

def compile_and_profile(code: str, input_data: str) -> str:
    """
    Generates code with debug and profiling information, don't use this to check runtime.
    Returns a string containing profiling information.
    """
    log.info(f"Starting compilation and profiling")
    log.info(f"Input data: {repr(input_data)}")
    log.info(f"Code length: {len(code)} characters")

    with tempfile.TemporaryDirectory() as tmp:
        src_path = pathlib.Path(tmp) / "main.cpp"
        bin_path = pathlib.Path(tmp) / "a.out"
        
        log.info(f"Writing code to: {src_path}")
        src_path.write_text(code, encoding="utf-8")
        
        compile_cmd = [shutil.which("g++")] + COMPILE_FLAGS + ["-pg", "-g"] + [str(src_path), "-o", str(bin_path)]
        log.info(f"Compilation command: {' '.join(shlex.quote(c) for c in compile_cmd)}")
        
        log.info("Starting compilation...")
        subprocess.run(compile_cmd, check=True)
        log.info("Compilation successful")
        
        run_cmd = [str(bin_path)]
        log.info(f"Execution command: {' '.join(shlex.quote(c) for c in run_cmd)}")
        
        log.info("Starting execution...")
        subprocess.run(run_cmd, input=input_data.encode(), capture_output=True)
        log.info("Execution completed")
        
        prof_cmd = [shutil.which("gprof"), "-l", bin_path]
        log.info(f"Profiling command: {' '.join(shlex.quote(c) for c in prof_cmd)}")
        
        log.info("Starting profiling...")
        proc = subprocess.run(prof_cmd, capture_output=True)
        log.info("Profiling completed")
        
        (pathlib.Path.cwd() / "gmon.out").unlink(True)
        profile_output = str(proc.stdout.decode())
        
        log.info(f"Profile output length: {len(profile_output)} characters")
        return profile_output