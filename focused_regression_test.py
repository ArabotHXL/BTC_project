#!/usr/bin/env python3
"""
Focused regression test for Bitcoin mining calculator
Tests core functionality and language interface separation
"""

import requests
import json
import time
import sys

class FocusedRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        
    def log_result(self, test_name, success, details=""):
        """Log test result"""
        status = "✓" if success else "✗"
        self.test_results.append({
            'name': test_name,
            'success': success,
            'details': details
        })
        print(f"  {status} {test_name}")
        if details and not success:
            print(f"    {details}")
    
    def test_language_interfaces(self):
        """Test Chinese and English interface separation"""
        print("Testing language interfaces...")
        
        # Test Chinese interface redirect
        try:
            response = self.session.get(f"{self.base_url}/zh")
            success = response.status_code == 200
            self.log_result("Chinese interface (/zh)", success)
        except Exception as e:
            self.log_result("Chinese interface (/zh)", False, str(e))
        
        # Test English interface redirect
        try:
            response = self.session.get(f"{self.base_url}/en")
            success = response.status_code == 200
            self.log_result("English interface (/en)", success)
        except Exception as e:
            self.log_result("English interface (/en)", False, str(e))
    
    def test_api_endpoints(self):
        """Test core API endpoints"""
        print("Testing API endpoints...")
        
        # Test network stats
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            data = response.json()
            success = data.get('success', False) and 'hashrate' in data and 'price' in data
            hashrate = data.get('hashrate', 0)
            price = data.get('price', 0)
            self.log_result(
                "Network stats API", 
                success, 
                f"Hashrate: {hashrate:.1f} EH/s, Price: ${price:,.0f}"
            )
        except Exception as e:
            self.log_result("Network stats API", False, str(e))
        
        # Test miners endpoint
        try:
            response = self.session.get(f"{self.base_url}/miners")
            data = response.json()
            success = data.get('success', False) and len(data.get('miners', [])) > 0
            miner_count = len(data.get('miners', []))
            self.log_result(
                "Miners API", 
                success, 
                f"Loaded {miner_count} miner models"
            )
        except Exception as e:
            self.log_result("Miners API", False, str(e))
    
    def test_mining_calculation(self):
        """Test mining profitability calculation"""
        print("Testing mining calculations...")
        
        try:
            # Test with standard parameters
            calc_data = {
                'miner_model': 'Antminer S21',
                'miner_count': '10',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06',
                'btc_price': '100000',
                'use_real_time': 'on',
                'hashrate_source': 'manual',
                'manual_hashrate': '921.8'
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            data = response.json()
            
            if 'error' in data:
                self.log_result("Mining calculation", False, data['error'])
            else:
                daily_profit = data.get('daily_profit', 0)
                monthly_profit = data.get('monthly_profit', 0)
                btc_per_day = data.get('btc_per_day', 0)
                
                success = all([
                    'daily_profit' in data,
                    'monthly_profit' in data,
                    'btc_per_day' in data
                ])
                
                self.log_result(
                    "Mining calculation", 
                    success,
                    f"Daily: ${daily_profit:.2f}, Monthly: ${monthly_profit:.2f}, BTC/day: {btc_per_day:.6f}"
                )
                
        except Exception as e:
            self.log_result("Mining calculation", False, str(e))
    
    def test_data_accuracy(self):
        """Test network hashrate accuracy with manual input"""
        print("Testing data accuracy...")
        
        try:
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06',
                'btc_price': '100000',
                'use_real_time': 'on',
                'hashrate_source': 'manual',
                'manual_hashrate': '921.8'  # Accurate network hashrate
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            data = response.json()
            
            if 'error' in data:
                self.log_result("Manual hashrate accuracy", False, data['error'])
            else:
                # Verify calculation uses manual hashrate
                success = data.get('btc_per_day', 0) > 0
                self.log_result(
                    "Manual hashrate (921.8 EH/s)", 
                    success,
                    f"BTC per day: {data.get('btc_per_day', 0):.8f}"
                )
                
        except Exception as e:
            self.log_result("Manual hashrate accuracy", False, str(e))
    
    def test_coinwarz_integration(self):
        """Test CoinWarz API integration"""
        print("Testing CoinWarz integration...")
        
        try:
            response = self.session.get(f"{self.base_url}/sha256_mining_comparison")
            data = response.json()
            
            success = data.get('success', False) and len(data.get('coins', [])) > 0
            coin_count = len(data.get('coins', []))
            api_calls = data.get('api_calls_remaining', 0)
            
            self.log_result(
                "CoinWarz SHA-256 comparison", 
                success,
                f"{coin_count} coins, {api_calls} API calls remaining"
            )
            
        except Exception as e:
            self.log_result("CoinWarz SHA-256 comparison", False, str(e))
    
    def run_all_tests(self):
        """Run all regression tests"""
        print("=" * 60)
        print("FOCUSED REGRESSION TEST SUITE")
        print("=" * 60)
        
        self.test_language_interfaces()
        self.test_api_endpoints()
        self.test_mining_calculation()
        self.test_data_accuracy()
        self.test_coinwarz_integration()
        
        # Summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("✓ ALL TESTS PASSED - System is functioning correctly")
            return True
        else:
            print("✗ SOME TESTS FAILED - Review failed components")
            failed_tests = [r for r in self.test_results if not r['success']]
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return False

if __name__ == "__main__":
    tester = FocusedRegressionTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)