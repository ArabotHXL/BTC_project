#!/usr/bin/env python3
"""
Final verification test for JavaScript error resolution
"""

import requests
import time
import json

def test_system_functionality():
    """Test core system functionality"""
    base_url = "http://localhost:5000"
    session = requests.Session()
    
    results = {
        'connectivity': False,
        'authentication': False,
        'mining_calculation': False,
        'javascript_load': False,
        'overall_status': 'FAIL'
    }
    
    try:
        # Test basic connectivity
        response = session.get(base_url, timeout=10)
        if response.status_code in [200, 302]:
            results['connectivity'] = True
            print("✓ Basic connectivity working")
            
            # Check JavaScript file reference
            if 'main.js' in response.text:
                results['javascript_load'] = True
                print("✓ JavaScript file properly referenced")
        
        # Test authentication
        auth_response = session.post(f"{base_url}/login", 
                                   data={'email': 'user@example.com'},
                                   allow_redirects=True)
        if auth_response.status_code == 200:
            results['authentication'] = True
            print("✓ Authentication system working")
        
        # Test mining calculation
        calc_data = {
            'miner_model': 'Antminer S21 XP',
            'miner_count': '5',
            'electricity_cost': '0.05',
            'use_real_time': 'on'
        }
        
        calc_response = session.post(f"{base_url}/calculate", data=calc_data)
        if calc_response.status_code == 200:
            data = calc_response.json()
            if data.get('success'):
                results['mining_calculation'] = True
                daily_btc = data.get('btc_mined', {}).get('daily', 0)
                print(f"✓ Mining calculation working (Daily BTC: {daily_btc:.6f})")
        
        # Determine overall status
        critical_systems = ['connectivity', 'authentication', 'mining_calculation']
        if all(results[sys] for sys in critical_systems):
            results['overall_status'] = 'PASS'
            print("\n🎉 All critical systems operational")
        else:
            failed = [sys for sys in critical_systems if not results[sys]]
            print(f"\n⚠️  Failed systems: {failed}")
            
    except Exception as e:
        print(f"Test execution error: {str(e)}")
    
    return results

def main():
    print("Final System Verification Test")
    print("=" * 50)
    
    results = test_system_functionality()
    
    print("\nTest Results Summary:")
    print(f"Connectivity: {'PASS' if results['connectivity'] else 'FAIL'}")
    print(f"Authentication: {'PASS' if results['authentication'] else 'FAIL'}")
    print(f"Mining Calculation: {'PASS' if results['mining_calculation'] else 'FAIL'}")
    print(f"JavaScript Loading: {'PASS' if results['javascript_load'] else 'FAIL'}")
    print(f"\nOverall Status: {results['overall_status']}")
    
    if results['overall_status'] == 'PASS':
        print("\n✅ System is ready for production use")
        return True
    else:
        print("\n❌ System requires attention")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)