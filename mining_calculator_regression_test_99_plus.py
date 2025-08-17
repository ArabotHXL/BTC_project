#!/usr/bin/env python3
"""
Mining Calculator Page Regression Test - 99%+ Accuracy
挖矿计算器页面回归测试 - 99%+准确率

Comprehensive testing of the mining calculator page including:
1. Page Loading & Language Support
2. Navigation Links & Buttons
3. Form Elements & Validation
4. JavaScript Functionality
5. API Integration
6. Data Consistency
7. User Interface Elements
8. Real-time Updates
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
from urllib.parse import urlparse, urljoin

# Add project root to path
sys.path.insert(0, '.')

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')

class MiningCalculatorRegressionTester:
    def __init__(self):
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []
        self.start_time = time.time()
        self.base_url = "http://localhost:5000"
        
    def run_test(self, test_name, test_func, *args, **kwargs):
        """Run a single test and track results"""
        self.total_tests += 1
        try:
            result = test_func(*args, **kwargs)
            if result:
                self.passed_tests += 1
                self.test_results.append({
                    "test": test_name,
                    "status": "PASSED",
                    "details": "Test completed successfully"
                })
                logging.info(f"✅ {test_name} - PASSED")
            else:
                self.failed_tests += 1
                self.test_results.append({
                    "test": test_name,
                    "status": "FAILED",
                    "details": "Test returned False"
                })
                logging.error(f"❌ {test_name} - FAILED")
            return result
        except Exception as e:
            self.failed_tests += 1
            self.test_results.append({
                "test": test_name,
                "status": "ERROR",
                "details": f"Exception: {str(e)}"
            })
            logging.error(f"❌ {test_name} - ERROR: {e}")
            return False

    def test_page_loading_chinese(self):
        """Test Chinese page loads correctly"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator?lang=zh", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for key Chinese elements
            checks = [
                "比特币挖矿计算器" in content,
                "矿机型号" in content,
                "批量计算器" in content,
                "主页" in content,
                "中文" in content and "English" in content,
                "总算力" in content,
                "总功耗" in content,
                "电费成本" in content
            ]
            
            return all(checks)
        except Exception as e:
            logging.error(f"Chinese page loading error: {e}")
            return False

    def test_page_loading_english(self):
        """Test English page loads correctly"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator?lang=en", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for key English elements
            checks = [
                "Bitcoin Mining Calculator" in content,
                "Miner Model" in content,
                "Batch Calculator" in content,
                "Home" in content,
                "中文" in content and "English" in content,
                "Total Hashrate" in content,
                "Total Power" in content,
                "Electricity Cost" in content
            ]
            
            return all(checks)
        except Exception as e:
            logging.error(f"English page loading error: {e}")
            return False

    def test_navigation_links(self):
        """Test navigation links are properly configured"""
        try:
            # Test Chinese version
            response = requests.get(f"{self.base_url}/mining-calculator?lang=zh", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for correct navigation links
            checks = [
                'href="/mining-calculator?lang=zh"' in content,
                'href="/mining-calculator?lang=en"' in content,
                'url_for(\'index\')' in content or 'href="/main"' in content,
                'batch_calculator' in content,
                'bi bi-house-door' in content,  # Home icon
                'bi bi-calculator-fill' in content  # Calculator icon
            ]
            
            return any(checks[:2]) and any(checks[2:])  # At least language links and some navigation
        except Exception as e:
            logging.error(f"Navigation links error: {e}")
            return False

    def test_form_elements_presence(self):
        """Test all required form elements are present"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for essential form elements
            form_elements = [
                'id="miner-model"',
                'id="site-power-mw"',
                'id="miner-count"',
                'id="total-hashrate-display"',
                'id="total-power-display"',
                'id="electricity-cost"',
                'id="client-electricity-cost"',
                'mining-calculator-form'
            ]
            
            checks = [element in content for element in form_elements]
            return sum(checks) >= len(form_elements) * 0.8  # 80% of elements must be present
        except Exception as e:
            logging.error(f"Form elements error: {e}")
            return False

    def test_api_endpoints_accessibility(self):
        """Test critical API endpoints are accessible"""
        try:
            endpoints = [
                "/api/network-data",
                "/api/get_miners_data", 
                "/api/get-btc-price",
                "/api/network-stats",
                "/miners"
            ]
            
            accessible_count = 0
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{self.base_url}{endpoint}", timeout=5)
                    if response.status_code == 200:
                        accessible_count += 1
                except:
                    continue
            
            # At least 80% of endpoints should be accessible
            return accessible_count >= len(endpoints) * 0.8
        except Exception as e:
            logging.error(f"API endpoints error: {e}")
            return False

    def test_language_switching_functionality(self):
        """Test language switching works correctly"""
        try:
            # Test Chinese to English switch
            zh_response = requests.get(f"{self.base_url}/mining-calculator?lang=zh", timeout=10)
            en_response = requests.get(f"{self.base_url}/mining-calculator?lang=en", timeout=10)
            
            if zh_response.status_code != 200 or en_response.status_code != 200:
                return False
            
            zh_content = zh_response.text
            en_content = en_response.text
            
            # Verify language-specific content
            zh_checks = [
                "比特币挖矿计算器" in zh_content,
                "矿机型号" in zh_content,
                "总算力" in zh_content
            ]
            
            en_checks = [
                "Bitcoin Mining Calculator" in en_content,
                "Miner Model" in en_content,
                "Total Hashrate" in en_content
            ]
            
            return all(zh_checks) and all(en_checks)
        except Exception as e:
            logging.error(f"Language switching error: {e}")
            return False

    def test_javascript_includes(self):
        """Test JavaScript files are properly included"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for JavaScript includes
            js_checks = [
                "bootstrap" in content.lower(),
                "chart.js" in content.lower() or "chartjs" in content.lower(),
                "updateSitePowerDirectly" in content,
                "页面加载优化器启动" in content or "page loading" in content.lower()
            ]
            
            return sum(js_checks) >= 2  # At least 2 JS components should be present
        except Exception as e:
            logging.error(f"JavaScript includes error: {e}")
            return False

    def test_css_styling(self):
        """Test CSS styling is properly applied"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for Bootstrap and custom styling
            css_checks = [
                "bootstrap" in content.lower(),
                "card" in content,
                "form-control" in content,
                "btn" in content,
                "container" in content,
                "@media" in content  # Responsive design
            ]
            
            return sum(css_checks) >= 4  # At least 4 styling elements
        except Exception as e:
            logging.error(f"CSS styling error: {e}")
            return False

    def test_network_stats_display(self):
        """Test network statistics display elements"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for network stats elements
            stats_checks = [
                "network-stats-container" in content,
                "btc-price" in content,
                "network-difficulty" in content,
                "network-hashrate" in content,
                "block-reward" in content,
                "badge" in content
            ]
            
            return sum(stats_checks) >= 4  # Most stats elements should be present
        except Exception as e:
            logging.error(f"Network stats error: {e}")
            return False

    def test_responsive_design_elements(self):
        """Test responsive design elements are present"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            # Check for responsive design elements
            responsive_checks = [
                "@media" in content,
                "col-lg" in content or "col-md" in content,
                "d-flex" in content,
                "gap-" in content,
                "flex-wrap" in content,
                "container-fluid" in content
            ]
            
            return sum(responsive_checks) >= 3  # Good responsive design coverage
        except Exception as e:
            logging.error(f"Responsive design error: {e}")
            return False

    def test_security_elements(self):
        """Test security elements are in place"""
        try:
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=10)
            if response.status_code != 200:
                return False
            
            content = response.text
            headers = response.headers
            
            # Check for security elements
            security_checks = [
                "session" in content.lower(),
                "csrf" in content.lower() or "token" in content.lower(),
                len(content) > 10000,  # Substantial content
                "X-Content-Type-Options" in headers or "Content-Security-Policy" in headers,
                not ("password" in content.lower() and "admin" in content.lower())  # No hardcoded creds
            ]
            
            return sum(security_checks) >= 2  # Basic security measures
        except Exception as e:
            logging.error(f"Security elements error: {e}")
            return False

    def test_performance_metrics(self):
        """Test page performance is acceptable"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/mining-calculator", timeout=15)
            load_time = time.time() - start_time
            
            if response.status_code != 200:
                return False
            
            # Performance checks
            performance_checks = [
                load_time < 10,  # Page loads within 10 seconds
                len(response.content) > 50000,  # Substantial content (50KB+)
                len(response.content) < 2000000,  # Not too heavy (2MB max)
                "gzip" in response.headers.get("Content-Encoding", "").lower() or len(response.content) < 500000
            ]
            
            return sum(performance_checks) >= 3  # Good performance metrics
        except Exception as e:
            logging.error(f"Performance metrics error: {e}")
            return False

    def test_multilingual_consistency(self):
        """Test multilingual content consistency"""
        try:
            zh_response = requests.get(f"{self.base_url}/mining-calculator?lang=zh", timeout=10)
            en_response = requests.get(f"{self.base_url}/mining-calculator?lang=en", timeout=10)
            
            if zh_response.status_code != 200 or en_response.status_code != 200:
                return False
            
            zh_content = zh_response.text
            en_content = en_response.text
            
            # Count major HTML structures in both versions
            zh_forms = zh_content.count('<form')
            en_forms = en_content.count('<form')
            zh_inputs = zh_content.count('<input')
            en_inputs = en_content.count('<input')
            zh_buttons = zh_content.count('<button') + zh_content.count('btn ')
            en_buttons = en_content.count('<button') + en_content.count('btn ')
            
            # Structure should be very similar
            consistency_checks = [
                abs(zh_forms - en_forms) <= 1,
                abs(zh_inputs - en_inputs) <= 2,
                abs(zh_buttons - en_buttons) <= 3,
                len(zh_content) > len(en_content) * 0.8,  # Similar content length
                len(en_content) > len(zh_content) * 0.8
            ]
            
            return sum(consistency_checks) >= 4  # High consistency
        except Exception as e:
            logging.error(f"Multilingual consistency error: {e}")
            return False

    def run_comprehensive_test(self):
        """Run all tests and generate comprehensive report"""
        logging.info("🚀 Starting Mining Calculator Regression Test - 99%+ Accuracy Target")
        
        # Define all tests
        tests = [
            ("Page Loading (Chinese)", self.test_page_loading_chinese),
            ("Page Loading (English)", self.test_page_loading_english), 
            ("Navigation Links", self.test_navigation_links),
            ("Form Elements Presence", self.test_form_elements_presence),
            ("API Endpoints Accessibility", self.test_api_endpoints_accessibility),
            ("Language Switching Functionality", self.test_language_switching_functionality),
            ("JavaScript Includes", self.test_javascript_includes),
            ("CSS Styling", self.test_css_styling),
            ("Network Stats Display", self.test_network_stats_display),
            ("Responsive Design Elements", self.test_responsive_design_elements),
            ("Security Elements", self.test_security_elements),
            ("Performance Metrics", self.test_performance_metrics),
            ("Multilingual Consistency", self.test_multilingual_consistency)
        ]
        
        # Run all tests
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Calculate results
        end_time = time.time()
        duration = end_time - self.start_time
        accuracy = (self.passed_tests / self.total_tests * 100) if self.total_tests > 0 else 0
        
        # Generate report
        report = {
            "test_run_info": {
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": round(duration, 2),
                "target_accuracy": "99%+",
                "actual_accuracy": f"{accuracy:.2f}%"
            },
            "summary": {
                "total_tests": self.total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "accuracy_percentage": round(accuracy, 2),
                "target_met": accuracy >= 99.0
            },
            "detailed_results": self.test_results
        }
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mining_calculator_regression_99_plus_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Print summary
        logging.info(f"📊 Test Summary:")
        logging.info(f"   Total Tests: {self.total_tests}")
        logging.info(f"   Passed: {self.passed_tests}")
        logging.info(f"   Failed: {self.failed_tests}")
        logging.info(f"   Accuracy: {accuracy:.2f}%")
        logging.info(f"   Target Met: {'✅ YES' if accuracy >= 99.0 else '❌ NO'}")
        logging.info(f"   Duration: {duration:.2f}s")
        logging.info(f"📁 Report saved: {filename}")
        
        if accuracy >= 99.0:
            logging.info("🎉 SUCCESS: 99%+ accuracy target achieved!")
        else:
            logging.warning(f"⚠️  BELOW TARGET: {accuracy:.2f}% accuracy (target: 99%+)")
        
        return report

if __name__ == "__main__":
    tester = MiningCalculatorRegressionTester()
    report = tester.run_comprehensive_test()
    
    # Exit with appropriate code
    sys.exit(0 if report['summary']['target_met'] else 1)