#!/usr/bin/env python3
"""
Application Functionality Test Suite
Tests all major components and identifies failures
"""
import os
import sys
import traceback
from typing import Dict, List

# Color codes
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text: str):
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(text: str):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    print(f"{BLUE}ℹ️  {text}{RESET}")

# Add parent directory to path for imports
import os
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

class TestResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.warning = None

def test_environment_variables():
    """Test 1: Environment Variables"""
    result = TestResult("Environment Variables")
    try:
        required = ['DATABASE_URL', 'SESSION_SECRET']
        missing = [var for var in required if not os.environ.get(var)]
        
        if missing:
            result.error = f"Missing required variables: {', '.join(missing)}"
        else:
            result.passed = True
    except Exception as e:
        result.error = str(e)
    
    return result

def test_database_connection():
    """Test 2: Database Connection"""
    result = TestResult("Database Connection")
    try:
        if not os.environ.get('DATABASE_URL'):
            result.error = "DATABASE_URL not set"
            return result
        
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(os.environ.get('DATABASE_URL'))
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None,
            connect_timeout=10
        )
        conn.close()
        result.passed = True
    except ImportError:
        result.error = "psycopg2 not installed"
    except Exception as e:
        result.error = str(e)
    
    return result

def test_flask_app_creation():
    """Test 3: Flask App Creation"""
    result = TestResult("Flask App Creation")
    try:
        from app import app
        if app:
            result.passed = True
        else:
            result.error = "App is None"
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_database_models():
    """Test 4: Database Models"""
    result = TestResult("Database Models")
    try:
        from models import db
        from app import app
        
        with app.app_context():
            # Try to import some key models
            from models import UserAccess, LoginRecord, NetworkSnapshot
            result.passed = True
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_billing_routes():
    """Test 5: Billing Routes"""
    result = TestResult("Billing Routes")
    try:
        from billing_routes import billing_bp, init_billing_plans
        from app import app
        
        with app.app_context():
            # Test initialization
            init_billing_plans(app)
            result.passed = True
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_calculator_routes():
    """Test 6: Calculator Routes"""
    result = TestResult("Calculator Routes")
    try:
        from routes.calculator_routes import calculator_bp
        result.passed = True
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_cache_manager():
    """Test 7: Cache Manager"""
    result = TestResult("Cache Manager")
    try:
        from cache_manager import CacheManager
        manager = CacheManager()
        result.passed = True
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_mining_calculator():
    """Test 8: Mining Calculator"""
    result = TestResult("Mining Calculator")
    try:
        from mining_calculator import calculate_mining_profitability, MINER_DATA
        
        # Test a simple calculation
        result_data = calculate_mining_profitability(
            hashrate=100.0,
            power_consumption=3000.0,
            electricity_cost=0.05
        )
        
        if result_data and 'daily_profit' in result_data:
            result.passed = True
        else:
            result.error = "Calculation returned invalid data"
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_blueprint_registration():
    """Test 9: Blueprint Registration"""
    result = TestResult("Blueprint Registration")
    try:
        from app import app
        
        # Check for duplicate calculator blueprint
        calculator_count = sum(1 for bp in app.blueprints.keys() if 'calculator' in bp.lower())
        
        if calculator_count > 1:
            result.warning = f"Multiple calculator blueprints found: {calculator_count}"
        
        result.passed = True
    except Exception as e:
        result.error = f"{type(e).__name__}: {str(e)}"
        result.traceback = traceback.format_exc()
    
    return result

def test_python_compatibility():
    """Test 10: Python 3.9 Compatibility"""
    result = TestResult("Python 3.9 Compatibility")
    try:
        import sys
        if sys.version_info < (3, 9):
            result.error = f"Python {sys.version_info.major}.{sys.version_info.minor} is too old (need 3.9+)"
        elif sys.version_info >= (3, 11):
            result.warning = f"Python {sys.version_info.major}.{sys.version_info.minor} - some features may require 3.11+"
            result.passed = True
        else:
            result.passed = True
    except Exception as e:
        result.error = str(e)
    
    return result

def run_all_tests():
    """Run all tests and return results"""
    tests = [
        test_environment_variables,
        test_database_connection,
        test_flask_app_creation,
        test_database_models,
        test_billing_routes,
        test_calculator_routes,
        test_cache_manager,
        test_mining_calculator,
        test_blueprint_registration,
        test_python_compatibility,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            result = TestResult(test_func.__name__)
            result.error = f"Test crashed: {str(e)}"
            result.traceback = traceback.format_exc()
            results.append(result)
    
    return results

def main():
    """Main test runner"""
    print_header("🧪 Application Functionality Test Suite")
    print("Testing all major components and identifying failures...\n")
    
    results = run_all_tests()
    
    # Print results
    passed = 0
    failed = 0
    warnings = 0
    
    for result in results:
        if result.passed:
            print_success(f"{result.name}")
            passed += 1
        elif result.warning:
            print_warning(f"{result.name}: {result.warning}")
            warnings += 1
        else:
            print_error(f"{result.name}: {result.error}")
            failed += 1
            if hasattr(result, 'traceback'):
                print(f"{RED}{result.traceback}{RESET}")
    
    # Summary
    print_header("📊 Test Summary")
    print(f"{GREEN}✅ Passed: {passed}{RESET}")
    if warnings > 0:
        print(f"{YELLOW}⚠️  Warnings: {warnings}{RESET}")
    if failed > 0:
        print(f"{RED}❌ Failed: {failed}{RESET}")
    
    # Recommendations
    if failed > 0:
        print_header("💡 Recommendations")
        print("1. Check the error messages above")
        print("2. Verify environment variables are set correctly")
        print("3. Check that all dependencies are installed")
        print("4. Review the traceback for detailed error information")
    
    return 0 if failed == 0 else 1

if __name__ == '__main__':
    sys.exit(main())
