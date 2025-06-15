#!/usr/bin/env python3
"""
Comprehensive regression test suite for the mining calculator application
Tests all critical functionality after API integration changes
"""
import requests
import json
import time
import sys

class RegressionTestSuite:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_email = "hxl2022hao@gmail.com"
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def log_test(self, test_name, passed, details=""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append(f"[{status}] {test_name}: {details}")
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1
            print(f"❌ {test_name}: {details}")

    def test_authentication(self):
        """Test user authentication system"""
        print("Testing authentication system...")
        
        # Test login endpoint
        response = self.session.post(f"{self.base_url}/login", 
                                   data={"email": self.test_email})
        
        if response.status_code in [200, 302]:
            self.log_test("User Authentication", True, "Login successful")
            return True
        else:
            self.log_test("User Authentication", False, f"Login failed: {response.status_code}")
            return False

    def test_network_data_apis(self):
        """Test network data API endpoints"""
        print("Testing network data APIs...")
        
        # Test network stats endpoint
        response = self.session.get(f"{self.base_url}/network_stats")
        
        if response.status_code == 200:
            try:
                data = response.json()
                required_fields = ['price', 'difficulty', 'hashrate', 'block_reward', 'data_source']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    price = data.get('price', 0)
                    hashrate = data.get('hashrate', 0)
                    source = data.get('data_source', '')
                    
                    if price > 50000 and hashrate > 500:
                        self.log_test("Network Stats API", True, 
                                    f"Price: ${price:,.0f}, Hashrate: {hashrate:.1f}EH/s, Source: {source}")
                    else:
                        self.log_test("Network Stats API", False, 
                                    f"Invalid data values: price={price}, hashrate={hashrate}")
                else:
                    self.log_test("Network Stats API", False, f"Missing fields: {missing_fields}")
            except json.JSONDecodeError:
                self.log_test("Network Stats API", False, "Invalid JSON response")
        else:
            self.log_test("Network Stats API", False, f"HTTP error: {response.status_code}")

    def test_mining_comparison_api(self):
        """Test SHA-256 mining comparison API"""
        print("Testing mining comparison API...")
        
        response = self.session.get(f"{self.base_url}/mining/sha256_comparison")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success') and data.get('data'):
                    coins = data['data']
                    api_calls = data.get('api_calls_remaining', 0)
                    
                    if len(coins) >= 3:
                        self.log_test("SHA-256 Comparison API", True, 
                                    f"Retrieved {len(coins)} coins, {api_calls} calls remaining")
                    else:
                        self.log_test("SHA-256 Comparison API", False, 
                                    f"Insufficient coin data: {len(coins)} coins")
                else:
                    self.log_test("SHA-256 Comparison API", False, 
                                f"API error: {data.get('error', 'Unknown')}")
            except json.JSONDecodeError:
                self.log_test("SHA-256 Comparison API", False, "Invalid JSON response")
        else:
            self.log_test("SHA-256 Comparison API", False, f"HTTP error: {response.status_code}")

    def test_mining_calculation(self):
        """Test core mining calculation functionality"""
        print("Testing mining calculation engine...")
        
        # Test with realistic mining parameters
        calc_data = {
            'miner_model': 'Antminer S21',
            'miner_count': 100,
            'electricity_cost': 0.05,
            'client_electricity_cost': 0.08,
            'use_real_time_data': True
        }
        
        response = self.session.post(f"{self.base_url}/calculate", data=calc_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Check for essential calculation results
                btc_mined = data.get('btc_mined', {})
                client_profit = data.get('client_profit', {})
                
                daily_btc = btc_mined.get('daily', 0)
                daily_profit = client_profit.get('daily', 0)
                
                if daily_btc > 0 and daily_profit > 0:
                    self.log_test("Mining Calculation", True, 
                                f"Daily BTC: {daily_btc:.6f}, Daily profit: ${daily_profit:,.2f}")
                else:
                    self.log_test("Mining Calculation", False, 
                                f"Invalid calculation results: BTC={daily_btc}, profit={daily_profit}")
            except json.JSONDecodeError:
                self.log_test("Mining Calculation", False, "Invalid JSON response")
        else:
            self.log_test("Mining Calculation", False, f"HTTP error: {response.status_code}")

    def test_miners_api(self):
        """Test miners list API"""
        print("Testing miners API...")
        
        response = self.session.get(f"{self.base_url}/miners")
        
        if response.status_code == 200:
            try:
                data = response.json()
                miners = data.get('miners', [])
                
                if len(miners) >= 5:
                    # Check if miners have required fields
                    sample_miner = miners[0]
                    required_fields = ['name', 'hashrate', 'power_consumption']
                    
                    if all(field in sample_miner for field in required_fields):
                        self.log_test("Miners API", True, f"Retrieved {len(miners)} miners")
                    else:
                        self.log_test("Miners API", False, "Miners missing required fields")
                else:
                    self.log_test("Miners API", False, f"Insufficient miner data: {len(miners)}")
            except json.JSONDecodeError:
                self.log_test("Miners API", False, "Invalid JSON response")
        else:
            self.log_test("Miners API", False, f"HTTP error: {response.status_code}")

    def test_btc_price_api(self):
        """Test BTC price API"""
        print("Testing BTC price API...")
        
        response = self.session.get(f"{self.base_url}/btc_price")
        
        if response.status_code == 200:
            try:
                data = response.json()
                if data.get('success'):
                    price = data.get('price', 0)
                    if price > 50000:  # Reasonable BTC price range
                        self.log_test("BTC Price API", True, f"Current price: ${price:,.2f}")
                    else:
                        self.log_test("BTC Price API", False, f"Invalid price: ${price}")
                else:
                    self.log_test("BTC Price API", False, "API returned failure")
            except json.JSONDecodeError:
                self.log_test("BTC Price API", False, "Invalid JSON response")
        else:
            self.log_test("BTC Price API", False, f"HTTP error: {response.status_code}")

    def test_web_interface(self):
        """Test main web interface"""
        print("Testing web interface...")
        
        response = self.session.get(f"{self.base_url}/")
        
        if response.status_code == 200:
            html_content = response.text
            
            # Check for essential UI elements
            ui_elements = [
                'mining', 'calculator', 'hashrate', 'electricity',
                'BTC', 'calculate'
            ]
            
            found_elements = [elem for elem in ui_elements if elem.lower() in html_content.lower()]
            
            if len(found_elements) >= len(ui_elements) * 0.8:  # 80% of elements found
                self.log_test("Web Interface", True, f"UI elements present: {len(found_elements)}/{len(ui_elements)}")
            else:
                self.log_test("Web Interface", False, f"Missing UI elements: {len(found_elements)}/{len(ui_elements)}")
        else:
            self.log_test("Web Interface", False, f"HTTP error: {response.status_code}")

    def test_api_switching_mechanism(self):
        """Test API switching logic"""
        print("Testing API switching mechanism...")
        
        # Make multiple calls to check API call counting
        initial_response = self.session.get(f"{self.base_url}/network_stats")
        
        if initial_response.status_code == 200:
            try:
                initial_data = initial_response.json()
                initial_calls = initial_data.get('api_calls_remaining', 0)
                
                # Make another call
                second_response = self.session.get(f"{self.base_url}/network_stats")
                second_data = second_response.json()
                second_calls = second_data.get('api_calls_remaining', 0)
                
                # Check if API calls are being tracked
                if initial_calls >= second_calls:
                    self.log_test("API Call Tracking", True, 
                                f"Calls tracked: {initial_calls} -> {second_calls}")
                else:
                    self.log_test("API Call Tracking", False, 
                                f"Call tracking inconsistent: {initial_calls} -> {second_calls}")
                
                # Check data source information
                data_source = second_data.get('data_source', '')
                if 'CoinWarz' in data_source or 'blockchain.info' in data_source:
                    self.log_test("Data Source Identification", True, f"Source: {data_source}")
                else:
                    self.log_test("Data Source Identification", False, f"Unknown source: {data_source}")
                    
            except (json.JSONDecodeError, KeyError) as e:
                self.log_test("API Switching Mechanism", False, f"Data parsing error: {e}")
        else:
            self.log_test("API Switching Mechanism", False, f"HTTP error: {initial_response.status_code}")

    def run_all_tests(self):
        """Execute complete regression test suite"""
        print("=" * 60)
        print("REGRESSION TEST SUITE - Mining Calculator Application")
        print("=" * 60)
        
        start_time = time.time()
        
        # Authentication test (required for other tests)
        if not self.test_authentication():
            print("❌ Authentication failed - cannot proceed with authenticated tests")
            return False
        
        # Core functionality tests
        self.test_network_data_apis()
        self.test_mining_comparison_api()
        self.test_mining_calculation()
        self.test_miners_api()
        self.test_btc_price_api()
        self.test_web_interface()
        self.test_api_switching_mechanism()
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Print summary
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.passed_tests}")
        print(f"Failed: {self.failed_tests}")
        print(f"Success Rate: {success_rate:.1f}%")
        print(f"Duration: {duration:.2f} seconds")
        
        print("\nDETAILED RESULTS:")
        for result in self.test_results:
            print(f"  {result}")
        
        if self.failed_tests == 0:
            print("\n✅ ALL TESTS PASSED - Application ready for production")
            return True
        else:
            print(f"\n❌ {self.failed_tests} TEST(S) FAILED - Review issues above")
            return False

if __name__ == "__main__":
    test_suite = RegressionTestSuite()
    success = test_suite.run_all_tests()
    sys.exit(0 if success else 1)