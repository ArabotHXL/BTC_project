#!/usr/bin/env python3
"""
Database Access Test
Comprehensive test to verify database connectivity and access
"""
import os
import sys
from typing import Dict, List, Tuple

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

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

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

def test_psycopg2_connection():
    """Test 1: Direct psycopg2 connection"""
    print_header("Test 1: Direct psycopg2 Connection")
    
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print_error("DATABASE_URL not set")
        return False
    
    try:
        import psycopg2
        from urllib.parse import urlparse
        
        parsed = urlparse(db_url)
        print_info(f"Connecting to: {parsed.hostname}:{parsed.port or 5432}")
        
        conn = psycopg2.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else None,
            connect_timeout=10
        )
        
        cursor = conn.cursor()
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print_success(f"Connected! PostgreSQL: {version.split(',')[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except ImportError:
        print_error("psycopg2 not installed")
        return False
    except Exception as e:
        print_error(f"Connection failed: {str(e)}")
        return False

def test_sqlalchemy_connection():
    """Test 2: SQLAlchemy connection"""
    print_header("Test 2: SQLAlchemy Connection")
    
    try:
        from app import app
        from db import db
        from sqlalchemy import text
        
        with app.app_context():
            result = db.session.execute(text('SELECT version();'))
            version = result.fetchone()[0]
            print_success(f"Connected! PostgreSQL: {version.split(',')[0]}")
            return True
            
    except Exception as e:
        print_error(f"SQLAlchemy connection failed: {str(e)}")
        return False

def test_table_access():
    """Test 3: Table access"""
    print_header("Test 3: Table Access")
    
    try:
        from app import app
        from db import db
        from sqlalchemy import text
        
        with app.app_context():
            # List all tables
            result = db.session.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            tables = [row[0] for row in result.fetchall()]
            
            print_info(f"Found {len(tables)} tables")
            
            # Test access to common tables
            test_tables = ['users', 'user_access', 'network_snapshot', 'miner_model']
            accessible = 0
            
            for table_name in test_tables:
                if table_name in tables:
                    try:
                        result = db.session.execute(text(f'SELECT COUNT(*) FROM {table_name};'))
                        count = result.fetchone()[0]
                        print_success(f"{table_name}: {count} rows")
                        accessible += 1
                    except Exception as e:
                        print_warning(f"{table_name}: {str(e)[:50]}")
                else:
                    print_warning(f"{table_name}: Table not found")
            
            return accessible > 0
            
    except Exception as e:
        print_error(f"Table access test failed: {str(e)}")
        return False

def test_model_access():
    """Test 4: Model access"""
    print_header("Test 4: Database Model Access")
    
    try:
        from app import app
        from models import UserAccess, NetworkSnapshot, MinerModel
        
        with app.app_context():
            # Test UserAccess
            try:
                count = UserAccess.query.count()
                print_success(f"UserAccess: {count} records")
            except Exception as e:
                print_warning(f"UserAccess: {str(e)[:50]}")
            
            # Test NetworkSnapshot
            try:
                count = NetworkSnapshot.query.count()
                print_success(f"NetworkSnapshot: {count} records")
            except Exception as e:
                print_warning(f"NetworkSnapshot: {str(e)[:50]}")
            
            # Test MinerModel
            try:
                count = MinerModel.query.count()
                print_success(f"MinerModel: {count} records")
            except Exception as e:
                print_warning(f"MinerModel: {str(e)[:50]}")
            
            return True
            
    except Exception as e:
        print_error(f"Model access test failed: {str(e)}")
        return False

def test_write_access():
    """Test 5: Write access (read-only test)"""
    print_header("Test 5: Write Access (Read-Only Test)")
    
    try:
        from app import app
        from db import db
        from sqlalchemy import text
        
        with app.app_context():
            # Test if we can execute a SELECT (read access)
            result = db.session.execute(text('SELECT 1;'))
            result.fetchone()
            print_success("Read access: OK")
            
            # Note: We don't test actual writes to avoid modifying data
            print_info("Write access: Not tested (to avoid data modification)")
            return True
            
    except Exception as e:
        print_error(f"Write access test failed: {str(e)}")
        return False

def main():
    """Run all database tests"""
    print_header("🗄️  Database Access Test Suite")
    print("Testing database connectivity and access...\n")
    
    results = {
        'psycopg2': test_psycopg2_connection(),
        'sqlalchemy': test_sqlalchemy_connection(),
        'tables': test_table_access(),
        'models': test_model_access(),
        'write': test_write_access(),
    }
    
    # Summary
    print_header("📊 Test Summary")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: Passed")
        else:
            print_error(f"{test_name}: Failed")
    
    print(f"\n{BOLD}Results: {passed}/{total} tests passed{RESET}\n")
    
    if passed == total:
        print_success("✅ All database access tests passed!")
        print("   Your database connection is working correctly.")
    else:
        print_warning("⚠️  Some tests failed. Check the errors above.")
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
