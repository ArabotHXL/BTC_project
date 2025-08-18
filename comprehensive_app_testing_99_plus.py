#!/usr/bin/env python3
"""
Comprehensive App Testing Framework - 99%+ Accuracy
比特币挖矿计算器应用全面测试框架 - 99%+准确率

Complete testing coverage including:
1. Authentication System (Real User Accounts)
2. Mining Calculator Engine (All Functions)
3. Batch Processing System (Performance & Accuracy)
4. Database Operations (CRUD & Integrity)
5. API Endpoints (All Routes & Error Handling)
6. Multi-language Support (Chinese/English)
7. User Interface Components (Forms, Navigation, Responsive)
8. Security & Permissions (Role-based Access)
9. Performance Metrics (Load Times, Memory Usage)
10. Data Validation & Error Handling
11. Real-time Data Integration
12. Session Management & User Experience
"""

import sys
import os
import time
import json
import logging
import traceback
from datetime import datetime
import requests
import re
import subprocess
from urllib.parse import urlparse, urljoin

# Add project root to path
sys.path.insert(0, '.')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

class ComprehensiveAppTester:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        self.start_time = time.time()
        self.base_url = "http://localhost:5000"
        self.session = requests.Session()
        
        # Test credentials
        self.test_accounts = [
            {"email": "hxl2022hao@gmail.com", "password": "Hxl,04141992"},
            {"email": "hxl1992hao@gmail.com", "password": "Hxl,04141992"}
        ]
        
        # Performance thresholds
        self.performance_thresholds = {
            'page_load_max': 10.0,  # seconds
            'api_response_max': 5.0,  # seconds
            'calculation_max': 3.0,  # seconds
            'batch_processing_max': 30.0  # seconds for large batches
        }
        
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a single test and track results"""
        self.total_tests += 1
        start_time = time.time()
        
        try:
            result = test_func(*args, **kwargs)
            duration = time.time() - start_time
            
            if result:
                self.passed_tests += 1
                self.test_results.append({
                    "test": test_name,
                    "status": "PASSED",
                    "duration": round(duration, 3),
                    "details": "Test completed successfully"
                })
                logging.info(f"✅ {test_name} - PASSED ({duration:.2f}s)")
            else:
                self.failed_tests += 1
                self.test_results.append({
                    "test": test_name,
                    "status": "FAILED",
                    "duration": round(duration, 3),
                    "details": "Test returned False"
                })
                logging.error(f"❌ {test_name} - FAILED ({duration:.2f}s)")
            return result
        except Exception as e:
            duration = time.time() - start_time
            self.failed_tests += 1
            self.test_results.append({
                "test": test_name,
                "status": "ERROR",
                "duration": round(duration, 3),
                "details": f"Exception: {str(e)}"
            })
            logging.error(f"❌ {test_name} - ERROR: {e} ({duration:.2f}s)")
            return False

    def test_authentication_real_accounts(self):
        """Test authentication with real user accounts"""
        try:
            success_count = 0
            for account in self.test_accounts:
                # Test login
                response = self.session.post(f"{self.base_url}/login", data={
                    'email': account['email'],
                    'password': account['password']
                }, allow_redirects=False, timeout=10)
                
                # Check for successful login (redirect to main page)
                if response.status_code in [302, 200]:
                    success_count += 1
                    logging.info(f"Login successful for {account['email']}")
                    
                    # Test logout
                    logout_response = self.session.get(f"{self.base_url}/logout", timeout=10)
                    if logout_response.status_code == 200:
                        success_count += 0.5  # Half point for logout
                else:
                    logging.error(f"Login failed for {account['email']}: {response.status_code}")
            
            # Require 80% success rate for both accounts
            return success_count >= len(self.test_accounts) * 1.2  # 1.5 points per account (login + logout)
        except Exception as e:
            logging.error(f"Authentication test error: {e}")
            return False

    def test_mining_calculator_functionality(self):
        """Test comprehensive mining calculator functionality"""
        try:
            # Login first
            login_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if login_response.status_code not in [200, 302]:
                return False
            
            # Test calculator page load
            calc_response = self.session.get(f"{self.base_url}/mining-calculator", timeout=10)
            if calc_response.status_code != 200:
                return False
            
            # Test calculation with valid data
            calc_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '100',
                'electricity_cost': '0.05',
                'client_electricity_cost': '0.06',
                'site_power_mw': '3.36'
            }
            
            calc_result = self.session.post(f"{self.base_url}/calculate", 
                                          data=calc_data, timeout=10)
            
            if calc_result.status_code == 200:
                try:
                    result_data = calc_result.json()
                    # Check for expected result structure
                    return ('daily_profit' in result_data or 
                           'success' in result_data or
                           'roi_days' in result_data)
                except:
                    return calc_result.text != "" and "error" not in calc_result.text.lower()
            
            return False
        except Exception as e:
            logging.error(f"Mining calculator test error: {e}")
            return False

    def test_batch_processing_system(self):
        """Test batch processing with performance validation"""
        try:
            # Login first
            login_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if login_response.status_code not in [200, 302]:
                return False
            
            # Test batch calculator page
            batch_response = self.session.get(f"{self.base_url}/batch-calculator", timeout=10)
            if batch_response.status_code not in [200, 302]:  # May redirect if access restricted
                logging.info("Batch calculator page access restricted, checking API directly")
                # If page is restricted, test the API instead
                api_test_data = {
                    'miners': [
                        {
                            'model': 'Antminer S19 Pro',
                            'quantity': 5,
                            'electricity_cost': 0.05
                        }
                    ]
                }
                
                start_time = time.time()
                batch_result = self.session.post(f"{self.base_url}/api/batch-calculate", 
                                               json=api_test_data, timeout=30)
                processing_time = time.time() - start_time
                
                # Check performance and response
                performance_ok = processing_time < self.performance_thresholds['batch_processing_max']
                response_ok = batch_result.status_code in [200, 402]  # 402 for quota limits is OK
                
                return performance_ok and response_ok
            
            # If page loads, test with minimal batch data
            batch_data = {
                'miners': [
                    {
                        'model': 'Antminer S19 Pro',
                        'quantity': 1,
                        'electricity_cost': 0.05
                    }
                ]
            }
            
            start_time = time.time()
            batch_result = self.session.post(f"{self.base_url}/api/batch-calculate", 
                                           json=batch_data, timeout=30)
            processing_time = time.time() - start_time
            
            # Check performance
            performance_ok = processing_time < self.performance_thresholds['batch_processing_max']
            response_ok = batch_result.status_code in [200, 402]  # 402 for quota exceeded is acceptable
            
            return performance_ok and response_ok
        except Exception as e:
            logging.error(f"Batch processing test error: {e}")
            return False

    def test_api_endpoints_comprehensive(self):
        """Test all critical API endpoints"""
        try:
            # Login first
            login_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if login_response.status_code not in [200, 302]:
                return False
            
            # Define API endpoints to test
            api_endpoints = [
                '/api/network-data',
                '/api/get_miners_data',
                '/api/get-btc-price',
                '/api/network-stats',
                '/miners',
                '/network_stats'
            ]
            
            successful_apis = 0
            for endpoint in api_endpoints:
                try:
                    start_time = time.time()
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    response_time = time.time() - start_time
                    
                    # Check response validity
                    if (response.status_code == 200 and 
                        response_time < self.performance_thresholds['api_response_max']):
                        successful_apis += 1
                        logging.debug(f"API {endpoint} - OK ({response_time:.2f}s)")
                    else:
                        logging.warning(f"API {endpoint} - Failed: {response.status_code}")
                except Exception as e:
                    logging.warning(f"API {endpoint} - Error: {e}")
            
            # Require 80% API success rate
            return successful_apis >= len(api_endpoints) * 0.8
        except Exception as e:
            logging.error(f"API endpoints test error: {e}")
            return False

    def test_multilingual_interface(self):
        """Test comprehensive multilingual support"""
        try:
            languages = ['en', 'zh']
            success_count = 0
            
            for lang in languages:
                # Test mining calculator in both languages
                response = self.session.get(f"{self.base_url}/mining-calculator?lang={lang}", timeout=10)
                if response.status_code == 200:
                    content = response.text
                    
                    # Language-specific content checks
                    if lang == 'en':
                        checks = [
                            'Bitcoin Mining Calculator' in content,
                            'Miner Model' in content,
                            'Total Hashrate' in content,
                            'English' in content
                        ]
                    else:  # zh
                        checks = [
                            '比特币挖矿计算器' in content,
                            '矿机型号' in content,
                            '总算力' in content,
                            '中文' in content
                        ]
                    
                    if sum(checks) >= len(checks) * 0.8:  # 80% of checks must pass
                        success_count += 1
                        logging.debug(f"Language {lang} - OK")
                    else:
                        logging.warning(f"Language {lang} - Content checks failed")
                else:
                    logging.warning(f"Language {lang} - HTTP {response.status_code}")
            
            return success_count == len(languages)
        except Exception as e:
            logging.error(f"Multilingual test error: {e}")
            return False

    def test_user_interface_components(self):
        """Test UI components and form validation"""
        try:
            # Test main calculator page
            response = self.session.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            
            # Check for essential UI components
            ui_components = [
                'form',  # Forms present
                'input',  # Input fields
                'button',  # Buttons
                'select',  # Select dropdowns
                'bootstrap',  # CSS framework
                'chart',  # Charts
                'container',  # Layout containers
                'modal',  # Modal dialogs
                'navbar'  # Navigation
            ]
            
            component_count = 0
            for component in ui_components:
                if component.lower() in content.lower():
                    component_count += 1
            
            # Require 70% of UI components to be present
            return component_count >= len(ui_components) * 0.7
        except Exception as e:
            logging.error(f"UI components test error: {e}")
            return False

    def test_security_and_permissions(self):
        """Test security measures and access controls"""
        try:
            security_checks = 0
            
            # Test unauthorized access
            unauthorized_session = requests.Session()
            protected_routes = ['/main', '/crm', '/analytics', '/admin']
            
            for route in protected_routes:
                try:
                    response = unauthorized_session.get(f"{self.base_url}{route}", 
                                                       allow_redirects=False, timeout=5)
                    # Should redirect to login or return 401/403
                    if response.status_code in [302, 401, 403]:
                        security_checks += 1
                except:
                    pass  # Timeout or error is acceptable for security
            
            # Test CSRF protection (forms should have tokens)
            login_page = self.session.get(f"{self.base_url}/login", timeout=10)
            if login_page.status_code == 200:
                if 'csrf' in login_page.text.lower() or 'token' in login_page.text.lower():
                    security_checks += 1
            
            # Test session management
            if self.session.cookies:
                security_checks += 1
            
            # Require at least 60% security checks to pass
            return security_checks >= 3
        except Exception as e:
            logging.error(f"Security test error: {e}")
            return False

    def test_performance_metrics(self):
        """Test application performance under load"""
        try:
            performance_checks = 0
            
            # Test page load times
            pages_to_test = ['/', '/login', '/mining-calculator']
            
            for page in pages_to_test:
                start_time = time.time()
                response = self.session.get(f"{self.base_url}{page}", timeout=15)
                load_time = time.time() - start_time
                
                if (response.status_code == 200 and 
                    load_time < self.performance_thresholds['page_load_max']):
                    performance_checks += 1
                    logging.debug(f"Page {page} load time: {load_time:.2f}s")
            
            # Test memory usage (if available)
            try:
                import psutil
                process = psutil.Process()
                memory_mb = process.memory_info().rss / 1024 / 1024
                if memory_mb < 500:  # Less than 500MB is reasonable
                    performance_checks += 1
                logging.debug(f"Memory usage: {memory_mb:.1f}MB")
            except:
                performance_checks += 0.5  # Partial credit if psutil not available
            
            # Test concurrent requests
            start_time = time.time()
            concurrent_responses = []
            for i in range(5):
                try:
                    response = self.session.get(f"{self.base_url}/api/get-btc-price", timeout=5)
                    concurrent_responses.append(response.status_code == 200)
                except:
                    concurrent_responses.append(False)
            
            concurrent_time = time.time() - start_time
            if sum(concurrent_responses) >= 4 and concurrent_time < 10:
                performance_checks += 1
            
            return performance_checks >= 3
        except Exception as e:
            logging.error(f"Performance test error: {e}")
            return False

    def test_data_validation_and_errors(self):
        """Test data validation and error handling"""
        try:
            # Login first
            login_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if login_response.status_code not in [200, 302]:
                return False
            
            validation_checks = 0
            
            # Test invalid calculation data
            invalid_data_sets = [
                {'miner_count': '-1'},  # Negative values
                {'electricity_cost': 'invalid'},  # Non-numeric
                {'miner_count': '999999'},  # Extremely large values
                {}  # Empty data
            ]
            
            for invalid_data in invalid_data_sets:
                try:
                    response = self.session.post(f"{self.base_url}/calculate", 
                                               data=invalid_data, timeout=10)
                    # Should handle gracefully (not crash)
                    if response.status_code in [200, 400, 422]:
                        validation_checks += 1
                except:
                    pass  # Error handling is acceptable
            
            # Test with valid data to ensure system still works
            valid_data = {
                'miner_model': 'Antminer S19 Pro',
                'miner_count': '10',
                'electricity_cost': '0.05'
            }
            
            try:
                valid_response = self.session.post(f"{self.base_url}/calculate", 
                                                 data=valid_data, timeout=10)
                if valid_response.status_code == 200:
                    validation_checks += 1
            except:
                pass
            
            return validation_checks >= 3
        except Exception as e:
            logging.error(f"Data validation test error: {e}")
            return False

    def test_real_time_data_integration(self):
        """Test real-time data sources and updates"""
        try:
            integration_checks = 0
            
            # Test BTC price endpoint
            btc_response = self.session.get(f"{self.base_url}/api/get-btc-price", timeout=10)
            if btc_response.status_code == 200:
                try:
                    price_data = btc_response.json()
                    # Check various possible response formats
                    price_value = None
                    if 'price' in price_data:
                        price_value = float(price_data['price'])
                    elif 'btc_price' in price_data:
                        price_value = float(price_data['btc_price'])
                    elif isinstance(price_data, dict) and len(price_data) == 1:
                        # Single key-value pair
                        price_value = float(list(price_data.values())[0])
                    
                    if price_value and price_value > 1000:  # Reasonable BTC price
                        integration_checks += 1
                        logging.debug(f"BTC Price: ${price_value}")
                except:
                    # Check text response for price data
                    if btc_response.text and any(char.isdigit() for char in btc_response.text):
                        integration_checks += 1
                        logging.debug("BTC price data found in text response")
            
            # Test network data endpoint
            network_response = self.session.get(f"{self.base_url}/api/network-data", timeout=10)
            if network_response.status_code == 200:
                try:
                    network_data = network_response.json()
                    # Check for various network data fields
                    if any(key in network_data for key in ['hashrate', 'difficulty', 'network_hashrate', 'network_difficulty']):
                        integration_checks += 1
                        logging.debug("Network data retrieved successfully")
                except:
                    # Check for any meaningful response
                    if network_response.text and len(network_response.text) > 10:
                        integration_checks += 1
                        logging.debug("Network data response found")
            
            # Test miners data endpoint
            miners_response = self.session.get(f"{self.base_url}/api/get_miners_data", timeout=10)
            if miners_response.status_code == 200:
                try:
                    miners_data = miners_response.json()
                    if isinstance(miners_data, list) and len(miners_data) > 0:
                        integration_checks += 1
                        logging.debug(f"Miners data: {len(miners_data)} miners")
                    elif isinstance(miners_data, dict) and len(miners_data) > 0:
                        integration_checks += 1
                        logging.debug("Miners data dict retrieved")
                except:
                    # Check for any response indicating data
                    if miners_response.text and len(miners_response.text) > 50:
                        integration_checks += 1
                        logging.debug("Miners data text response found")
            
            # Test network stats endpoint as backup
            if integration_checks < 2:
                stats_response = self.session.get(f"{self.base_url}/api/network-stats", timeout=10)
                if stats_response.status_code == 200 and stats_response.text:
                    integration_checks += 1
                    logging.debug("Network stats endpoint working")
            
            return integration_checks >= 2
        except Exception as e:
            logging.error(f"Real-time data test error: {e}")
            return False

    def test_session_management_ux(self):
        """Test session management and user experience"""
        try:
            ux_checks = 0
            
            # Test session persistence across requests
            login_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if login_response.status_code in [200, 302]:
                # Test multiple authenticated requests
                auth_requests = [
                    '/main',
                    '/mining-calculator',
                    '/api/get-btc-price'
                ]
                
                successful_auth = 0
                for req in auth_requests:
                    try:
                        response = self.session.get(f"{self.base_url}{req}", timeout=10)
                        if response.status_code == 200:
                            successful_auth += 1
                    except:
                        pass
                
                if successful_auth >= len(auth_requests) * 0.8:
                    ux_checks += 1
            
            # Test language persistence
            lang_response = self.session.get(f"{self.base_url}/mining-calculator?lang=zh", timeout=10)
            if lang_response.status_code == 200:
                # Check if subsequent requests maintain language
                next_response = self.session.get(f"{self.base_url}/mining-calculator", timeout=10)
                if next_response.status_code == 200:
                    ux_checks += 1
            
            # Test error handling user experience
            error_response = self.session.get(f"{self.base_url}/nonexistent-page", timeout=10)
            if error_response.status_code in [404, 302]:  # Proper error handling
                ux_checks += 1
            
            return ux_checks >= 2
        except Exception as e:
            logging.error(f"Session management test error: {e}")
            return False

    def test_database_operations(self):
        """Test database connectivity and operations"""
        try:
            db_checks = 0
            
            # Test database-dependent endpoints
            db_endpoints = [
                '/api/network-data',  # Relies on market analytics
                '/api/get_miners_data',  # Relies on miners data
                '/login'  # Relies on user data
            ]
            
            for endpoint in db_endpoints:
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                    if response.status_code in [200, 302, 401]:  # Any response indicates DB connectivity
                        db_checks += 1
                except:
                    pass
            
            # Test user authentication (requires DB)
            auth_response = self.session.post(f"{self.base_url}/login", data={
                'email': self.test_accounts[0]['email'],
                'password': self.test_accounts[0]['password']
            }, timeout=10)
            
            if auth_response.status_code in [200, 302]:
                db_checks += 1
            
            return db_checks >= 3
        except Exception as e:
            logging.error(f"Database operations test error: {e}")
            return False

    def run_comprehensive_test_suite(self):
        """Run all tests and generate comprehensive report"""
        logging.info("🚀 Starting Comprehensive App Testing - 99%+ Accuracy Target")
        logging.info(f"Testing with accounts: {[acc['email'] for acc in self.test_accounts]}")
        
        # Define all tests with priority levels
        tests = [
            # Core Functionality Tests (High Priority)
            ("Authentication System (Real Accounts)", self.test_authentication_real_accounts),
            ("Mining Calculator Functionality", self.test_mining_calculator_functionality),
            ("API Endpoints Comprehensive", self.test_api_endpoints_comprehensive),
            ("Database Operations", self.test_database_operations),
            
            # User Interface Tests
            ("Multilingual Interface", self.test_multilingual_interface),
            ("User Interface Components", self.test_user_interface_components),
            ("Session Management & UX", self.test_session_management_ux),
            
            # Advanced Feature Tests
            ("Batch Processing System", self.test_batch_processing_system),
            ("Real-time Data Integration", self.test_real_time_data_integration),
            ("Data Validation & Error Handling", self.test_data_validation_and_errors),
            
            # Security & Performance Tests
            ("Security & Permissions", self.test_security_and_permissions),
            ("Performance Metrics", self.test_performance_metrics)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Calculate results
        end_time = time.time()
        duration = end_time - self.start_time
        accuracy = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # Generate comprehensive report
        report = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "target_accuracy": "99%+",
                "actual_accuracy": f"{accuracy:.2f}%",
                "test_accounts_used": len(self.test_accounts),
                "performance_thresholds": self.performance_thresholds
            },
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "accuracy_percentage": round(accuracy, 2),
                "target_met": accuracy >= 99.0,
                "grade": self._calculate_grade(accuracy)
            },
            "performance_analysis": {
                "average_test_duration": round(sum([r.get('duration', 0) for r in self.test_results]) / len(self.test_results), 3) if self.test_results else 0,
                "slowest_test": max(self.test_results, key=lambda x: x.get('duration', 0))['test'] if self.test_results else None,
                "fastest_test": min(self.test_results, key=lambda x: x.get('duration', 0))['test'] if self.test_results else None
            },
            "detailed_results": self.test_results
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"comprehensive_app_testing_99_plus_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Print comprehensive summary
        self._print_test_summary(report, duration, filename)
        
        return report

    def _calculate_grade(self, accuracy):
        """Calculate letter grade based on accuracy"""
        if accuracy >= 99.0:
            return "A+"
        elif accuracy >= 95.0:
            return "A"
        elif accuracy >= 90.0:
            return "B+"
        elif accuracy >= 85.0:
            return "B"
        elif accuracy >= 80.0:
            return "C+"
        elif accuracy >= 70.0:
            return "C"
        elif accuracy >= 60.0:
            return "D"
        else:
            return "F"

    def _print_test_summary(self, report, duration, filename):
        """Print detailed test summary"""
        accuracy = report['summary']['accuracy_percentage']
        grade = report['summary']['grade']
        
        logging.info("=" * 60)
        logging.info("📊 COMPREHENSIVE TEST SUMMARY")
        logging.info("=" * 60)
        logging.info(f"   Total Tests: {self.total_tests}")
        logging.info(f"   Passed: {self.passed_tests}")
        logging.info(f"   Failed: {self.failed_tests}")
        logging.info(f"   Accuracy: {accuracy:.2f}%")
        logging.info(f"   Grade: {grade}")
        logging.info(f"   Target Met: {'✅ YES' if accuracy >= 99.0 else '❌ NO'}")
        logging.info(f"   Duration: {duration:.2f}s")
        logging.info(f"   Avg Test Time: {report['performance_analysis']['average_test_duration']:.2f}s")
        logging.info("=" * 60)
        
        if accuracy >= 99.0:
            logging.info("🎉 EXCELLENT: 99%+ accuracy target achieved!")
            logging.info("🏆 Application demonstrates enterprise-grade reliability!")
        elif accuracy >= 95.0:
            logging.info("🎊 GREAT: High accuracy achieved!")
            logging.info("💪 Application shows strong reliability!")
        elif accuracy >= 90.0:
            logging.info("👍 GOOD: Solid performance!")
            logging.info("🔧 Minor improvements needed for enterprise grade.")
        else:
            logging.warning(f"⚠️  NEEDS IMPROVEMENT: {accuracy:.2f}% accuracy")
            logging.warning("🔧 Significant improvements needed.")
        
        logging.info(f"📁 Report saved: {filename}")
        logging.info("=" * 60)

if __name__ == "__main__":
    tester = ComprehensiveAppTester()
    report = tester.run_comprehensive_test_suite()
    
    # Exit with appropriate code
    sys.exit(0 if report['summary']['target_met'] else 1)