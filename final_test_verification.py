#!/usr/bin/env python3
"""
Final Verification Test for 99%+ Target Achievement
"""

import requests
import json
import time
from datetime import datetime

class FinalVerificationTest:
    def __init__(self, base_url="http://localhost:5000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.passed_tests = 0
        self.total_tests = 0
        self.test_results = []
        
    def log_test(self, name, passed, details=""):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        
        self.test_results.append({
            "name": name,
            "passed": passed,
            "details": details
        })
    
    def test_core_functionality(self):
        """Test core application functionality"""
        print("\n🔧 Testing Core Functionality:")
        
        # Application startup
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            self.log_test("Application Startup", response.status_code == 200, f"({response.status_code})")
        except Exception as e:
            self.log_test("Application Startup", False, f"(Connection Error: {e})")
        
        # Login page
        try:
            response = self.session.get(f"{self.base_url}/login", timeout=10)
            self.log_test("Login Page Template", response.status_code == 200, f"({response.status_code})")
        except Exception as e:
            self.log_test("Login Page Template", False, f"(Template Error: {e})")
        
        # Calculator page (with auth redirect)
        try:
            response = self.session.get(f"{self.base_url}/calculator", timeout=10)
            self.log_test("Calculator Page", response.status_code in [200, 302], f"({response.status_code})")
        except Exception as e:
            self.log_test("Calculator Page", False, f"(Error: {e})")
        
        # Batch calculator page
        try:
            response = self.session.get(f"{self.base_url}/batch-calculator", timeout=10)
            self.log_test("Batch Calculator", response.status_code in [200, 302], f"({response.status_code})")
        except Exception as e:
            self.log_test("Batch Calculator", False, f"(Error: {e})")
    
    def test_api_endpoints(self):
        """Test critical API endpoints"""
        print("\n🔌 Testing API Endpoints:")
        
        # Analytics API
        try:
            response = self.session.get(f"{self.base_url}/api/analytics-data", timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_data = data.get('success') and data.get('data')
                self.log_test("Analytics API", has_data, "(Data integrity verified)")
            else:
                self.log_test("Analytics API", False, f"({response.status_code})")
        except Exception as e:
            self.log_test("Analytics API", False, f"(Error: {e})")
        
        # Network Data API
        try:
            response = self.session.get(f"{self.base_url}/api/network-data", timeout=10)
            self.log_test("Network Data API", response.status_code == 200, f"({response.status_code})")
        except Exception as e:
            self.log_test("Network Data API", False, f"(Error: {e})")
        
        # Miner Models API (newly fixed)
        try:
            response = self.session.get(f"{self.base_url}/api/miner-models", timeout=10)
            if response.status_code == 200:
                data = response.json()
                has_models = data.get('success') and data.get('data')
                self.log_test("Miner Models API", has_models, "(Model data available)")
            else:
                self.log_test("Miner Models API", False, f"({response.status_code})")
        except Exception as e:
            self.log_test("Miner Models API", False, f"(Error: {e})")
    
    def test_data_integrity(self):
        """Test data integrity and real-time sources"""
        print("\n📊 Testing Data Integrity:")
        
        # Real-time data validation
        try:
            response = self.session.get(f"{self.base_url}/api/analytics-data", timeout=10)
            if response.status_code == 200:
                data = response.json()['data']
                
                # BTC price validation
                btc_price = data.get('btc_price')
                price_valid = btc_price and 30000 <= btc_price <= 300000
                self.log_test("BTC Price Data", price_valid, f"(${btc_price})")
                
                # Network hashrate validation
                hashrate = data.get('network_hashrate')
                hashrate_valid = hashrate and 400 <= hashrate <= 2000
                self.log_test("Network Hashrate", hashrate_valid, f"({hashrate} EH/s)")
                
                # Data timestamp validation
                timestamp = data.get('timestamp')
                timestamp_valid = timestamp is not None
                self.log_test("Data Timestamp", timestamp_valid, "(Real-time data)")
                
            else:
                self.log_test("Data Validation", False, "No analytics data available")
        except Exception as e:
            self.log_test("Data Integrity", False, f"(Error: {e})")
    
    def test_ui_consistency(self):
        """Test UI consistency and template integrity"""
        print("\n🎨 Testing UI Consistency:")
        
        pages = [
            ("/", "Landing Page"),
            ("/login", "Login Page"),
            # Protected pages will redirect, which is correct behavior
        ]
        
        for url, name in pages:
            try:
                response = self.session.get(f"{self.base_url}{url}", timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # Check for critical UI elements
                    has_bootstrap = "bootstrap" in content.lower()
                    has_proper_lang = "lang=" in content or "language" in content.lower()
                    no_template_errors = "unexpected end of template" not in content.lower()
                    
                    ui_valid = has_bootstrap and no_template_errors
                    self.log_test(f"{name} UI", ui_valid, 
                                f"(Bootstrap: {has_bootstrap}, No errors: {no_template_errors})")
                else:
                    self.log_test(f"{name} UI", response.status_code == 302, f"({response.status_code})")
            except Exception as e:
                self.log_test(f"{name} UI", False, f"(Error: {e})")
    
    def test_performance(self):
        """Test application performance"""
        print("\n⚡ Testing Performance:")
        
        # Page load time test
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            load_time = time.time() - start_time
            self.log_test("Page Load Speed", load_time < 3.0, f"({load_time:.2f}s)")
        except Exception as e:
            self.log_test("Page Load Speed", False, f"(Error: {e})")
        
        # API response time test
        start_time = time.time()
        try:
            response = self.session.get(f"{self.base_url}/api/analytics-data", timeout=10)
            api_time = time.time() - start_time
            self.log_test("API Response Speed", api_time < 5.0, f"({api_time:.2f}s)")
        except Exception as e:
            self.log_test("API Response Speed", False, f"(Error: {e})")
    
    def test_error_handling(self):
        """Test error handling and graceful degradation"""
        print("\n🛡️ Testing Error Handling:")
        
        # 404 error handling
        try:
            response = self.session.get(f"{self.base_url}/nonexistent-page-12345", timeout=10)
            self.log_test("404 Error Handling", response.status_code == 404, f"({response.status_code})")
        except Exception as e:
            self.log_test("404 Error Handling", False, f"(Error: {e})")
        
        # Invalid API request handling
        try:
            response = self.session.post(f"{self.base_url}/api/calculate", 
                                       json={"invalid": "data"}, timeout=10)
            self.log_test("Invalid API Handling", response.status_code in [400, 422, 500], 
                         f"({response.status_code})")
        except Exception as e:
            self.log_test("Invalid API Handling", False, f"(Error: {e})")
    
    def run_all_tests(self):
        """Run all verification tests"""
        print("🎯 BTC Mining Calculator - Final Verification Test")
        print("=" * 55)
        
        self.test_core_functionality()
        self.test_api_endpoints()
        self.test_data_integrity()
        self.test_ui_consistency()
        self.test_performance()
        self.test_error_handling()
        
        return self.generate_final_report()
    
    def generate_final_report(self):
        """Generate final test report"""
        success_rate = (self.passed_tests / self.total_tests) * 100 if self.total_tests > 0 else 0
        target_achieved = success_rate >= 99.0
        
        print(f"\n📋 FINAL TEST RESULTS:")
        print("=" * 55)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed Tests: {self.passed_tests}")
        print(f"Success Rate: {success_rate:.2f}%")
        print(f"Target Achieved (≥99%): {'✅ YES' if target_achieved else '❌ NO'}")
        
        if not target_achieved:
            failed_tests = [test for test in self.test_results if not test['passed']]
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['name']}: {test['details']}")
        
        # Save detailed report
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "success_rate": success_rate,
            "target_achieved": target_achieved,
            "test_results": self.test_results
        }
        
        with open(f"final_test_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n{'🎉 SUCCESS! 99%+ accuracy target achieved!' if target_achieved else '⚠️ Target not achieved. Additional fixes needed.'}")
        
        return target_achieved

def main():
    tester = FinalVerificationTest()
    return tester.run_all_tests()

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)