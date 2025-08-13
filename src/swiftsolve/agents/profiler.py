# agents/profiler.py
import re
import subprocess
import tempfile
import pathlib
import json
import platform
import shutil
from typing import List, Tuple, Dict
from .base import Agent
from ..schemas import CodeMessage, ProfileReport
from ..utils.config import get_settings
from ..utils.logger import get_logger

# Regex patterns for parsing /usr/bin/time -v output
_RX_WALL = re.compile(r"Elapsed \(wall clock\) time.*?:\s*(\d+):(\d+\.\d+)")
_RX_RSS = re.compile(r"Maximum resident set size \(kbytes\):\s*(\d+)")

class SandboxError(Exception):
    """Raised when sandbox compilation or execution fails."""
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)

class ParseError(Exception):
    """Raised when time output parsing fails."""
    pass

class Profiler(Agent):
    """Empirical runtime/memory measurement for a single CodeMessage."""
    
    def __init__(self):
        super().__init__("Profiler")
        self.settings = get_settings()
        self.time_cmd = self._detect_time_command()
        
    def _detect_time_command(self) -> str:
        """Detect the correct time command for the current platform."""
        if platform.system() == "Darwin":  # macOS
            # Try GNU time first (installed via brew)
            for cmd in ["/usr/local/bin/gtime", "/opt/homebrew/bin/gtime", "gtime"]:
                if shutil.which(cmd):
                    # Test if it supports -v flag
                    try:
                        result = subprocess.run([cmd, "-v", "echo", "test"], 
                                              capture_output=True, text=True, timeout=5)
                        if "Maximum resident set size" in result.stderr:
                            self.log.info(f"Using GNU time: {cmd}")
                            return cmd
                    except:
                        continue
            
            # Fallback: warn user and use basic time
            self.log.warning("GNU time not found on macOS. Install with: brew install gnu-time")
            return "/usr/bin/time"  # Won't work properly but will fail gracefully
        else:
            # Linux/Unix - use standard time
            return "/usr/bin/time"
        
    def run(self, code: CodeMessage, *, debug: bool = False) -> ProfileReport:
        """Compile & execute, returning ProfileReport.
        
        Raises:
            SandboxError: on compilation or runtime error that persists after 1 retry.
        """
        self.log.info(f"Profiler starting with code: {code.model_dump_json(indent=2)}")
        self.log.info(f"Debug mode: {debug}")
        self.log.info(f"Time command: {self.time_cmd}")
        
        # Prepare input cases
        input_sizes, input_data_list = self._prepare_inputs(code)
        self.log.info(f"Input sizes: {input_sizes}")
        
        # Compile the C++ code
        binary_path = self._compile_cpp(code.code_cpp)
        self.log.info(f"Compilation successful, binary at: {binary_path}")
        
        runtimes = []
        memories = []
        hotspots = {}
        
        # Execute for each input size
        for i, (n, input_data) in enumerate(zip(input_sizes, input_data_list)):
            self.log.info(f"Profiling input size {n} ({i+1}/{len(input_sizes)})")
            self.log.debug(f"Input data: {repr(input_data)}")
            
            try:
                stdout, time_output = self._execute_binary(binary_path, input_data)
                runtime_ms, peak_mem_mb = self._parse_time_output(time_output)
                
                self.log.info(f"  Runtime: {runtime_ms:.2f}ms, Memory: {peak_mem_mb:.2f}MB")
                runtimes.append(runtime_ms)
                memories.append(peak_mem_mb)
                
            except Exception as e:
                self.log.warning(f"Execution failed for input size {n}: {e}")
                # Mark as infinite runtime/memory and continue
                runtimes.append(float('inf'))
                memories.append(float('inf'))
                hotspots["_crash"] = str(e)
        
        # Collect hotspot information if debug mode
        if debug:
            try:
                hotspots.update(self._collect_gprof(binary_path, input_data_list[0]))
                self.log.info("Hotspot collection completed")
            except Exception as e:
                self.log.warning(f"Hotspot collection failed: {e}")
        
        # Build and return ProfileReport
        profile = ProfileReport(
            task_id=code.task_id,
                             iteration=code.iteration,
            input_sizes=input_sizes,
                             runtime_ms=runtimes,
                             peak_memory_mb=memories,
            hotspots=hotspots
        )
        
        self.log.info(f"Profiler completed. Profile report: {profile.model_dump_json(indent=2)}")
        return profile
    
    def _prepare_inputs(self, code: CodeMessage) -> Tuple[List[int], List[str]]:
        """Generate deterministic worst-case inputs."""
        # Get n_max from code bounds or use default
        n_max = 100000  # Default max size
        
        # Generate logarithmic scales within bounds
        scales = [1000, 5000, 10000, 50000, 100000]
        sizes_log = [int(x) for x in scales if x <= n_max]
        
        # Add corner cases
        input_sizes = [0, 1] + sizes_log
        
        # Generate corresponding input data
        input_data_list = []
        for n in input_sizes:
            input_data = self._generate_input_for_size(n)
            input_data_list.append(input_data)
        
        return input_sizes, input_data_list
    
    def _generate_input_for_size(self, n: int) -> str:
        """Generate input string for given size n."""
        # Generic generator - just feed n and assume program reads it
        # TODO: Use task-specific generators when datasets/ is implemented
        return f"{n}\n"
    
    def _compile_cpp(self, code: str) -> pathlib.Path:
        """Compile source to binary; retry once on failure."""
        compile_flags = ["-O2", "-std=c++17", "-march=native", "-ffast-math"]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = pathlib.Path(tmp_dir)
            src_path = tmp_path / "main.cpp"
            bin_path = tmp_path / "main.out"
            
            # Write source code
            src_path.write_text(code, encoding="utf-8")
            
            # Try compilation
            for attempt in range(2):  # Retry once
                compile_cmd = ["g++"] + compile_flags + [str(src_path), "-o", str(bin_path)]
                self.log.info(f"Compilation attempt {attempt + 1}: {' '.join(compile_cmd)}")
                
                try:
                    result = subprocess.run(
                        compile_cmd, 
                        capture_output=True, 
                        text=True, 
                        check=True,
                        timeout=30
                    )
                    
                    # Copy binary to a persistent location
                    persistent_dir = pathlib.Path("/tmp") / "swiftsolve_binaries"
                    persistent_dir.mkdir(exist_ok=True)
                    persistent_bin = persistent_dir / f"main_{id(code)}.out"
                    
                    # Copy the binary
                    import shutil
                    shutil.copy2(bin_path, persistent_bin)
                    persistent_bin.chmod(0o755)
                    
                    self.log.info(f"Compilation successful, binary copied to: {persistent_bin}")
                    return persistent_bin
                    
                except subprocess.CalledProcessError as e:
                    error_msg = f"Compilation failed (attempt {attempt + 1}): {e.stderr}"
                    self.log.warning(error_msg)
                    if attempt == 1:  # Last attempt
                        raise SandboxError("compile", error_msg)
                except subprocess.TimeoutExpired:
                    error_msg = f"Compilation timeout (attempt {attempt + 1})"
                    self.log.warning(error_msg)
                    if attempt == 1:
                        raise SandboxError("compile", error_msg)
    
    def _execute_binary(self, binary_path: pathlib.Path, input_data: str) -> Tuple[str, str]:
        """Run binary with /usr/bin/time -v to capture telemetry."""
        timeout = self.settings.sandbox_timeout_sec
        
        # Use detected time command to capture detailed timing information
        time_cmd = [self.time_cmd, "-v", str(binary_path)]
        
        self.log.debug(f"Executing: {' '.join(time_cmd)}")
        self.log.debug(f"Input: {repr(input_data)}")
        
        try:
            # Run with timeout and capture both stdout and stderr
            result = subprocess.run(
                time_cmd,
                input=input_data,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            stdout = result.stdout
            stderr = result.stderr  # This contains the /usr/bin/time output
            
            self.log.debug(f"Return code: {result.returncode}")
            self.log.debug(f"stdout: {repr(stdout)}")
            self.log.debug(f"stderr (time output): {repr(stderr)}")
            
            if result.returncode != 0:
                raise RuntimeError(f"Binary exited with code {result.returncode}: {stderr}")
            
            return stdout, stderr
            
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Execution timed out after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Execution failed: {e}")
    
    def _parse_time_output(self, time_output: str) -> Tuple[float, float]:
        """Parse /usr/bin/time -v output to extract runtime and memory."""
        self.log.debug(f"Parsing time output: {repr(time_output)}")
        
        # Parse wall clock time
        wall_match = _RX_WALL.search(time_output)
        if not wall_match:
            # Fallback for macOS built-in time command
            if "real" in time_output:
                # Try to parse macOS time format: "real 0m0.001s"
                real_match = re.search(r"real\s+(\d+)m(\d+\.\d+)s", time_output)
                if real_match:
                    mins, secs = real_match.groups()
                    runtime_ms = (int(mins) * 60 + float(secs)) * 1000
                else:
                    raise ParseError(f"Could not parse macOS time format from: {time_output}")
            else:
                raise ParseError(f"Could not parse wall clock time from: {time_output}")
        else:
            mins, secs = wall_match.groups()
            runtime_ms = (int(mins) * 60 + float(secs)) * 1000
        
        # Parse RSS memory
        rss_match = _RX_RSS.search(time_output)
        if not rss_match:
            # Fallback: estimate memory usage (not accurate but prevents crashes)
            self.log.warning("Could not parse memory usage, using fallback estimate")
            peak_mb = 1.0  # Minimum fallback
        else:
            rss_kb = int(rss_match.group(1))
            peak_mb = rss_kb / 1024.0
        
        self.log.debug(f"Parsed: {runtime_ms:.2f}ms, {peak_mb:.2f}MB")
        return runtime_ms, peak_mb
    
    def _collect_gprof(self, binary_path: pathlib.Path, input_data: str) -> Dict[str, str]:
        """Run gprof to collect hotspot information."""
        self.log.info("Collecting hotspot information with gprof")
        
        try:
            # First, we need to recompile with -pg flag for profiling
            with tempfile.TemporaryDirectory() as tmp_dir:
                tmp_path = pathlib.Path(tmp_dir)
                
                # Read the original source (we need to recompile with -pg)
                # For now, just return empty hotspots since we don't have the source here
                # TODO: Pass source code or store it for profiling
                self.log.warning("gprof hotspot collection not fully implemented")
                return {"_note": "gprof collection requires source code access"}
                
        except Exception as e:
            self.log.error(f"gprof collection failed: {e}")
            return {"_error": str(e)}