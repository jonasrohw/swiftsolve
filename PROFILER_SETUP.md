# Profiler Agent Setup Instructions

## Overview

The Profiler Agent is now fully implemented according to the technical specification. It provides empirical runtime and memory measurement for C++ code by compiling and executing it with `/usr/bin/time -v` to capture precise telemetry.

## Prerequisites

### System Requirements

1. **Linux/macOS system** (required for `/usr/bin/time -v`)
2. **Python 3.11+**
3. **GCC compiler** (`g++`)
4. **GNU time utility** (`/usr/bin/time`)

### Install System Dependencies

#### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y build-essential time
```

#### macOS:
```bash
# Install Xcode command line tools
xcode-select --install

# Install GNU time (macOS has a different time command)
brew install gnu-time
# Note: On macOS, use `/usr/local/bin/gtime` instead of `/usr/bin/time`
```

#### CentOS/RHEL:
```bash
sudo yum groupinstall "Development Tools"
sudo yum install time
```

## Environment Setup

### 1. Clone and Setup Project

```bash
cd /path/to/swiftsolve
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Required API keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional profiler settings (defaults shown)
SANDBOX_TIMEOUT_SEC=5
SANDBOX_MEM_MB=512
LOG_LEVEL=INFO
```

### 3. Verify System Dependencies

Run this verification script:

```python
# test_profiler_setup.py
import subprocess
import shutil
import pathlib

def check_dependency(cmd, name):
    """Check if a command exists and is executable."""
    try:
        path = shutil.which(cmd) or cmd
        result = subprocess.run([path, '--version'], 
                              capture_output=True, text=True, timeout=5)
        print(f"✅ {name}: {path}")
        return True
    except Exception as e:
        print(f"❌ {name}: Not found or not working - {e}")
        return False

def main():
    print("🔍 Checking Profiler Dependencies...\n")
    
    deps = [
        ("g++", "GCC Compiler"),
        ("/usr/bin/time", "GNU Time Utility"),
        ("python3", "Python 3"),
    ]
    
    all_good = True
    for cmd, name in deps:
        if not check_dependency(cmd, name):
            all_good = False
    
    # Special check for time -v
    try:
        result = subprocess.run(["/usr/bin/time", "-v", "echo", "test"], 
                              capture_output=True, text=True, timeout=5)
        if "Maximum resident set size" in result.stderr:
            print("✅ GNU Time -v output: Working correctly")
        else:
            print("❌ GNU Time -v output: Not producing expected format")
            all_good = False
    except Exception as e:
        print(f"❌ GNU Time -v test: Failed - {e}")
        all_good = False
    
    # Check temp directory permissions
    try:
        test_dir = pathlib.Path("/tmp/swiftsolve_test")
        test_dir.mkdir(exist_ok=True)
        test_file = test_dir / "test.txt"
        test_file.write_text("test")
        test_file.unlink()
        test_dir.rmdir()
        print("✅ Temp directory access: Working")
    except Exception as e:
        print(f"❌ Temp directory access: Failed - {e}")
        all_good = False
    
    print(f"\n{'🎉 All dependencies ready!' if all_good else '❌ Some dependencies need attention'}")
    return all_good

if __name__ == "__main__":
    main()
```

Run it:
```bash
python test_profiler_setup.py
```

## Testing the Profiler

### Basic Test

Create a test script to verify the profiler works:

```python
# test_profiler.py
import sys
sys.path.append('src')

from swiftsolve.agents.profiler import Profiler
from swiftsolve.schemas import CodeMessage

def test_profiler():
    # Simple C++ code that should compile and run
    test_code = """
#include <iostream>
#include <vector>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    // Simple O(n) operation
    vector<int> nums(n);
    for (int i = 0; i < n; i++) {
        nums[i] = i * i;
    }
    
    cout << nums[n-1] << endl;
    return 0;
}
"""
    
    # Create a CodeMessage
    code_message = CodeMessage(
        task_id="TEST_PROFILER",
        iteration=0,
        code_cpp=test_code
    )
    
    # Run profiler
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=False)
        print("✅ Profiler test successful!")
        print(f"Input sizes: {profile.input_sizes}")
        print(f"Runtimes: {profile.runtime_ms}")
        print(f"Memory usage: {profile.peak_memory_mb}")
        return True
    except Exception as e:
        print(f"❌ Profiler test failed: {e}")
        return False

if __name__ == "__main__":
    test_profiler()
```

Run the test:
```bash
cd /path/to/swiftsolve
python test_profiler.py
```

## Troubleshooting

### Common Issues

1. **"Command not found: /usr/bin/time"**
   - On macOS: Install `gnu-time` via Homebrew and use `/usr/local/bin/gtime`
   - On Linux: Install the `time` package

2. **"Permission denied" errors**
   - Ensure `/tmp` directory is writable
   - Check that compiled binaries have execute permissions

3. **"Compilation failed" errors**
   - Verify GCC is installed and working: `g++ --version`
   - Check that C++17 is supported: `g++ -std=c++17 --version`

4. **"Parse error" from time output**
   - Verify GNU time format: `/usr/bin/time -v echo test`
   - Output should include "Maximum resident set size (kbytes)"

5. **Memory errors during execution**
   - Increase `SANDBOX_MEM_MB` in your `.env` file
   - Default is 512MB, try 1024MB for larger programs

### macOS Specific Setup

If you're on macOS, you need to modify the profiler to use GNU time:

```python
# Add this to your .env file or modify the profiler code
# For macOS, use gtime instead of /usr/bin/time
```

Or install GNU coreutils:
```bash
brew install coreutils
# Then use /usr/local/bin/gtime -v instead of /usr/bin/time -v
```

## Directory Structure

After setup, your profiler will use these directories:

```
/tmp/swiftsolve_binaries/     # Compiled binaries (auto-created)
logs/                         # Profiler logs (if configured)
```

## Configuration Options

You can configure the profiler behavior via environment variables:

```bash
# Timeout for each execution (seconds)
SANDBOX_TIMEOUT_SEC=10

# Memory limit for execution (MB)
SANDBOX_MEM_MB=1024

# Log level for debugging
LOG_LEVEL=DEBUG
```

## Performance Expectations

- **Compilation time**: 1-3 seconds per C++ file
- **Execution time per input size**: 0.1-5 seconds (depends on code complexity)
- **Total profiling time**: 10-30 seconds for 7 input sizes
- **Memory usage**: Varies by program, typically 1-100MB

## Next Steps

1. ✅ **Verify setup** with the test scripts above
2. ✅ **Run a simple test** to confirm profiler works
3. ✅ **Check logs** for any warnings or errors
4. ✅ **Test with your actual code** by running the full pipeline

## Getting Help

If you encounter issues:

1. **Check logs** - Set `LOG_LEVEL=DEBUG` for detailed output
2. **Verify dependencies** - Run the dependency check script
3. **Test manually** - Try compiling and running code manually with `/usr/bin/time -v`
4. **Check permissions** - Ensure write access to `/tmp`

The profiler is now ready to provide precise runtime and memory measurements for your C++ code! 