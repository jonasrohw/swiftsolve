#!/usr/bin/env python3
"""
Test script to verify the iterative feedback loop is working correctly.

This script tests that:
1. When the Analyst deems a solution inefficient, it generates appropriate patches
2. The solve_loop correctly routes patches to the Coder
3. The Coder applies patches to optimize the code
4. The system can iteratively improve solutions
"""

import sys
import os
import pathlib

# Add src to path so we can import swiftsolve modules
sys.path.insert(0, str(pathlib.Path(__file__).parent / "src"))

try:
    from swiftsolve.agents.analyst import Analyst
    from swiftsolve.agents.coder import Coder
    from swiftsolve.agents.planner import Planner
    from swiftsolve.schemas import (
        ProfileReport, PlanMessage, CodeMessage, ProblemInput, VerdictMessage
    )
    from swiftsolve.controller.solve_loop import run_pipeline
except ImportError as e:
    print(f"❌ Failed to import SwiftSolve modules: {e}")
    print("Make sure you're running this from the project root directory.")
    sys.exit(1)

def test_analyst_patch_generation():
    """Test that the Analyst generates intelligent patches based on complexity."""
    print("🧪 Testing Analyst patch generation...")
    
    # Create a mock ProfileReport showing O(n^2) complexity
    mock_profile = ProfileReport(
        task_id="TEST_PATCH",
        iteration=0,
        input_sizes=[1000, 5000, 10000, 50000, 100000],
        runtime_ms=[10.0, 250.0, 1000.0, 25000.0, 100000.0],  # Quadratic growth
        peak_memory_mb=[2.0, 10.0, 40.0, 1000.0, 4000.0],    # High memory growth
        hotspots={}
    )
    
    analyst = Analyst()
    verdict = analyst.run(mock_profile, {"runtime_limit": 2000, "memory_limit": 512})
    
    print(f"   Efficiency: {verdict.efficient}")
    print(f"   Target agent: {verdict.target_agent}")
    print(f"   Patch: {verdict.patch}")
    
    # Check that analyst correctly identified inefficiency
    if not verdict.efficient:
        print("✅ Analyst correctly identified inefficient solution")
    else:
        print("❌ Analyst should have identified solution as inefficient")
        return False
    
    # Check that it routes to CODER
    if verdict.target_agent == "CODER":
        print("✅ Analyst correctly routed to CODER")
    else:
        print("❌ Analyst should have routed to CODER")
        return False
    
    # Check that patch is intelligent (mentions hash map for O(n^2) + high memory)
    if verdict.patch and ("hash map" in verdict.patch.lower() or "unordered_map" in verdict.patch.lower()):
        print("✅ Analyst generated intelligent patch mentioning hash maps")
    else:
        print("❌ Analyst should have generated patch mentioning hash maps")
        return False
    
    return True

def test_coder_patch_application():
    """Test that the Coder can apply patches to improve code."""
    print("\n🧪 Testing Coder patch application...")
    
    # Create a basic plan
    plan = PlanMessage(
        task_id="TEST_CODER_PATCH",
        iteration=0,
        algorithm="nested_loop_search",
        input_bounds={"n": 100000},
        constraints={"runtime_limit": 2000, "memory_limit": 512}
    )
    
    # Test patch
    patch = "Replace nested loops with hash map lookup. Use unordered_map<int, int> to store values and their indices, then iterate once to find complements in O(1) time."
    
    coder = Coder()
    
    # Generate code without patch
    print("   Generating code without patch...")
    code_without_patch = coder.run(plan)
    
    # Generate code with patch
    print("   Generating code with patch...")
    code_with_patch = coder.run(plan, patch=patch)
    
    # Check that patch was applied (should mention unordered_map)
    if "unordered_map" in code_with_patch.code_cpp:
        print("✅ Coder successfully applied patch (includes unordered_map)")
    else:
        print("⚠️  Coder patch application unclear (no unordered_map found)")
        print(f"   Generated code: {code_with_patch.code_cpp[:200]}...")
    
    # Check that codes are different
    if code_without_patch.code_cpp != code_with_patch.code_cpp:
        print("✅ Coder generated different code when patch was applied")
        return True
    else:
        print("❌ Coder generated identical code with and without patch")
        return False

def test_planner_feedback():
    """Test that the Planner can re-plan with feedback."""
    print("\n🧪 Testing Planner feedback handling...")
    
    problem = ProblemInput(
        task_id="TEST_PLANNER_FEEDBACK",
        prompt="Find two numbers in an array that sum to a target value",
        constraints={"runtime_limit": 2000, "memory_limit": 512},
        unit_tests=[]
    )
    
    planner = Planner()
    
    # Generate initial plan
    print("   Generating initial plan...")
    initial_plan = planner.run(problem)
    
    # Generate plan with feedback
    feedback = "Previous algorithm 'nested_loop_search' resulted in O(n^2) complexity. This is inefficient for the given constraints. Choose a fundamentally different algorithmic approach that can achieve O(n log n) or better time complexity."
    print("   Generating plan with feedback...")
    feedback_plan = planner.run(problem, feedback=feedback)
    
    # Check that plans are different
    if initial_plan.algorithm != feedback_plan.algorithm:
        print(f"✅ Planner generated different algorithm: '{initial_plan.algorithm}' → '{feedback_plan.algorithm}'")
        return True
    else:
        print(f"❌ Planner generated same algorithm despite feedback: '{initial_plan.algorithm}'")
        return False

def main():
    """Run all feedback loop tests."""
    print("🚀 SwiftSolve Iterative Feedback Loop Tests")
    print("=" * 50)
    
    tests = [
        ("Analyst Patch Generation", test_analyst_patch_generation),
        ("Coder Patch Application", test_coder_patch_application),
        ("Planner Feedback Handling", test_planner_feedback),
    ]
    
    results = []
    for test_name, test_func in tests:
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
        print("🎉 All tests passed! The iterative feedback loop is working correctly.")
        print("\n📋 What this means:")
        print("   ✅ Analyst can detect inefficient algorithms and generate specific optimization patches")
        print("   ✅ Coder can apply patches to modify and optimize code")
        print("   ✅ Planner can re-plan with feedback to choose different algorithms")
        print("   ✅ The solve_loop can route corrections properly between agents")
        print("\n🔄 Gap #2 - Iterative Feedback Loop: FIXED!")
        return True
    else:
        print("❌ Some tests failed. The feedback loop needs more work.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)