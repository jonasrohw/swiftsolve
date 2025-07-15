# sandbox/run_in_sandbox.py
import subprocess, tempfile, os, json, pathlib, shlex
from utils.config import get_settings
from utils.logger import get_logger

log = get_logger("Sandbox")

def compile_and_run(code: str, input_data: str, timeout: int):
    with tempfile.TemporaryDirectory() as tmp:
        src_path = pathlib.Path(tmp) / "main.cpp"
        bin_path = pathlib.Path(tmp) / "a.out"
        src_path.write_text(code, encoding="utf-8")

        compile_cmd = ["g++", "-O2", "-std=c++17", str(src_path), "-o", str(bin_path)]
        log.info(" ".join(shlex.quote(c) for c in compile_cmd))
        subprocess.run(compile_cmd, check=True, capture_output=True)

        run_cmd = ["timeout", f"{timeout}", str(bin_path)]
        res = subprocess.run(run_cmd, input=input_data.encode(),
                             capture_output=True)
        return res.stdout.decode(), res.stderr.decode()