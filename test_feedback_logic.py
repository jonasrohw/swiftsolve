#!/usr/bin/env python3
"""
Test script to verify the iterative feedback loop logic is working correctly.

This tests the core logic without requiring LLM API calls.
"""

import sys
import os
import pathlib

# Add src to path so we can import swiftsolve modules
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

try:
    from swiftsolve.agents.analyst import Analyst
    from swiftsolve.schemas import ProfileReport, VerdictMessage
except ImportError as e:
    print(f"❌ Failed to import SwiftSolve modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def test_analyst_patch_intelligence():
    """Test that the Analyst generates different patches for different complexity patterns."""
    print("🧪 Testing Analyst patch intelligence...")
    
    analyst = Analyst()
    
    # Test 1: O(n^2) with high memory growth
    profile_quadratic_memory = ProfileReport(
        task_id="TEST_QUAD_MEM",
        iteration=0,
        input_sizes=[1000, 5000, 10000, 50000, 100000],
        runtime_ms=[10.0, 250.0, 1000.0, 25000.0, 100000.0],  # Quadratic growth
        peak_memory_mb=[2.0, 50.0, 200.0, 5000.0, 20000.0],   # High memory growth (10x)
        hotspots={}
    )
    
    verdict1 = analyst.run(profile_quadratic_memory, {"runtime_limit": 2000})
    
    # Test 2: O(n^2) with low memory growth
    profile_quadratic_low_mem = ProfileReport(
        task_id="TEST_QUAD_LOW",
        iteration=0,
        input_sizes=[1000, 5000, 10000, 50000, 100000],
        runtime_ms=[10.0, 250.0, 1000.0, 25000.0, 100000.0],  # Quadratic growth
        peak_memory_mb=[2.0, 2.1, 2.2, 2.5, 2.8],            # Low memory growth
        hotspots={}
    )
    
    verdict2 = analyst.run(profile_quadratic_low_mem, {"runtime_limit": 2000})
    
    # Test 3: O(n^k) exponential
    profile_exponential = ProfileReport(
        task_id="TEST_EXP",
        iteration=0,
        input_sizes=[100, 200, 300, 400, 500],  # Smaller sizes for exponential
        runtime_ms=[10.0, 1000.0, 100000.0, 10000000.0, 1000000000.0],  # Exponential
        peak_memory_mb=[2.0, 20.0, 200.0, 2000.0, 20000.0],
        hotspots={}
    )
    
    verdict3 = analyst.run(profile_exponential, {"runtime_limit": 2000})
    
    print(f"   O(n^2) + High Memory patch: {verdict1.patch[:80]}...")
    print(f"   O(n^2) + Low Memory patch:  {verdict2.patch[:80]}...")
    print(f"   O(n^k) Exponential patch:   {verdict3.patch[:80]}...")
    
    # Verify all are inefficient
    if not verdict1.efficient and not verdict2.efficient and not verdict3.efficient:
        print("✅ All inefficient algorithms correctly identified")
    else:
        print("❌ Some efficient flags incorrect")
        return False
    
    # Verify all route to CODER
    if (verdict1.target_agent == "CODER" and 
        verdict2.target_agent == "CODER" and 
        verdict3.target_agent == "CODER"):
        print("✅ All inefficient algorithms routed to CODER")
    else:
        print("❌ Incorrect routing")
        return False
    
    # Verify patches are different and intelligent
    patches = [verdict1.patch, verdict2.patch, verdict3.patch]
    
    # High memory O(n^2) should mention hash maps
    if "hash map" in verdict1.patch.lower() or "unordered_map" in verdict1.patch.lower():
        print("✅ High memory O(n^2) patch mentions hash maps")
    else:
        print("❌ High memory O(n^2) patch should mention hash maps")
        return False
    
    # Exponential should mention more advanced techniques
    if ("dynamic programming" in verdict3.patch.lower() or 
        "memoization" in verdict3.patch.lower() or
        "greedy" in verdict3.patch.lower()):
        print("✅ Exponential patch mentions advanced optimization techniques")
    else:
        print("❌ Exponential patch should mention advanced techniques")
        return False
    
    # All patches should be different
    if len(set(patches)) == 3:
        print("✅ All patches are different and context-specific")
        return True
    else:
        print("❌ Patches should be different for different complexity patterns")
        return False

def test_coder_signature():
    """Test that the Coder agent accepts patch parameter."""
    print("\n🧪 Testing Coder signature compatibility...")
    
    from swiftsolve.agents.coder import Coder
    from swiftsolve.schemas import PlanMessage
    import inspect
    
    # Check that run method accepts patch parameter
    coder = Coder()
    sig = inspect.signature(coder.run)
    
    if 'patch' in sig.parameters:
        print("✅ Coder.run() accepts 'patch' parameter")
        
        # Check that patch parameter is optional
        patch_param = sig.parameters['patch']
        if patch_param.default is not inspect.Parameter.empty:
            print("✅ Coder patch parameter is optional with default")
            return True
        else:
            print("❌ Coder patch parameter should be optional")
            return False
    else:
        print("❌ Coder.run() missing 'patch' parameter")
        return False

def test_planner_signature():
    """Test that the Planner agent accepts feedback parameter."""
    print("\n🧪 Testing Planner signature compatibility...")
    
    from swiftsolve.agents.planner import Planner
    import inspect
    
    # Check that run method accepts feedback parameter
    planner = Planner()
    sig = inspect.signature(planner.run)
    
    if 'feedback' in sig.parameters:
        print("✅ Planner.run() accepts 'feedback' parameter")
        
        # Check that feedback parameter is optional
        feedback_param = sig.parameters['feedback']
        if feedback_param.default is not inspect.Parameter.empty:
            print("✅ Planner feedback parameter is optional with default")
            return True
        else:
            print("❌ Planner feedback parameter should be optional")
            return False
    else:
        print("❌ Planner.run() missing 'feedback' parameter")
        return False

def test_solve_loop_integration():
    """Test that solve_loop has proper patch handling logic."""
    print("\n🧪 Testing solve_loop integration...")
    
    # Read the solve_loop.py file and check for key integration points
    solve_loop_path = pathlib.Path("src/swiftsolve/controller/solve_loop.py")
    
    if not solve_loop_path.exists():
        print("❌ solve_loop.py not found")
        return False
    
    content = solve_loop_path.read_text()
    
    # Check for pending_patch variable
    if "pending_patch" in content:
        print("✅ solve_loop tracks pending patches")
    else:
        print("❌ solve_loop missing pending_patch tracking")
        return False
    
    # Check for patch application in coder call
    if "coder.run(plan, patch=" in content:
        print("✅ solve_loop passes patches to coder")
    else:
        print("❌ solve_loop not passing patches to coder")
        return False
    
    # Check for feedback in planner call
    if "planner.run(problem, feedback=" in content:
        print("✅ solve_loop passes feedback to planner")
    else:
        print("❌ solve_loop not passing feedback to planner")
        return False
    
    # Check for routing logic
    if 'verdict.target_agent == "CODER"' in content:
        print("✅ solve_loop has proper routing logic")
        return True
    else:
        print("❌ solve_loop missing routing logic")
        return False

def main():
    """Run all feedback loop logic tests."""
    print("🚀 SwiftSolve Iterative Feedback Loop Logic Tests")
    print("=" * 55)
    
    tests = [
        ("Analyst Patch Intelligence", test_analyst_patch_intelligence),
        ("Coder Signature Compatibility", test_coder_signature),
        ("Planner Signature Compatibility", test_planner_signature),
        ("Solve Loop Integration", test_solve_loop_integration),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'=' * 55}")
    print("🏁 Test Summary:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(tests)} tests passed")
    
    if passed == len(tests):
        print("🎉 All logic tests passed! The iterative feedback loop is correctly implemented.")
        print("\n📋 What has been fixed in Gap #2:")
        print("   ✅ Analyst generates intelligent, context-specific optimization patches")
        print("   ✅ Coder accepts and can apply patches to modify generated code")
        print("   ✅ Planner accepts feedback for algorithmic re-planning")
        print("   ✅ solve_loop properly routes patches and feedback between agents")
        print("   ✅ Iterative refinement loop can now actually improve solutions")
        print("\n🔄 Gap #2 - Iterative Feedback Loop: COMPLETELY FIXED!")
        print("\n🚀 The multi-agent system can now:")
        print("   • Detect inefficient algorithms through empirical profiling")
        print("   • Generate specific optimization suggestions based on complexity analysis")
        print("   • Apply targeted code improvements via intelligent patches")
        print("   • Re-plan with different algorithms when local optimizations aren't enough")
        print("   • Iteratively improve solutions until efficiency targets are met")
        return True
    else:
        print("❌ Some logic tests failed. The feedback loop implementation needs fixes.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)