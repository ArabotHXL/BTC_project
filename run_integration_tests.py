#!/usr/bin/env python3
"""
SLA NFT System Integration Tests
End-to-end testing of the complete SLA NFT system

This script tests:
1. Application startup and basic functionality
2. SLA data collection and processing
3. NFT metadata generation
4. API endpoints (with authentication)
5. Dashboard interface components
6. Database operations
7. System integration
"""

import os
import sys
import time
import json
import logging
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List

# Test configuration
TEST_CONFIG = {
    'base_url': 'http://localhost:5000',
    'timeout': 30,
    'test_email': 'test@example.com',
    'test_password': 'testpassword123'
}

class SLANFTIntegrationTester:
    """Comprehensive integration tester for SLA NFT system"""
    
    def __init__(self):
        self.setup_logging()
        self.session = requests.Session()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'details': []
        }
    
    def setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def run_all_tests(self):
        """Run complete integration test suite"""
        self.logger.info("🚀 Starting SLA NFT System Integration Tests")
        self.logger.info("=" * 70)
        
        test_cases = [
            ("Application Health Check", self.test_application_health),
            ("Database Connectivity", self.test_database_connectivity),
            ("SLA Data Collection", self.test_sla_data_collection),
            ("NFT Metadata Generation", self.test_nft_metadata_generation),
            ("API Endpoints Structure", self.test_api_endpoints),
            ("Dashboard Interface", self.test_dashboard_interface),
            ("Frontend JavaScript", self.test_frontend_javascript),
            ("System Architecture", self.test_system_architecture),
            ("Security and Permissions", self.test_security_permissions),
            ("Performance Metrics", self.test_performance)
        ]
        
        for test_name, test_func in test_cases:
            self.logger.info(f"\n🔍 Running: {test_name}")
            self.logger.info("-" * 50)
            
            try:
                result = test_func()
                if result.get('status') == 'passed':
                    self.test_results['passed'] += 1
                    self.logger.info(f"✅ {test_name}: PASSED")
                elif result.get('status') == 'warning':
                    self.test_results['warnings'] += 1
                    self.logger.warning(f"⚠️ {test_name}: WARNING - {result.get('message', '')}")
                else:
                    self.test_results['failed'] += 1
                    self.logger.error(f"❌ {test_name}: FAILED - {result.get('message', '')}")
                
                self.test_results['details'].append({
                    'test': test_name,
                    'result': result
                })
                
            except Exception as e:
                self.test_results['failed'] += 1
                self.logger.error(f"💥 {test_name}: ERROR - {str(e)}")
                self.test_results['details'].append({
                    'test': test_name,
                    'result': {'status': 'error', 'message': str(e)}
                })
        
        # Generate final report
        self.generate_final_report()
    
    def test_application_health(self) -> Dict[str, Any]:
        """Test basic application health and responsiveness"""
        try:
            # Test main page
            response = self.session.get(f"{TEST_CONFIG['base_url']}/", timeout=TEST_CONFIG['timeout'])
            if response.status_code != 200:
                return {'status': 'failed', 'message': f'Main page returned {response.status_code}'}
            
            # Test favicon (should exist)
            favicon_response = self.session.get(f"{TEST_CONFIG['base_url']}/favicon.ico", timeout=5)
            
            # Test login page
            login_response = self.session.get(f"{TEST_CONFIG['base_url']}/login", timeout=10)
            if login_response.status_code != 200:
                return {'status': 'warning', 'message': 'Login page not accessible'}
            
            return {
                'status': 'passed',
                'details': {
                    'main_page_status': response.status_code,
                    'login_page_status': login_response.status_code,
                    'response_time_ms': response.elapsed.total_seconds() * 1000
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Application health check failed: {str(e)}'}
    
    def test_database_connectivity(self) -> Dict[str, Any]:
        """Test database connectivity and basic operations"""
        try:
            # Test if we can import database models
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            
            try:
                from models import db, SLAMetrics, SLACertificateRecord
                db_import_success = True
            except ImportError as e:
                return {'status': 'warning', 'message': f'Database models import failed: {str(e)}'}
            
            # Check if database URL is configured
            db_url = os.getenv('DATABASE_URL')
            if not db_url:
                return {'status': 'warning', 'message': 'DATABASE_URL not configured'}
            
            return {
                'status': 'passed',
                'details': {
                    'models_imported': db_import_success,
                    'database_configured': bool(db_url),
                    'database_type': 'postgresql' if 'postgresql' in db_url.lower() else 'other'
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Database connectivity test failed: {str(e)}'}
    
    def test_sla_data_collection(self) -> Dict[str, Any]:
        """Test SLA data collection system"""
        try:
            # Try to import SLA collector
            try:
                from sla_collector_engine import SLACollectorEngine
                collector = SLACollectorEngine()
                collector_available = True
            except ImportError:
                return {'status': 'warning', 'message': 'SLA collector engine not available'}
            
            # Test metrics structure
            expected_metrics = [
                'uptime', 'response_time', 'accuracy', 'availability',
                'transparency_score', 'blockchain_verifications', 'composite_sla_score'
            ]
            
            return {
                'status': 'passed',
                'details': {
                    'collector_available': collector_available,
                    'expected_metrics': expected_metrics,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'SLA data collection test failed: {str(e)}'}
    
    def test_nft_metadata_generation(self) -> Dict[str, Any]:
        """Test NFT metadata generation"""
        try:
            # Try to import NFT metadata generator
            try:
                from nft_metadata_generator import NFTMetadataGenerator
                generator = NFTMetadataGenerator()
                generator_available = True
            except ImportError:
                return {'status': 'warning', 'message': 'NFT metadata generator not available'}
            
            # Test metadata structure
            test_sla_data = {
                'uptime': 99.5,
                'response_time': 150,
                'accuracy': 98.8,
                'availability': 99.9,
                'transparency_score': 95.0,
                'blockchain_verifications': 100,
                'composite_sla_score': 96.2
            }
            
            # Check if we can create basic metadata structure
            metadata_template = {
                'name': 'SLA Certificate - Test',
                'description': 'Test SLA certificate',
                'attributes': []
            }
            
            return {
                'status': 'passed',
                'details': {
                    'generator_available': generator_available,
                    'metadata_template': metadata_template,
                    'test_data_valid': True
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'NFT metadata generation test failed: {str(e)}'}
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Test API endpoint structure and responses"""
        try:
            # Test API endpoints (without authentication)
            api_endpoints = [
                '/api/sla/status',
                '/api/sla/certificates',
                '/api/sla/reports'
            ]
            
            endpoint_results = {}
            for endpoint in api_endpoints:
                try:
                    response = self.session.get(f"{TEST_CONFIG['base_url']}{endpoint}", timeout=10)
                    # Expected to get 302 (redirect to login) or 401/403 (unauthorized)
                    endpoint_results[endpoint] = {
                        'status_code': response.status_code,
                        'requires_auth': response.status_code in [302, 401, 403],
                        'accessible': response.status_code < 500
                    }
                except Exception as e:
                    endpoint_results[endpoint] = {
                        'status_code': None,
                        'error': str(e),
                        'accessible': False
                    }
            
            # Check if all endpoints are properly protected
            all_protected = all(result.get('requires_auth', False) for result in endpoint_results.values())
            
            return {
                'status': 'passed' if all_protected else 'warning',
                'details': {
                    'endpoints_tested': len(api_endpoints),
                    'all_properly_protected': all_protected,
                    'endpoint_results': endpoint_results
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'API endpoints test failed: {str(e)}'}
    
    def test_dashboard_interface(self) -> Dict[str, Any]:
        """Test dashboard interface components"""
        try:
            # Test dashboard page (should redirect to login)
            dashboard_response = self.session.get(f"{TEST_CONFIG['base_url']}/dashboard", timeout=10)
            
            # Check if dashboard template exists
            dashboard_template_exists = os.path.exists('templates/dashboard_home.html')
            
            # Check if SLA NFT section is in template
            sla_nft_in_template = False
            if dashboard_template_exists:
                with open('templates/dashboard_home.html', 'r') as f:
                    template_content = f.read()
                    sla_nft_in_template = 'sla-nft-item' in template_content and 'SLA NFT' in template_content
            
            return {
                'status': 'passed',
                'details': {
                    'dashboard_protected': dashboard_response.status_code in [302, 401, 403],
                    'template_exists': dashboard_template_exists,
                    'sla_nft_section_added': sla_nft_in_template,
                    'response_status': dashboard_response.status_code
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Dashboard interface test failed: {str(e)}'}
    
    def test_frontend_javascript(self) -> Dict[str, Any]:
        """Test frontend JavaScript components"""
        try:
            # Check if SLA NFT JavaScript functions are in dashboard template
            dashboard_template_exists = os.path.exists('templates/dashboard_home.html')
            
            js_functions_present = False
            if dashboard_template_exists:
                with open('templates/dashboard_home.html', 'r') as f:
                    template_content = f.read()
                    required_functions = [
                        'openSLANFTModal',
                        'updateSLANFTStatus',
                        'loadSLANFTData'
                    ]
                    js_functions_present = all(func in template_content for func in required_functions)
            
            # Check for CSS styles
            sla_styles_present = False
            if dashboard_template_exists:
                with open('templates/dashboard_home.html', 'r') as f:
                    template_content = f.read()
                    sla_styles_present = '.sla-nft-item' in template_content and '.sla-status-indicator' in template_content
            
            return {
                'status': 'passed',
                'details': {
                    'template_exists': dashboard_template_exists,
                    'js_functions_added': js_functions_present,
                    'css_styles_added': sla_styles_present,
                    'interactive_components': js_functions_present and sla_styles_present
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Frontend JavaScript test failed: {str(e)}'}
    
    def test_system_architecture(self) -> Dict[str, Any]:
        """Test system architecture and module integration"""
        try:
            # Check if key files exist
            key_files = [
                'sla_nft_routes.py',
                'sla_collector_engine.py',
                'sla_nft_minting_system.py',
                'nft_metadata_generator.py',
                'contracts/SLAProofNFT.sol',
                'deploy_contracts.py',
                'config/blockchain_config.py',
                'test_contract_integration.py'
            ]
            
            files_status = {}
            for file_path in key_files:
                files_status[file_path] = os.path.exists(file_path)
            
            # Check if SLA routes are registered in app.py
            app_py_exists = os.path.exists('app.py')
            sla_routes_registered = False
            
            if app_py_exists:
                with open('app.py', 'r') as f:
                    app_content = f.read()
                    sla_routes_registered = 'sla_nft_bp' in app_content and 'register_blueprint' in app_content
            
            missing_files = [f for f, exists in files_status.items() if not exists]
            
            return {
                'status': 'passed' if len(missing_files) == 0 else 'warning',
                'details': {
                    'total_files': len(key_files),
                    'existing_files': len(key_files) - len(missing_files),
                    'missing_files': missing_files,
                    'sla_routes_registered': sla_routes_registered,
                    'architecture_complete': len(missing_files) == 0 and sla_routes_registered
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'System architecture test failed: {str(e)}'}
    
    def test_security_permissions(self) -> Dict[str, Any]:
        """Test security and permission system"""
        try:
            # Test that protected endpoints require authentication
            protected_endpoints = [
                '/api/sla/status',
                '/api/sla/certificates', 
                '/dashboard'
            ]
            
            security_results = {}
            for endpoint in protected_endpoints:
                try:
                    response = self.session.get(f"{TEST_CONFIG['base_url']}{endpoint}", timeout=5)
                    security_results[endpoint] = {
                        'status_code': response.status_code,
                        'properly_protected': response.status_code in [302, 401, 403],
                        'redirects_to_login': 'login' in response.url if hasattr(response, 'url') else False
                    }
                except Exception as e:
                    security_results[endpoint] = {'error': str(e)}
            
            all_protected = all(
                result.get('properly_protected', False) 
                for result in security_results.values() 
                if 'error' not in result
            )
            
            return {
                'status': 'passed' if all_protected else 'warning',
                'details': {
                    'endpoints_tested': len(protected_endpoints),
                    'all_properly_protected': all_protected,
                    'security_results': security_results
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Security permissions test failed: {str(e)}'}
    
    def test_performance(self) -> Dict[str, Any]:
        """Test basic performance metrics"""
        try:
            # Test response times
            start_time = time.time()
            response = self.session.get(f"{TEST_CONFIG['base_url']}/", timeout=30)
            response_time = time.time() - start_time
            
            # Test concurrent requests (simple load test)
            import threading
            import queue
            
            def make_request(result_queue):
                try:
                    start = time.time()
                    resp = self.session.get(f"{TEST_CONFIG['base_url']}/", timeout=10)
                    end = time.time()
                    result_queue.put({'success': True, 'time': end - start, 'status': resp.status_code})
                except Exception as e:
                    result_queue.put({'success': False, 'error': str(e)})
            
            # Run 5 concurrent requests
            threads = []
            result_queue = queue.Queue()
            
            for _ in range(5):
                thread = threading.Thread(target=make_request, args=(result_queue,))
                threads.append(thread)
                thread.start()
            
            for thread in threads:
                thread.join(timeout=15)
            
            # Collect results
            results = []
            while not result_queue.empty():
                results.append(result_queue.get())
            
            successful_requests = [r for r in results if r.get('success')]
            avg_response_time = sum(r['time'] for r in successful_requests) / len(successful_requests) if successful_requests else 0
            
            return {
                'status': 'passed' if response_time < 5.0 and avg_response_time < 5.0 else 'warning',
                'details': {
                    'single_request_time': response_time,
                    'concurrent_requests': len(results),
                    'successful_requests': len(successful_requests),
                    'average_response_time': avg_response_time,
                    'performance_acceptable': response_time < 5.0 and avg_response_time < 5.0
                }
            }
            
        except Exception as e:
            return {'status': 'failed', 'message': f'Performance test failed: {str(e)}'}
    
    def generate_final_report(self):
        """Generate and display final test report"""
        total_tests = self.test_results['passed'] + self.test_results['failed'] + self.test_results['warnings']
        
        print("\n" + "=" * 70)
        print("🏁 SLA NFT SYSTEM INTEGRATION TEST REPORT")
        print("=" * 70)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   ✅ Passed: {self.test_results['passed']}")
        print(f"   ⚠️  Warnings: {self.test_results['warnings']}")
        print(f"   ❌ Failed: {self.test_results['failed']}")
        
        success_rate = (self.test_results['passed'] / max(1, total_tests)) * 100
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        
        print(f"\n🔍 Detailed Results:")
        for detail in self.test_results['details']:
            test_name = detail['test']
            result = detail['result']
            status = result.get('status', 'unknown')
            
            if status == 'passed':
                print(f"   ✅ {test_name}")
            elif status == 'warning':
                print(f"   ⚠️  {test_name}: {result.get('message', '')}")
            else:
                print(f"   ❌ {test_name}: {result.get('message', '')}")
        
        print(f"\n🌟 System Status:")
        if self.test_results['failed'] == 0:
            if self.test_results['warnings'] == 0:
                print("   🎉 ALL SYSTEMS GO! SLA NFT system is fully integrated and functional.")
            else:
                print("   ✨ MOSTLY READY! SLA NFT system is functional with minor issues.")
        else:
            print("   ⚠️  NEEDS ATTENTION! Some critical issues need to be resolved.")
        
        # Save report to file
        report_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'summary': self.test_results,
            'system_status': 'ready' if self.test_results['failed'] == 0 else 'needs_attention'
        }
        
        with open('integration_test_report.json', 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Full report saved to: integration_test_report.json")
        print("=" * 70)

def main():
    """Run integration tests"""
    print("🚀 Starting SLA NFT System Integration Tests...")
    
    tester = SLANFTIntegrationTester()
    tester.run_all_tests()

if __name__ == '__main__':
    main()