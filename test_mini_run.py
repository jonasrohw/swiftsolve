#!/usr/bin/env python3
"""
Mini-Run Test Script
===================

Quick test of the mini research evaluation (18 iterations instead of 225).
Perfect for testing your setup before running the full benchmark.
"""

import json
import requests
import time
from pathlib import Path

def test_mini_run_api():
    """Test mini-run via API endpoint."""
    
    print("🧪 Testing Mini-Run via API")
    print("=" * 40)
    
    # API endpoint
    url = "http://localhost:8000/research/evaluate"
    
    # Mini-run request
    payload = {
        "seeds": [42, 123, 456],
        "max_workers": 2,
        "output_dir": "test_mini_results",
        "mini_run": True  # This is the key parameter!
    }
    
    print(f"📤 Sending request to {url}")
    print(f"   Payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        print(f"\n✅ Request successful!")
        print(f"   Evaluation ID: {result['evaluation_id']}")
        print(f"   Total runs: {result['total_runs']}")
        print(f"   Estimated duration: {result['estimated_duration_minutes']:.1f} minutes")
        
        return result['evaluation_id']
        
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the API server running?")
        print("   Start it with: PYTHONPATH=src uvicorn swiftsolve.main:app --host 127.0.0.1 --port 8000")
        return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_mini_run_direct():
    """Test mini-run directly via Python."""
    
    print("\n🧪 Testing Mini-Run via Direct Python Call")
    print("=" * 40)
    
    from src.swiftsolve.research.evaluation import ResearchEvaluationRunner
    import os
    
    # Check API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    
    print("🔑 API Key Status:")
    print(f"   OPENAI_API_KEY: {'✅ Set' if openai_key else '❌ Missing'}")
    print(f"   ANTHROPIC_API_KEY: {'✅ Set' if anthropic_key else '❌ Missing'}")
    
    if not (openai_key and anthropic_key):
        print("\n⚠️  API keys required for evaluation. Set them with:")
        print("   export OPENAI_API_KEY='your_key_here'")
        print("   export ANTHROPIC_API_KEY='your_key_here'")
        return
    
    print("\n📊 Initializing mini-run...")
    runner = ResearchEvaluationRunner(Path("test_mini_results_direct"), max_workers=1)
    
    print("🚀 Starting MINI evaluation (2 tasks, 18 iterations)...")
    print("   This will make actual API calls!")
    
    try:
        analysis = runner.run_full_evaluation(seeds=[42], mini_run=True)
        print(f"✅ Mini evaluation completed!")
        print(f"   Success rate: {analysis['evaluation_summary']['success_rate_percent']:.1f}%")
        print(f"   Total runs: {analysis['evaluation_summary']['total_runs']}")
        return analysis
    except Exception as e:
        print(f"❌ Mini evaluation failed: {e}")
        return None

if __name__ == "__main__":
    print("🎯 SwiftSolve Mini-Run Test")
    print("="*50)
    print("Mini-run: 2 tasks × 3 seeds × 3 replans = 18 iterations")
    print("Full-run: 25 tasks × 3 seeds × 3 replans = 225 iterations")
    print("Speed up: 12.5x faster! 🚀")
    print()
    
    # Test API first
    evaluation_id = test_mini_run_api()
    
    # Test direct call
    test_mini_run_direct()
    
    if evaluation_id:
        print(f"\n📋 Your mini evaluation is running with ID: {evaluation_id}")
        print(f"   Check results in: test_mini_results/{evaluation_id}/")
        print(f"   Monitor logs for progress updates")
