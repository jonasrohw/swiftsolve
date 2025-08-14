#!/usr/bin/env python3
"""
Profiler Setup Verification Script

This script checks all dependencies required for the SwiftSolve Profiler Agent.
Run this before using the profiler to ensure everything is properly configured.
"""

import subprocess
import shutil
import pathlib
import sys
import os

def check_dependency(cmd, name, version_flag="--version"):
    """Check if a command exists and is executable."""
    try:
        path = shutil.which(cmd) or cmd
        result = subprocess.run([path, version_flag], 
                              capture_output=True, text=True, timeout=5)
        print(f"✅ {name}: {path}")
        if result.stdout:
            print(f"   Version: {result.stdout.split()[0] if result.stdout.split() else 'Unknown'}")
        return True
    except Exception as e:
        print(f"❌ {name}: Not found or not working - {e}")
        return False

def check_time_utility():
    """Special check for GNU time utility with -v flag."""
    print("\n🔍 Testing GNU Time Utility...")
    
    time_commands = ["/usr/bin/time", "gtime", "time"]
    
    for cmd in time_commands:
        try:
            result = subprocess.run([cmd, "-v", "echo", "test"], 
                                  capture_output=True, text=True, timeout=5)
            if "Maximum resident set size" in result.stderr:
                print(f"✅ GNU Time -v: {cmd} (working correctly)")
                print(f"   Output format: Valid")
                return cmd
            else:
                print(f"⚠️  {cmd}: Found but wrong format")
        except Exception as e:
            print(f"❌ {cmd}: {e}")
    
    return None

def check_cpp_compilation():
    """Test C++ compilation with required flags."""
    print("\n🔍 Testing C++ Compilation...")
    
    test_code = """
#include <iostream>
#include <vector>
using namespace std;

int main() {
    cout << "Hello from C++17!" << endl;
    return 0;
}
"""
    
    try:
        with pathlib.Path("/tmp/test_cpp_compile.cpp").open("w") as f:
            f.write(test_code)
        
        compile_cmd = ["g++", "-O2", "-std=c++17", "-march=native", 
                       "/tmp/test_cpp_compile.cpp", "-o", "/tmp/test_cpp_compile"]
        
        result = subprocess.run(compile_cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ C++ Compilation: Success")
            
            # Test execution
            exec_result = subprocess.run(["/tmp/test_cpp_compile"], 
                                       capture_output=True, text=True, timeout=5)
            if exec_result.returncode == 0:
                print("✅ C++ Execution: Success")
                return True
            else:
                print(f"❌ C++ Execution: Failed - {exec_result.stderr}")
        else:
            print(f"❌ C++ Compilation: Failed - {result.stderr}")
        
    except Exception as e:
        print(f"❌ C++ Test: {e}")
    finally:
        # Cleanup
        for path in ["/tmp/test_cpp_compile.cpp", "/tmp/test_cpp_compile"]:
            try:
                pathlib.Path(path).unlink(missing_ok=True)
            except:
                pass
    
    return False

def check_python_imports():
    """Check if required Python packages are available."""
    print("\n🔍 Testing Python Dependencies...")
    
    required_packages = [
        "pydantic",
        "pydantic_settings", 
        "pathlib",
        "subprocess",
        "tempfile",
        "re"
    ]
    
    all_good = True
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ Python package: {package}")
        except ImportError:
            print(f"❌ Python package: {package} (not found)")
            all_good = False
    
    return all_good

def check_directory_permissions():
    """Check write permissions for required directories."""
    print("\n🔍 Testing Directory Permissions...")
    
    test_dirs = ["/tmp", "/tmp/swiftsolve_binaries"]
    all_good = True
    
    for dir_path in test_dirs:
        try:
            test_dir = pathlib.Path(dir_path)
            test_dir.mkdir(exist_ok=True)
            
            test_file = test_dir / f"test_{os.getpid()}.txt"
            test_file.write_text("test")
            test_file.unlink()
            
            print(f"✅ Directory access: {dir_path}")
        except Exception as e:
            print(f"❌ Directory access: {dir_path} - {e}")
            all_good = False
    
    return all_good

def check_environment():
    """Check environment variables and configuration."""
    print("\n🔍 Testing Environment Configuration...")
    
    # Check for .env file
    env_file = pathlib.Path(".env")
    if env_file.exists():
        print("✅ Environment file: .env found")
    else:
        print("⚠️  Environment file: .env not found (optional)")
    
    # Check key environment variables
    required_vars = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
    optional_vars = ["SANDBOX_TIMEOUT_SEC", "SANDBOX_MEM_MB", "LOG_LEVEL"]
    
    for var in required_vars:
        if os.getenv(var):
            print(f"✅ Environment variable: {var} (set)")
        else:
            print(f"⚠️  Environment variable: {var} (not set - required for full functionality)")
    
    for var in optional_vars:
        if os.getenv(var):
            print(f"✅ Environment variable: {var} = {os.getenv(var)}")
        else:
            print(f"ℹ️  Environment variable: {var} (using default)")
    
    return True

def main():
    """Run all dependency checks."""
    print("🚀 SwiftSolve Profiler Setup Verification")
    print("=" * 50)
    
    all_checks = []
    
    # Check basic system dependencies
    print("\n🔍 Checking System Dependencies...")
    deps = [
        ("python3", "Python 3"),
        ("g++", "GCC Compiler"),
        ("make", "Make Utility"),
    ]
    
    for cmd, name in deps:
        all_checks.append(check_dependency(cmd, name))
    
    # Special checks
    all_checks.append(check_time_utility() is not None)
    all_checks.append(check_cpp_compilation())
    all_checks.append(check_python_imports())
    all_checks.append(check_directory_permissions())
    check_environment()  # This one is informational
    
    # Summary
    print("\n" + "=" * 50)
    success_count = sum(all_checks)
    total_count = len(all_checks)
    
    if success_count == total_count:
        print("🎉 All critical dependencies are ready!")
        print("✅ You can now use the SwiftSolve Profiler Agent.")
        return True
    else:
        print(f"❌ {total_count - success_count} out of {total_count} checks failed.")
        print("🔧 Please fix the issues above before using the profiler.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 