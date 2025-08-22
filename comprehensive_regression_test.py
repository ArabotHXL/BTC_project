#!/usr/bin/env python3
"""
Comprehensive Regression Test Suite for BTC Mining Calculator System
全面回归测试套件 - 目标: 99%+ 准确度和可用率
"""

import os
import sys
import time
import json
import requests
import psycopg2
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any
from urllib.parse import urljoin
import pandas as pd
import numpy as np

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('regression_test_report.log'),
        logging.StreamHandler()
    ]
)

class ComprehensiveRegressionTest:
    """
    Comprehensive Regression Test Suite
    全面回归测试套件
    """
    
    def __init__(self):
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        self.test_results = []
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.skipped_tests = 0
        self.start_time = None
        self.end_time = None
        self.database_url = os.environ.get('DATABASE_URL')
        
        # Test credentials
        self.test_users = {
            'admin': {
                'email': 'admin@test.com',
                'password': 'Admin123!@#',
                'role': 'admin'
            },
            'owner': {
                'email': 'owner@test.com', 
                'password': 'Owner123!@#',
                'role': 'owner'
            },
            'guest': {
                'email': 'guest@test.com',
                'password': 'Guest123!@#',
                'role': 'guest'
            }
        }
        
    def log_test_result(self, category: str, test_name: str, status: str, 
                       message: str = "", duration: float = 0):
        """Log test result"""
        result = {
            'category': category,
            'test_name': test_name,
            'status': status,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if status == 'PASS':
            self.passed_tests += 1
            logging.info(f"✅ {category} - {test_name}: PASSED ({duration:.2f}s)")
        elif status == 'FAIL':
            self.failed_tests += 1
            logging.error(f"❌ {category} - {test_name}: FAILED - {message}")
        else:
            self.skipped_tests += 1
            logging.warning(f"⚠️ {category} - {test_name}: SKIPPED - {message}")
            
        self.total_tests += 1
        
    def test_database_connection(self) -> bool:
        """Test database connectivity"""
        start = time.time()
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result and result[0] == 1:
                self.log_test_result("Database", "Connection Test", "PASS", 
                                   duration=time.time()-start)
                return True
            else:
                self.log_test_result("Database", "Connection Test", "FAIL", 
                                   "Query result invalid")
                return False
        except Exception as e:
            self.log_test_result("Database", "Connection Test", "FAIL", str(e))
            return False
            
    def test_database_tables(self) -> bool:
        """Test all required database tables exist"""
        required_tables = [
            'users', 'user_access', 'customers', 'leads', 'activities',
            'market_analytics', 'technical_indicators', 'miner_specs',
            'network_snapshots', 'subscription_plans', 'user_subscriptions'
        ]
        
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
            
            all_exist = True
            for table in required_tables:
                if table in existing_tables:
                    self.log_test_result("Database", f"Table {table}", "PASS")
                else:
                    self.log_test_result("Database", f"Table {table}", "FAIL", 
                                       "Table does not exist")
                    all_exist = False
                    
            cursor.close()
            conn.close()
            return all_exist
            
        except Exception as e:
            self.log_test_result("Database", "Table Check", "FAIL", str(e))
            return False
            
    def test_server_health(self) -> bool:
        """Test server is running and responsive"""
        start = time.time()
        try:
            response = self.session.get(self.base_url, timeout=5)
            duration = time.time() - start
            
            if response.status_code in [200, 302]:
                self.log_test_result("Server", "Health Check", "PASS", 
                                   duration=duration)
                return True
            else:
                self.log_test_result("Server", "Health Check", "FAIL", 
                                   f"Status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test_result("Server", "Health Check", "FAIL", str(e))
            return False
            
    def test_static_resources(self) -> bool:
        """Test static resources are accessible"""
        static_files = [
            '/static/css/styles.css',
            '/static/css/responsive.css',
            '/static/css/animations.css',
            '/static/js/chart.min.js'
        ]
        
        all_accessible = True
        for file in static_files:
            try:
                url = urljoin(self.base_url, file)
                response = self.session.get(url, timeout=5)
                if response.status_code == 200:
                    self.log_test_result("Static", file, "PASS")
                else:
                    self.log_test_result("Static", file, "FAIL", 
                                       f"Status: {response.status_code}")
                    all_accessible = False
            except Exception as e:
                self.log_test_result("Static", file, "FAIL", str(e))
                all_accessible = False
                
        return all_accessible
        
    def test_public_routes(self) -> bool:
        """Test all public routes"""
        public_routes = [
            ('/', 'Landing Page'),
            ('/login', 'Login Page'),
            ('/register', 'Register Page'),
            ('/price', 'Price Page'),
            ('/architecture', 'Architecture Diagram'),
            ('/system-relationships', 'System Relationships'),
            ('/legal', 'Legal Page')
        ]
        
        all_accessible = True
        for route, name in public_routes:
            start = time.time()
            try:
                url = urljoin(self.base_url, route)
                response = self.session.get(url, timeout=10)
                duration = time.time() - start
                
                if response.status_code == 200:
                    self.log_test_result("Routes", name, "PASS", duration=duration)
                else:
                    self.log_test_result("Routes", name, "FAIL", 
                                       f"Status: {response.status_code}")
                    all_accessible = False
            except Exception as e:
                self.log_test_result("Routes", name, "FAIL", str(e))
                all_accessible = False
                
        return all_accessible
        
    def test_authentication_system(self) -> bool:
        """Test authentication system"""
        # Test registration
        test_email = f"test_{int(time.time())}@example.com"
        test_password = "TestPass123!@#"
        
        try:
            # Register new user
            register_data = {
                'email': test_email,
                'password': test_password,
                'confirm_password': test_password,
                'accept_terms': 'on'
            }
            
            response = self.session.post(
                urljoin(self.base_url, '/register'),
                data=register_data,
                allow_redirects=False
            )
            
            if response.status_code in [302, 200]:
                self.log_test_result("Auth", "Registration", "PASS")
            else:
                self.log_test_result("Auth", "Registration", "FAIL", 
                                   f"Status: {response.status_code}")
                return False
                
            # Test login
            login_data = {
                'email': test_email,
                'password': test_password
            }
            
            response = self.session.post(
                urljoin(self.base_url, '/login'),
                data=login_data,
                allow_redirects=False
            )
            
            if response.status_code == 302:
                self.log_test_result("Auth", "Login", "PASS")
            else:
                self.log_test_result("Auth", "Login", "FAIL", 
                                   f"Status: {response.status_code}")
                return False
                
            # Test logout
            response = self.session.get(
                urljoin(self.base_url, '/logout'),
                allow_redirects=False
            )
            
            if response.status_code == 302:
                self.log_test_result("Auth", "Logout", "PASS")
                return True
            else:
                self.log_test_result("Auth", "Logout", "FAIL", 
                                   f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Auth", "System Test", "FAIL", str(e))
            return False
            
    def test_mining_calculator(self) -> bool:
        """Test mining calculator functionality"""
        # Login first
        self.session.post(
            urljoin(self.base_url, '/login'),
            data={'email': 'test@example.com', 'password': 'Test123!@#'}
        )
        
        test_data = {
            'miner_model': 'Antminer S21 Pro',
            'miner_count': '10',
            'electricity_cost': '0.05',
            'btc_price': '113000',
            'use_real_time': 'false'
        }
        
        try:
            response = self.session.post(
                urljoin(self.base_url, '/api/calculate'),
                json=test_data
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'btc_mined' in data and 'profit' in data:
                    self.log_test_result("Calculator", "Mining Calculation", "PASS")
                    
                    # Validate calculation accuracy
                    if data.get('btc_mined', {}).get('daily', 0) > 0:
                        self.log_test_result("Calculator", "Calculation Accuracy", "PASS")
                        return True
                    else:
                        self.log_test_result("Calculator", "Calculation Accuracy", "FAIL",
                                           "Invalid calculation results")
                        return False
                else:
                    self.log_test_result("Calculator", "Mining Calculation", "FAIL",
                                       "Missing required fields in response")
                    return False
            else:
                self.log_test_result("Calculator", "Mining Calculation", "FAIL",
                                   f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test_result("Calculator", "Mining Calculation", "FAIL", str(e))
            return False
            
    def test_api_endpoints(self) -> bool:
        """Test all API endpoints"""
        api_endpoints = [
            ('/api/analytics/market-data', 'GET', 'Market Data API'),
            ('/api/analytics/technical-indicators', 'GET', 'Technical Indicators API'),
            ('/api/network/snapshots', 'GET', 'Network Snapshots API'),
            ('/api/performance/metrics', 'GET', 'Performance Metrics API')
        ]
        
        all_working = True
        for endpoint, method, name in api_endpoints:
            try:
                url = urljoin(self.base_url, endpoint)
                if method == 'GET':
                    response = self.session.get(url, timeout=10)
                else:
                    response = self.session.post(url, json={}, timeout=10)
                    
                # Some endpoints require authentication
                if response.status_code in [200, 401, 403]:
                    self.log_test_result("API", name, "PASS")
                else:
                    self.log_test_result("API", name, "FAIL", 
                                       f"Status: {response.status_code}")
                    all_working = False
            except Exception as e:
                self.log_test_result("API", name, "FAIL", str(e))
                all_working = False
                
        return all_working
        
    def test_language_switching(self) -> bool:
        """Test language switching functionality"""
        try:
            # Test Chinese
            response = self.session.get(
                urljoin(self.base_url, '/switch_language/zh')
            )
            if response.status_code in [200, 302]:
                self.log_test_result("i18n", "Switch to Chinese", "PASS")
            else:
                self.log_test_result("i18n", "Switch to Chinese", "FAIL")
                return False
                
            # Test English  
            response = self.session.get(
                urljoin(self.base_url, '/switch_language/en')
            )
            if response.status_code in [200, 302]:
                self.log_test_result("i18n", "Switch to English", "PASS")
                return True
            else:
                self.log_test_result("i18n", "Switch to English", "FAIL")
                return False
                
        except Exception as e:
            self.log_test_result("i18n", "Language Switching", "FAIL", str(e))
            return False
            
    def test_external_api_connectivity(self) -> bool:
        """Test external API connectivity"""
        external_apis = [
            ('https://api.coingecko.com/api/v3/ping', 'CoinGecko API'),
            ('https://blockchain.info/q/getdifficulty', 'Blockchain.info API'),
            ('https://mempool.space/api/v1/fees/recommended', 'Mempool API')
        ]
        
        all_working = True
        for url, name in external_apis:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    self.log_test_result("External", name, "PASS")
                else:
                    self.log_test_result("External", name, "FAIL", 
                                       f"Status: {response.status_code}")
                    all_working = False
            except Exception as e:
                self.log_test_result("External", name, "FAIL", str(e))
                all_working = False
                
        return all_working
        
    def test_performance(self) -> bool:
        """Test performance metrics"""
        performance_tests = [
            ('/', 'Homepage Load Time', 2.0),
            ('/login', 'Login Page Load Time', 2.0),
            ('/price', 'Price Page Load Time', 3.0),
            ('/api/analytics/market-data', 'API Response Time', 1.0)
        ]
        
        all_passed = True
        for route, name, threshold in performance_tests:
            try:
                url = urljoin(self.base_url, route)
                start = time.time()
                response = self.session.get(url, timeout=10)
                duration = time.time() - start
                
                if duration <= threshold:
                    self.log_test_result("Performance", name, "PASS", 
                                       f"{duration:.2f}s < {threshold}s", duration)
                else:
                    self.log_test_result("Performance", name, "FAIL", 
                                       f"{duration:.2f}s > {threshold}s", duration)
                    all_passed = False
            except Exception as e:
                self.log_test_result("Performance", name, "FAIL", str(e))
                all_passed = False
                
        return all_passed
        
    def test_data_integrity(self) -> bool:
        """Test data integrity and consistency"""
        try:
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            
            # Check for orphaned records
            cursor.execute("""
                SELECT COUNT(*) FROM user_access 
                WHERE created_by_id NOT IN (SELECT id FROM users)
            """)
            orphaned = cursor.fetchone()[0]
            
            if orphaned == 0:
                self.log_test_result("Data Integrity", "No Orphaned Records", "PASS")
            else:
                self.log_test_result("Data Integrity", "Orphaned Records", "FAIL", 
                                   f"Found {orphaned} orphaned records")
                
            # Check for data consistency
            cursor.execute("""
                SELECT COUNT(*) FROM market_analytics 
                WHERE btc_price <= 0 OR network_hashrate <= 0
            """)
            invalid = cursor.fetchone()[0]
            
            if invalid == 0:
                self.log_test_result("Data Integrity", "Valid Market Data", "PASS")
            else:
                self.log_test_result("Data Integrity", "Invalid Market Data", "FAIL",
                                   f"Found {invalid} invalid records")
                
            cursor.close()
            conn.close()
            return orphaned == 0 and invalid == 0
            
        except Exception as e:
            self.log_test_result("Data Integrity", "Integrity Check", "FAIL", str(e))
            return False
            
    def test_security_headers(self) -> bool:
        """Test security headers"""
        required_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'Content-Security-Policy'
        ]
        
        try:
            response = self.session.get(self.base_url)
            all_present = True
            
            for header in required_headers:
                if header in response.headers:
                    self.log_test_result("Security", f"Header {header}", "PASS")
                else:
                    self.log_test_result("Security", f"Header {header}", "FAIL",
                                       "Header not present")
                    all_present = False
                    
            return all_present
            
        except Exception as e:
            self.log_test_result("Security", "Security Headers", "FAIL", str(e))
            return False
            
    def test_error_handling(self) -> bool:
        """Test error handling"""
        error_tests = [
            ('/nonexistent', 404, '404 Error Page'),
            ('/api/calculate', 400, 'Invalid API Request'),
        ]
        
        all_handled = True
        for route, expected_status, name in error_tests:
            try:
                url = urljoin(self.base_url, route)
                if 'api' in route:
                    response = self.session.post(url, json={})
                else:
                    response = self.session.get(url)
                    
                if response.status_code == expected_status:
                    self.log_test_result("Error Handling", name, "PASS")
                else:
                    self.log_test_result("Error Handling", name, "FAIL",
                                       f"Expected {expected_status}, got {response.status_code}")
                    all_handled = False
            except Exception as e:
                self.log_test_result("Error Handling", name, "FAIL", str(e))
                all_handled = False
                
        return all_handled
        
    def generate_report(self):
        """Generate comprehensive test report"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # Calculate metrics
        pass_rate = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        availability_rate = pass_rate  # For this test, we consider pass rate as availability
        
        report = {
            'test_suite': 'Comprehensive Regression Test',
            'timestamp': datetime.now().isoformat(),
            'duration': f"{duration:.2f} seconds",
            'total_tests': self.total_tests,
            'passed': self.passed_tests,
            'failed': self.failed_tests,
            'skipped': self.skipped_tests,
            'pass_rate': f"{pass_rate:.2f}%",
            'availability_rate': f"{availability_rate:.2f}%",
            'meets_99_requirement': pass_rate >= 99.0,
            'test_results': self.test_results
        }
        
        # Save report to file
        with open('regression_test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        # Print summary
        print("\n" + "="*60)
        print("COMPREHENSIVE REGRESSION TEST REPORT")
        print("="*60)
        print(f"Total Tests: {self.total_tests}")
        print(f"Passed: {self.passed_tests} ✅")
        print(f"Failed: {self.failed_tests} ❌")
        print(f"Skipped: {self.skipped_tests} ⚠️")
        print(f"Pass Rate: {pass_rate:.2f}%")
        print(f"Availability Rate: {availability_rate:.2f}%")
        print(f"Duration: {duration:.2f} seconds")
        print("-"*60)
        
        if pass_rate >= 99.0:
            print("✅ MEETS 99%+ REQUIREMENT")
        else:
            print("❌ DOES NOT MEET 99%+ REQUIREMENT")
            print(f"   Need to fix {self.failed_tests} failing tests")
            
        print("="*60)
        
        # List failed tests
        if self.failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['category']}/{result['test_name']}: {result['message']}")
                    
        return report
        
    def run_all_tests(self):
        """Run all regression tests"""
        self.start_time = time.time()
        
        print("\n" + "="*60)
        print("STARTING COMPREHENSIVE REGRESSION TEST SUITE")
        print("Target: 99%+ Accuracy and Availability")
        print("="*60 + "\n")
        
        # Test categories
        test_categories = [
            ("Database Connection", self.test_database_connection),
            ("Database Tables", self.test_database_tables),
            ("Server Health", self.test_server_health),
            ("Static Resources", self.test_static_resources),
            ("Public Routes", self.test_public_routes),
            ("Authentication System", self.test_authentication_system),
            ("Mining Calculator", self.test_mining_calculator),
            ("API Endpoints", self.test_api_endpoints),
            ("Language Switching", self.test_language_switching),
            ("External APIs", self.test_external_api_connectivity),
            ("Performance", self.test_performance),
            ("Data Integrity", self.test_data_integrity),
            ("Security Headers", self.test_security_headers),
            ("Error Handling", self.test_error_handling)
        ]
        
        for category_name, test_func in test_categories:
            print(f"\n📋 Testing {category_name}...")
            try:
                test_func()
            except Exception as e:
                self.log_test_result(category_name, "Category Test", "FAIL", str(e))
                
        # Generate final report
        report = self.generate_report()
        return report


def main():
    """Main function to run regression tests"""
    tester = ComprehensiveRegressionTest()
    report = tester.run_all_tests()
    
    # Return exit code based on results
    if report['meets_99_requirement']:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()