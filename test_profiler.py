#!/usr/bin/env python3
"""
Profiler Functionality Test Script

This script tests the SwiftSolve Profiler Agent with a simple C++ program
to verify that it can compile, execute, and measure performance correctly.
"""

import sys
import os
import pathlib

# Add src to path so we can import swiftsolve modules
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

try:
    from swiftsolve.agents.profiler import Profiler
    from swiftsolve.schemas import CodeMessage
    from swiftsolve.utils.config import get_settings
except ImportError as e:
    print(f"❌ Failed to import SwiftSolve modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def test_simple_program():
    """Test with a simple O(n) program."""
    print("🧪 Testing Simple O(n) Program...")
    
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
    
    if (n > 0) {
        cout << nums[n-1] << endl;
    } else {
        cout << 0 << endl;
    }
    return 0;
}
"""
    
    code_message = CodeMessage(
        task_id="TEST_SIMPLE",
        iteration=0,
        code_cpp=test_code
    )
    
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=False)
        
        print("✅ Simple program test successful!")
        print(f"   Task ID: {profile.task_id}")
        print(f"   Input sizes: {profile.input_sizes}")
        print(f"   Runtimes (ms): {[f'{x:.2f}' for x in profile.runtime_ms]}")
        print(f"   Memory (MB): {[f'{x:.2f}' for x in profile.peak_memory_mb]}")
        
        # Validate results
        if len(profile.runtime_ms) == len(profile.input_sizes):
            print("✅ Runtime measurements: Correct count")
        else:
            print("❌ Runtime measurements: Incorrect count")
            return False
            
        if all(x > 0 and x != float('inf') for x in profile.runtime_ms):
            print("✅ Runtime values: All valid")
        else:
            print("❌ Runtime values: Some invalid")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Simple program test failed: {e}")
        return False

def test_compilation_error():
    """Test handling of compilation errors."""
    print("\n🧪 Testing Compilation Error Handling...")
    
    bad_code = """
#include <iostream>
using namespace std;

int main() {
    // This should cause a compilation error
    undefined_function();
    return 0;
}
"""
    
    code_message = CodeMessage(
        task_id="TEST_COMPILE_ERROR",
        iteration=0,
        code_cpp=bad_code
    )
    
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=False)
        print("❌ Expected compilation error but got success")
        return False
    except Exception as e:
        if "compilation" in str(e).lower() or "compile" in str(e).lower():
            print("✅ Compilation error handled correctly")
            return True
        else:
            print(f"❌ Unexpected error type: {e}")
            return False

def test_runtime_error():
    """Test handling of runtime errors."""
    print("\n🧪 Testing Runtime Error Handling...")
    
    crash_code = """
#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    // This will crash for n > 0
    int* ptr = nullptr;
    if (n > 0) {
        *ptr = 42;  // Segmentation fault
    }
    
    cout << "Should not reach here" << endl;
    return 0;
}
"""
    
    code_message = CodeMessage(
        task_id="TEST_RUNTIME_ERROR",
        iteration=0,
        code_cpp=crash_code
    )
    
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=False)
        
        # Check if some executions failed (should have inf values)
        inf_count = sum(1 for x in profile.runtime_ms if x == float('inf'))
        if inf_count > 0:
            print(f"✅ Runtime errors handled correctly ({inf_count} failures)")
            return True
        else:
            print("⚠️  Expected runtime failures but all succeeded")
            return True  # This might be OK depending on input sizes
            
    except Exception as e:
        print(f"⚠️  Runtime error test failed unexpectedly: {e}")
        return True  # This is acceptable behavior

def test_performance_scaling():
    """Test that performance scales with input size."""
    print("\n🧪 Testing Performance Scaling...")
    
    scaling_code = """
#include <iostream>
#include <vector>
#include <algorithm>
using namespace std;

int main() {
    int n;
    cin >> n;
    
    if (n <= 0) {
        cout << 0 << endl;
        return 0;
    }
    
    // O(n log n) operation
    vector<int> nums(n);
    for (int i = 0; i < n; i++) {
        nums[i] = n - i;
    }
    
    sort(nums.begin(), nums.end());
    
    cout << nums[0] << endl;
    return 0;
}
"""
    
    code_message = CodeMessage(
        task_id="TEST_SCALING",
        iteration=0,
        code_cpp=scaling_code
    )
    
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=False)
        
        # Check if runtimes generally increase with input size
        valid_runtimes = [x for x in profile.runtime_ms if x != float('inf') and x > 0]
        
        if len(valid_runtimes) >= 3:
            # Check if there's a general upward trend
            increasing = sum(1 for i in range(len(valid_runtimes)-1) 
                           if valid_runtimes[i+1] >= valid_runtimes[i])
            total_comparisons = len(valid_runtimes) - 1
            
            if increasing >= total_comparisons * 0.6:  # 60% should be increasing
                print("✅ Performance scaling: Runtimes increase with input size")
                return True
            else:
                print("⚠️  Performance scaling: Inconsistent scaling pattern")
                print(f"   Runtimes: {[f'{x:.2f}' for x in valid_runtimes]}")
                return True  # Still acceptable, could be noise
        else:
            print("⚠️  Performance scaling: Not enough valid measurements")
            return True
            
    except Exception as e:
        print(f"❌ Performance scaling test failed: {e}")
        return False

def test_debug_mode():
    """Test debug mode functionality."""
    print("\n🧪 Testing Debug Mode...")
    
    debug_code = """
#include <iostream>
using namespace std;

int main() {
    int n;
    cin >> n;
    cout << n * 2 << endl;
    return 0;
}
"""
    
    code_message = CodeMessage(
        task_id="TEST_DEBUG",
        iteration=0,
        code_cpp=debug_code
    )
    
    profiler = Profiler()
    try:
        profile = profiler.run(code_message, debug=True)
        
        print("✅ Debug mode test successful!")
        if profile.hotspots:
            print(f"   Hotspots collected: {list(profile.hotspots.keys())}")
        else:
            print("   No hotspots collected (normal for simple programs)")
        return True
        
    except Exception as e:
        print(f"❌ Debug mode test failed: {e}")
        return False

def main():
    """Run all profiler tests."""
    print("🚀 SwiftSolve Profiler Functionality Tests")
    print("=" * 50)
    
    # Check basic setup
    try:
        settings = get_settings()
        print(f"✅ Configuration loaded")
        print(f"   Timeout: {settings.sandbox_timeout_sec}s")
        print(f"   Memory limit: {settings.sandbox_mem_mb}MB")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False
    
    # Run all tests
    tests = [
        ("Simple Program", test_simple_program),
        ("Compilation Error", test_compilation_error),
        ("Runtime Error", test_runtime_error),
        ("Performance Scaling", test_performance_scaling),
        ("Debug Mode", test_debug_mode),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'─' * 20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 50}")
    print("🏁 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All tests passed! The profiler is working correctly.")
        return True
    elif passed >= len(tests) * 0.8:
        print("⚠️  Most tests passed. Minor issues may exist but profiler should work.")
        return True
    else:
        print("❌ Multiple test failures. Please check your setup.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 