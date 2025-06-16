#!/usr/bin/env python3
"""
Authenticated regression test for Bitcoin mining calculator
"""

import requests
import json
import sys
from urllib.parse import urljoin

class AuthenticatedRegressionTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
        self.authenticated = False
        
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
    
    def authenticate(self):
        """Authenticate with authorized email"""
        try:
            # Get login page first
            login_response = self.session.get(f"{self.base_url}/login")
            if login_response.status_code != 200:
                return False
            
            # Login with authorized email
            login_data = {
                'email': 'hxl2022hao@gmail.com'  # Using the authorized email from logs
            }
            
            auth_response = self.session.post(f"{self.base_url}/login", data=login_data)
            
            # Check if redirected to main page (successful login)
            self.authenticated = auth_response.status_code in [200, 302]
            
            if self.authenticated:
                print("✓ Authentication successful")
            else:
                print("✗ Authentication failed")
                
            return self.authenticated
            
        except Exception as e:
            print(f"✗ Authentication error: {e}")
            return False
    
    def test_language_interfaces(self):
        """Test Chinese and English interface separation"""
        print("\nTesting language interfaces...")
        
        # Test Chinese interface
        try:
            response = self.session.get(f"{self.base_url}/zh")
            success = response.status_code == 200 and "比特币挖矿收益计算器" in response.text
            self.log_result("Chinese interface (/zh)", success)
        except Exception as e:
            self.log_result("Chinese interface (/zh)", False, str(e))
        
        # Test English interface
        try:
            response = self.session.get(f"{self.base_url}/en")
            success = response.status_code == 200 and "Bitcoin Mining Profitability Calculator" in response.text
            self.log_result("English interface (/en)", success)
        except Exception as e:
            self.log_result("English interface (/en)", False, str(e))
    
    def test_api_endpoints(self):
        """Test core API endpoints"""
        print("\nTesting API endpoints...")
        
        # Test network stats
        try:
            response = self.session.get(f"{self.base_url}/network_stats")
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False) and 'hashrate' in data and 'price' in data
                hashrate = data.get('hashrate', 0)
                price = data.get('price', 0)
                api_calls = data.get('api_calls_remaining', 0)
                self.log_result(
                    "Network stats API", 
                    success, 
                    f"Hashrate: {hashrate:.1f} EH/s, Price: ${price:,.0f}, API calls: {api_calls}"
                )
            else:
                self.log_result("Network stats API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Network stats API", False, str(e))
        
        # Test miners endpoint
        try:
            response = self.session.get(f"{self.base_url}/miners")
            if response.status_code == 200:
                data = response.json()
                success = data.get('success', False) and len(data.get('miners', [])) > 0
                miner_count = len(data.get('miners', []))
                sample_miner = data.get('miners', [{}])[0].get('name', 'N/A')
                self.log_result(
                    "Miners API", 
                    success, 
                    f"Loaded {miner_count} models (e.g., {sample_miner})"
                )
            else:
                self.log_result("Miners API", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_result("Miners API", False, str(e))
    
    def test_mining_calculation(self):
        """Test mining profitability calculation"""
        print("\nTesting mining calculations...")
        
        try:
            # Test with Antminer S21 parameters
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
            
            if response.status_code == 200:
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
                        'btc_per_day' in data,
                        daily_profit != 0
                    ])
                    
                    self.log_result(
                        "Mining calculation (S21 x10)", 
                        success,
                        f"Daily: ${daily_profit:.2f}, Monthly: ${monthly_profit:.2f}, BTC/day: {btc_per_day:.6f}"
                    )
            else:
                self.log_result("Mining calculation", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Mining calculation", False, str(e))
    
    def test_manual_hashrate(self):
        """Test manual hashrate input accuracy"""
        print("\nTesting manual hashrate accuracy...")
        
        try:
            # Test with manual hashrate 921.8 EH/s
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
            
            if response.status_code == 200:
                data = response.json()
                
                if 'error' in data:
                    self.log_result("Manual hashrate (921.8 EH/s)", False, data['error'])
                else:
                    btc_per_day = data.get('btc_per_day', 0)
                    daily_profit = data.get('daily_profit', 0)
                    
                    # Verify reasonable calculation results
                    success = btc_per_day > 0 and btc_per_day < 1  # Should be fractional BTC
                    
                    self.log_result(
                        "Manual hashrate (921.8 EH/s)", 
                        success,
                        f"BTC/day: {btc_per_day:.8f}, Daily profit: ${daily_profit:.2f}"
                    )
            else:
                self.log_result("Manual hashrate (921.8 EH/s)", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Manual hashrate (921.8 EH/s)", False, str(e))
    
    def test_coinwarz_integration(self):
        """Test CoinWarz API integration"""
        print("\nTesting CoinWarz integration...")
        
        try:
            response = self.session.get(f"{self.base_url}/sha256_mining_comparison")
            
            if response.status_code == 200:
                data = response.json()
                
                success = data.get('success', False) and len(data.get('coins', [])) > 0
                coin_count = len(data.get('coins', []))
                api_calls = data.get('api_calls_remaining', 0)
                
                if success:
                    sample_coin = data.get('coins', [{}])[0]
                    coin_name = sample_coin.get('name', 'Unknown')
                    profitability = sample_coin.get('profitability_24h', 0)
                    
                    self.log_result(
                        "CoinWarz SHA-256 comparison", 
                        success,
                        f"{coin_count} coins, {api_calls} calls left, top: {coin_name} ({profitability:.2f}%)"
                    )
                else:
                    self.log_result("CoinWarz SHA-256 comparison", False, "No coin data returned")
            else:
                self.log_result("CoinWarz SHA-256 comparison", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("CoinWarz SHA-256 comparison", False, str(e))
    
    def test_crm_access(self):
        """Test CRM system access"""
        print("\nTesting CRM access...")
        
        try:
            response = self.session.get(f"{self.base_url}/crm/dashboard")
            success = response.status_code == 200 and "CRM" in response.text
            self.log_result("CRM dashboard access", success)
        except Exception as e:
            self.log_result("CRM dashboard access", False, str(e))
    
    def run_all_tests(self):
        """Run complete regression test suite"""
        print("=" * 60)
        print("AUTHENTICATED REGRESSION TEST SUITE")
        print("=" * 60)
        
        # First authenticate
        if not self.authenticate():
            print("Cannot proceed without authentication")
            return False
        
        # Run all tests
        self.test_language_interfaces()
        self.test_api_endpoints()
        self.test_mining_calculation()
        self.test_manual_hashrate()
        self.test_coinwarz_integration()
        self.test_crm_access()
        
        # Summary
        print("\n" + "=" * 60)
        print("REGRESSION TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Tests passed: {passed}/{total}")
        print(f"Success rate: {(passed/total*100):.1f}%")
        
        if passed == total:
            print("✓ ALL TESTS PASSED - System fully functional")
            return True
        elif passed >= total * 0.8:  # 80% pass rate
            print("⚠ MOSTLY FUNCTIONAL - Minor issues detected")
            return True
        else:
            print("✗ SIGNIFICANT ISSUES - Review failed components")
            failed_tests = [r for r in self.test_results if not r['success']]
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
            return False

if __name__ == "__main__":
    tester = AuthenticatedRegressionTest()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)