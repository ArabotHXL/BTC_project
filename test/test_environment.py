#!/usr/bin/env python3
"""
Environment Variables Test Suite
Tests all environment variables and identifies what's missing from Replit
"""
import os
import sys
from typing import Dict, List, Tuple

# Color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{BOLD}{BLUE}{'='*70}{RESET}")
    print(f"{BOLD}{BLUE}{text}{RESET}")
    print(f"{BOLD}{BLUE}{'='*70}{RESET}\n")

def print_success(text: str):
    """Print success message"""
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text: str):
    """Print error message"""
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text: str):
    """Print warning message"""
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text: str):
    """Print info message"""
    print(f"{BLUE}ℹ️  {text}{RESET}")

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print_success("Loaded .env file")
except ImportError:
    print_warning("python-dotenv not installed - .env file not loaded")
except Exception as e:
    print_warning(f"Could not load .env file: {e}")

# Define all environment variables
ENV_VARS = {
    # CRITICAL - Required for application to start
    'CRITICAL': {
        'DATABASE_URL': {
            'description': 'PostgreSQL database connection string',
            'example': 'postgresql://user:password@host:5432/database',
            'required': True,
            'from_replit': 'Secrets tab → DATABASE_URL',
            'friendly_name': 'Database Connection'
        },
        'SESSION_SECRET': {
            'description': 'Flask session encryption key (minimum 32 characters)',
            'example': 'your-secure-random-secret-key-here',
            'required': True,
            'from_replit': 'Secrets tab → SESSION_SECRET',
            'friendly_name': 'Session Security Key'
        }
    },
    
    # IMPORTANT - Required for specific features
    'IMPORTANT': {
        'COINWARZ_API_KEY': {
            'description': 'API key for CoinWarz mining data service',
            'example': 'your_coinwarz_api_key',
            'required': False,
            'from_replit': 'Secrets tab → COINWARZ_API_KEY',
            'friendly_name': 'CoinWarz API Key'
        },
        'REDIS_URL': {
            'description': 'Redis connection URL for caching (optional)',
            'example': 'redis://localhost:6379/0',
            'required': False,
            'from_replit': 'Secrets tab → REDIS_URL (if using Redis)',
            'friendly_name': 'Redis Cache URL'
        }
    },
    
    # BLOCKCHAIN - Optional blockchain features
    'BLOCKCHAIN': {
        'BLOCKCHAIN_PRIVATE_KEY': {
            'description': 'Private key for blockchain transactions (testnet/mainnet)',
            'example': '0x...',
            'required': False,
            'from_replit': 'Secrets tab → BLOCKCHAIN_PRIVATE_KEY',
            'friendly_name': 'Blockchain Wallet Private Key'
        },
        'PINATA_JWT': {
            'description': 'Pinata JWT token for IPFS storage (or set BLOCKCHAIN_DISABLE_IPFS=true)',
            'example': 'your_pinata_jwt_token',
            'required': False,
            'from_replit': 'Secrets tab → PINATA_JWT',
            'friendly_name': 'Pinata IPFS Token',
            'alternative': 'Set BLOCKCHAIN_DISABLE_IPFS=true to disable IPFS'
        },
        'BLOCKCHAIN_DISABLE_IPFS': {
            'description': 'Disable IPFS functionality (set to "true" if no PINATA_JWT)',
            'example': 'true',
            'required': False,
            'from_replit': 'Secrets tab → BLOCKCHAIN_DISABLE_IPFS',
            'friendly_name': 'Disable IPFS'
        }
    },
    
    # OPTIONAL - Performance and features
    'OPTIONAL': {
        'ENABLE_BACKGROUND_SERVICES': {
            'description': 'Enable background scheduled tasks (0 or 1)',
            'example': '0',
            'required': False,
            'default': '0',
            'friendly_name': 'Background Services'
        },
        'LOG_LEVEL': {
            'description': 'Logging level (DEBUG, INFO, WARNING, ERROR)',
            'example': 'INFO',
            'required': False,
            'default': 'INFO',
            'friendly_name': 'Log Level'
        },
        'FLASK_ENV': {
            'description': 'Flask environment (development or production)',
            'example': 'development',
            'required': False,
            'default': 'development',
            'friendly_name': 'Flask Environment'
        },
        'FLASK_RUN_PORT': {
            'description': 'Port to run Flask application',
            'example': '5001',
            'required': False,
            'default': '5001',
            'friendly_name': 'Application Port'
        },
        'SKIP_DATABASE_HEALTH_CHECK': {
            'description': 'Skip database health check on startup (1 or 0)',
            'example': '1',
            'required': False,
            'default': '1',
            'friendly_name': 'Skip DB Health Check'
        },
        'FAST_STARTUP': {
            'description': 'Enable fast startup mode (1 or 0)',
            'example': '1',
            'required': False,
            'default': '1',
            'friendly_name': 'Fast Startup'
        }
    }
}

def check_environment_variables() -> Tuple[Dict, List[str], List[str]]:
    """Check all environment variables and return status"""
    results = {
        'critical': {'missing': [], 'present': []},
        'important': {'missing': [], 'present': []},
        'blockchain': {'missing': [], 'present': []},
        'optional': {'missing': [], 'present': []}
    }
    
    missing_critical = []
    warnings = []
    
    for category, vars_dict in ENV_VARS.items():
        for var_name, var_info in vars_dict.items():
            value = os.environ.get(var_name)
            
            if value:
                results[category.lower()]['present'].append(var_name)
                if category == 'CRITICAL':
                    print_success(f"{var_info['friendly_name']}: Set")
                elif category == 'IMPORTANT':
                    print_info(f"{var_info['friendly_name']}: Set")
            else:
                results[category.lower()]['missing'].append(var_name)
                if category == 'CRITICAL':
                    print_error(f"{var_info['friendly_name']}: MISSING (Required!)")
                    missing_critical.append(var_name)
                elif category == 'IMPORTANT':
                    print_warning(f"{var_info['friendly_name']}: Not set (Optional but recommended)")
                elif category == 'BLOCKCHAIN':
                    if var_name == 'BLOCKCHAIN_DISABLE_IPFS' and not os.environ.get('PINATA_JWT'):
                        print_warning(f"{var_info['friendly_name']}: Not set (IPFS will be disabled)")
                    else:
                        print_info(f"{var_info['friendly_name']}: Not set (Optional)")
                else:
                    default = var_info.get('default', 'Not set')
                    print_info(f"{var_info['friendly_name']}: {default} (Using default)")
    
    return results, missing_critical, warnings

def print_replit_instructions(missing_vars: List[str]):
    """Print instructions for getting variables from Replit"""
    if not missing_vars:
        return
    
    print_header("📋 How to Get Missing Variables from Replit")
    
    for var_name in missing_vars:
        var_info = None
        for category in ENV_VARS.values():
            if var_name in category:
                var_info = category[var_name]
                break
        
        if var_info:
            print(f"\n{BOLD}{var_info['friendly_name']} ({var_name}){RESET}")
            print(f"  Description: {var_info['description']}")
            print(f"  Where to find: {var_info['from_replit']}")
            print(f"  Example: {var_info['example']}")
            if 'alternative' in var_info:
                print(f"  {YELLOW}Alternative: {var_info['alternative']}{RESET}")

def test_database_connection():
    """Test database connection"""
    print_header("🗄️  Database Connection Test")
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print_error("DATABASE_URL not set - cannot test connection")
        return False
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        # Parse connection string
        parsed = urlparse(db_url)
        
        # Test connection
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None,
            connect_timeout=10
        )
        conn.close()
        print_success("Database connection successful!")
        return True
    except ImportError:
        print_error("psycopg2 not installed - cannot test connection")
        return False
    except Exception as e:
        print_error(f"Database connection failed: {str(e)}")
        return False

def test_application_imports():
    """Test if application modules can be imported"""
    print_header("📦 Application Module Import Test")
    
    # Add parent directory to path
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)
    
    modules_to_test = [
        ('app', 'Flask application'),
        ('config', 'Configuration'),
        ('models', 'Database models'),
        ('db', 'Database connection'),
    ]
    
    success_count = 0
    for module_name, description in modules_to_test:
        try:
            __import__(module_name)
            print_success(f"{description}: Import successful")
            success_count += 1
        except Exception as e:
            print_error(f"{description}: Import failed - {str(e)}")
    
    return success_count == len(modules_to_test)

def main():
    """Main test function"""
    print_header("🧪 Environment Variables Test Suite")
    print("This test will check all required and optional environment variables")
    print("and identify what you need to get from Replit.\n")
    
    # Check environment variables
    results, missing_critical, warnings = check_environment_variables()
    
    # Print summary
    print_header("📊 Test Summary")
    
    if missing_critical:
        print_error(f"❌ {len(missing_critical)} CRITICAL variables missing!")
        print("The application will NOT start without these variables.\n")
        print_replit_instructions(missing_critical)
    else:
        print_success("✅ All critical variables are set!")
    
    # Test database connection
    if 'DATABASE_URL' in os.environ:
        test_database_connection()
    
    # Test imports
    test_application_imports()
    
    # Final recommendations
    print_header("💡 Recommendations")
    
    if missing_critical:
        print("1. Get the missing critical variables from Replit Secrets tab")
        print("2. Add them to your .env file")
        print("3. Run this test again to verify")
    else:
        print("✅ All critical variables are set!")
        print("You can now run the application with: python main.py")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} optional variables are not set")
        print("These are recommended but not required for basic functionality")
    
    return 0 if not missing_critical else 1

if __name__ == '__main__':
    sys.exit(main())
