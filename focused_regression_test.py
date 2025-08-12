#!/usr/bin/env python3
"""
Focused Regression Test for Critical Issues
Target: 99%+ accuracy and applicability
"""

import requests
import json
import time
from datetime import datetime

def test_critical_endpoints():
    """Test the most critical endpoints that were failing"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": [],
        "timestamp": datetime.now().isoformat()
    }
    
    # Test 1: Application startup
    print("Testing application startup...")
    try:
        response = session.get(f"{base_url}/", timeout=10)
        if response.status_code == 200:
            print("✅ Application startup: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Application startup: FAILED ({response.status_code})")
            results["failed_tests"].append("Application startup")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Application startup: ERROR - {e}")
        results["failed_tests"].append("Application startup - CONNECTION ERROR")
        results["total_tests"] += 1
    
    # Test 2: Login page access (fixed template)
    print("Testing login page access...")
    try:
        response = session.get(f"{base_url}/login", timeout=10)
        if response.status_code == 200:
            print("✅ Login page: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Login page: FAILED ({response.status_code})")
            results["failed_tests"].append("Login page")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Login page: ERROR - {e}")
        results["failed_tests"].append("Login page - TEMPLATE ERROR")
        results["total_tests"] += 1
    
    # Test 3: Calculator page access
    print("Testing calculator page access...")
    try:
        response = session.get(f"{base_url}/calculator", timeout=10)
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("✅ Calculator page: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Calculator page: FAILED ({response.status_code})")
            results["failed_tests"].append("Calculator page")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Calculator page: ERROR - {e}")
        results["failed_tests"].append("Calculator page - TEMPLATE ERROR")
        results["total_tests"] += 1
    
    # Test 4: Batch calculator page access
    print("Testing batch calculator page access...")
    try:
        response = session.get(f"{base_url}/batch-calculator", timeout=10)
        if response.status_code in [200, 302]:  # 302 for redirect to login
            print("✅ Batch calculator page: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Batch calculator page: FAILED ({response.status_code})")
            results["failed_tests"].append("Batch calculator page")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Batch calculator page: ERROR - {e}")
        results["failed_tests"].append("Batch calculator page - ERROR")
        results["total_tests"] += 1
    
    # Test 5: Analytics API endpoint
    print("Testing analytics API endpoint...")
    try:
        response = session.get(f"{base_url}/api/analytics-data", timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get('success') and data.get('data'):
                print("✅ Analytics API: PASSED")
                results["passed_tests"] += 1
            else:
                print("❌ Analytics API: FAILED (Invalid data structure)")
                results["failed_tests"].append("Analytics API - Invalid data")
        else:
            print(f"❌ Analytics API: FAILED ({response.status_code})")
            results["failed_tests"].append("Analytics API")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Analytics API: ERROR - {e}")
        results["failed_tests"].append("Analytics API - ERROR")
        results["total_tests"] += 1
    
    # Test 6: Network data API endpoint
    print("Testing network data API endpoint...")
    try:
        response = session.get(f"{base_url}/api/network-data", timeout=10)
        if response.status_code == 200:
            print("✅ Network data API: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Network data API: FAILED ({response.status_code})")
            results["failed_tests"].append("Network data API")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Network data API: ERROR - {e}")
        results["failed_tests"].append("Network data API - ERROR")
        results["total_tests"] += 1
    
    # Test 7: Miner models API endpoint
    print("Testing miner models API endpoint...")
    try:
        response = session.get(f"{base_url}/api/miner-models", timeout=10)
        if response.status_code == 200:
            print("✅ Miner models API: PASSED")
            results["passed_tests"] += 1
        else:
            print(f"❌ Miner models API: FAILED ({response.status_code})")
            results["failed_tests"].append("Miner models API")
        results["total_tests"] += 1
    except Exception as e:
        print(f"❌ Miner models API: ERROR - {e}")
        results["failed_tests"].append("Miner models API - ERROR")
        results["total_tests"] += 1
    
    # Calculate success rate
    success_rate = (results["passed_tests"] / results["total_tests"]) * 100 if results["total_tests"] > 0 else 0
    
    print(f"\n📊 FOCUSED TEST RESULTS:")
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed Tests: {results['passed_tests']}")
    print(f"Success Rate: {success_rate:.2f}%")
    
    if results["failed_tests"]:
        print(f"\n❌ FAILED TESTS:")
        for test in results["failed_tests"]:
            print(f"  - {test}")
    
    # Save results
    with open(f"focused_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
        json.dump({
            **results,
            "success_rate": success_rate,
            "target_achieved": success_rate >= 99
        }, f, indent=2)
    
    return success_rate >= 99

if __name__ == "__main__":
    print("🔍 BTC Mining Calculator - Focused Regression Test")
    print("=" * 50)
    success = test_critical_endpoints()
    
    if success:
        print("\n🎉 TARGET ACHIEVED: 99%+ success rate!")
    else:
        print("\n⚠️  Target not achieved. Further fixes needed.")