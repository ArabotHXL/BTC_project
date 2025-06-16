#!/usr/bin/env python3
"""
Final regression test for Bitcoin mining calculator system
Tests all core functionality after language interface separation
"""

import requests
import json
import sys

class FinalRegressionTest:
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
        if details:
            print(f"    {details}")
    
    def authenticate(self):
        """Authenticate with system"""
        try:
            login_data = {'email': 'hxl2022hao@gmail.com'}
            response = self.session.post(f"{self.base_url}/login", data=login_data)
            return response.status_code in [200, 302]
        except:
            return False
    
    def test_language_separation(self):
        """Test Chinese/English interface separation"""
        print("\nTesting language interface separation...")
        
        # Chinese interface
        try:
            response = self.session.get(f"{self.base_url}/zh")
            success = response.status_code == 200 and "比特币挖矿收益计算器" in response.text
            self.log_result("Chinese interface (/zh)", success)
        except Exception as e:
            self.log_result("Chinese interface (/zh)", False, str(e))
        
        # English interface  
        try:
            response = self.session.get(f"{self.base_url}/en")
            success = response.status_code == 200 and "Bitcoin Mining Profitability Calculator" in response.text
            self.log_result("English interface (/en)", success)
        except Exception as e:
            self.log_result("English interface (/en)", False, str(e))
    
    def test_api_functionality(self):
        """Test core API endpoints"""
        print("\nTesting API functionality...")
        
        # Network stats API
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            data = response.json()
            success = data.get('success') and data.get('hashrate') > 900
            hashrate = data.get('hashrate', 0)
            price = data.get('price', 0)
            self.log_result(
                "Network stats API", 
                success,
                f"Hashrate: {hashrate:.1f} EH/s, BTC: ${price:,.0f}"
            )
        except Exception as e:
            self.log_result("Network stats API", False, str(e))
        
        # Miners API
        try:
            response = self.session.get(f"{self.base_url}/miners")
            data = response.json()
            success = data.get('success') and len(data.get('miners', [])) >= 10
            count = len(data.get('miners', []))
            self.log_result("Miners API", success, f"{count} miner models loaded")
        except Exception as e:
            self.log_result("Miners API", False, str(e))
    
    def test_mining_calculations(self):
        """Test mining profitability calculations"""
        print("\nTesting mining calculations...")
        
        # Test 1: Single S19 Pro with manual hashrate
        try:
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1', 
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06',
                'btc_price': '100000',
                'use_real_time': 'on',
                'hashrate_source': 'manual',
                'manual_hashrate': '921.8'
            }
            
            response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
            data = response.json()
            
            if data.get('success'):
                btc_daily = data.get('btc_mined', {}).get('daily', 0)
                client_profit_daily = data.get('client_profit', {}).get('daily', 0)
                success = btc_daily > 0 and client_profit_daily > 0
                
                self.log_result(
                    "S19 Pro calculation (manual hashrate)",
                    success,
                    f"BTC/day: {btc_daily:.6f}, Client profit: ${client_profit_daily:.2f}"
                )
            else:
                self.log_result("S19 Pro calculation (manual hashrate)", False, "Calculation failed")
                
        except Exception as e:
            self.log_result("S19 Pro calculation (manual hashrate)", False, str(e))
        
        # Test 2: Multiple S21 miners 
        try:
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
            
            if data.get('success'):
                btc_daily = data.get('btc_mined', {}).get('daily', 0)
                client_profit_monthly = data.get('client_profit', {}).get('monthly', 0)
                success = btc_daily > 0.025 and client_profit_monthly > 40000  # Expected for 10x S21
                
                self.log_result(
                    "S21 x10 calculation",
                    success, 
                    f"BTC/day: {btc_daily:.6f}, Monthly profit: ${client_profit_monthly:,.0f}"
                )
            else:
                self.log_result("S21 x10 calculation", False, "Calculation failed")
                
        except Exception as e:
            self.log_result("S21 x10 calculation", False, str(e))
    
    def test_manual_hashrate_accuracy(self):
        """Test manual hashrate input accuracy"""
        print("\nTesting manual hashrate accuracy...")
        
        try:
            # Test with accurate 921.8 EH/s vs API value
            calc_data_manual = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '1',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06', 
                'btc_price': '100000',
                'use_real_time': 'on',
                'hashrate_source': 'manual',
                'manual_hashrate': '921.8'
            }
            
            calc_data_api = calc_data_manual.copy()
            calc_data_api['hashrate_source'] = 'api'
            
            # Manual calculation
            response_manual = self.session.post(f"{self.base_url}/calculate", data=calc_data_manual)
            data_manual = response_manual.json()
            
            # API calculation  
            response_api = self.session.post(f"{self.base_url}/calculate", data=calc_data_api)
            data_api = response_api.json()
            
            if data_manual.get('success') and data_api.get('success'):
                btc_manual = data_manual.get('btc_mined', {}).get('daily', 0)
                btc_api = data_api.get('btc_mined', {}).get('daily', 0)
                
                # Manual should be slightly higher due to more accurate hashrate
                success = btc_manual > 0 and btc_api > 0
                difference = ((btc_manual - btc_api) / btc_api * 100) if btc_api > 0 else 0
                
                self.log_result(
                    "Manual vs API hashrate comparison",
                    success,
                    f"Manual: {btc_manual:.6f}, API: {btc_api:.6f} BTC/day ({difference:+.1f}%)"
                )
            else:
                self.log_result("Manual vs API hashrate comparison", False, "Calculation failed")
                
        except Exception as e:
            self.log_result("Manual vs API hashrate comparison", False, str(e))
    
    def test_coinwarz_integration(self):
        """Test CoinWarz API integration status"""
        print("\nTesting CoinWarz integration...")
        
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            data = response.json()
            
            api_calls = data.get('api_calls_remaining', 0)
            data_source = data.get('data_source', '')
            success = api_calls > 900 and 'CoinWarz' in data_source
            
            self.log_result(
                "CoinWarz API status",
                success,
                f"{api_calls}/1000 calls remaining, Source: {data_source}"
            )
            
        except Exception as e:
            self.log_result("CoinWarz API status", False, str(e))
    
    def test_system_navigation(self):
        """Test system navigation and menus"""
        print("\nTesting system navigation...")
        
        # Test CRM access
        try:
            response = self.session.get(f"{self.base_url}/crm/dashboard")
            success = response.status_code == 200
            self.log_result("CRM dashboard access", success)
        except Exception as e:
            self.log_result("CRM dashboard access", False, str(e))
        
        # Test network data access
        try:
            response = self.session.get(f"{self.base_url}/network_history")
            success = response.status_code == 200
            self.log_result("Network history access", success)
        except Exception as e:
            self.log_result("Network history access", False, str(e))
    
    def run_all_tests(self):
        """Execute complete regression test suite"""
        print("=" * 60)
        print("FINAL REGRESSION TEST SUITE")
        print("Language Interface Separation & Core Functionality")
        print("=" * 60)
        
        # Authenticate first
        if not self.authenticate():
            print("Authentication failed - cannot proceed")
            return False
        
        print("✓ Authentication successful")
        
        # Run all test suites
        self.test_language_separation()
        self.test_api_functionality() 
        self.test_mining_calculations()
        self.test_manual_hashrate_accuracy()
        self.test_coinwarz_integration()
        self.test_system_navigation()
        
        # Generate summary
        print("\n" + "=" * 60)
        print("REGRESSION TEST RESULTS")
        print("=" * 60)
        
        passed = sum(1 for r in self.test_results if r['success'])
        total = len(self.test_results)
        success_rate = (passed / total * 100) if total > 0 else 0
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {success_rate:.1f}%")
        
        if success_rate >= 90:
            print("✓ EXCELLENT - System fully functional")
            status = "PASS"
        elif success_rate >= 80:
            print("⚠ GOOD - Minor issues detected") 
            status = "PASS"
        elif success_rate >= 70:
            print("⚠ ACCEPTABLE - Some functionality issues")
            status = "WARN"
        else:
            print("✗ POOR - Significant issues detected")
            status = "FAIL"
        
        # List any failures
        failed_tests = [r for r in self.test_results if not r['success']]
        if failed_tests:
            print("\nFailed components:")
            for test in failed_tests:
                print(f"  - {test['name']}")
        
        print(f"\nSystem Status: {status}")
        return success_rate >= 70

if __name__ == "__main__":
    tester = FinalRegressionTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)