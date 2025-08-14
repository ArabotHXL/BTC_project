"""
Database Health and Connection Management
Provides robust database connection with retry logic and health checks
"""

import os
import time
import logging
import psycopg2
from urllib.parse import urlparse
from contextlib import contextmanager
from typing import Optional, Dict, Any

class DatabaseHealthManager:
    """Manages database connection health with retry logic"""
    
    def __init__(self, max_retries=5, retry_delay=2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.logger = logging.getLogger(__name__)
        
    def validate_database_url(self, database_url: str) -> bool:
        """Validate database URL format"""
        try:
            parsed = urlparse(database_url)
            return all([parsed.scheme, parsed.netloc, parsed.path])
        except Exception:
            return False
    
    def check_database_connection(self, database_url: str) -> Dict[str, Any]:
        """Check database connection with detailed status"""
        if not database_url:
            return {
                'connected': False,
                'error': 'DATABASE_URL environment variable not set',
                'suggestion': 'Set DATABASE_URL environment variable'
            }
        
        if not self.validate_database_url(database_url):
            return {
                'connected': False,
                'error': 'Invalid DATABASE_URL format',
                'suggestion': 'Update DATABASE_URL with valid PostgreSQL connection string'
            }
        
        for attempt in range(self.max_retries):
            try:
                # Parse database URL
                parsed = urlparse(database_url)
                
                # Extract connection parameters
                conn_params = {
                    'host': parsed.hostname,
                    'port': parsed.port or 5432,
                    'database': parsed.path.lstrip('/'),
                    'user': parsed.username,
                    'password': parsed.password,
                    'connect_timeout': 10,
                    'application_name': 'btc_mining_calculator_health_check'
                }
                
                # Test connection
                conn = psycopg2.connect(**conn_params)
                
                # Execute basic query to verify database is operational
                with conn.cursor() as cursor:
                    cursor.execute('SELECT version()')
                    version = cursor.fetchone()[0]
                
                conn.close()
                
                return {
                    'connected': True,
                    'database_version': version,
                    'attempt': attempt + 1,
                    'total_attempts': self.max_retries
                }
                
            except psycopg2.OperationalError as e:
                error_message = str(e)
                self.logger.warning(f"Database connection attempt {attempt + 1}/{self.max_retries} failed: {error_message}")
                
                # Check for specific Neon endpoint disabled error
                if 'endpoint has been disabled' in error_message.lower():
                    return {
                        'connected': False,
                        'error': 'Neon database endpoint has been disabled',
                        'suggestion': 'Enable your Neon database endpoint using the Neon API or console',
                        'neon_specific': True
                    }
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    return {
                        'connected': False,
                        'error': error_message,
                        'attempt': attempt + 1,
                        'total_attempts': self.max_retries,
                        'suggestion': 'Check DATABASE_URL and ensure database server is running'
                    }
                    
            except Exception as e:
                self.logger.error(f"Unexpected database connection error: {e}")
                return {
                    'connected': False,
                    'error': f'Unexpected error: {str(e)}',
                    'suggestion': 'Check database configuration and network connectivity'
                }
        
        return {
            'connected': False,
            'error': 'Max retries exceeded',
            'total_attempts': self.max_retries
        }
    
    def wait_for_database(self, database_url: str, timeout=60) -> bool:
        """Wait for database to become available with timeout"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            result = self.check_database_connection(database_url)
            if result['connected']:
                self.logger.info("Database connection established successfully")
                return True
            
            self.logger.info(f"Waiting for database... ({result.get('error', 'Unknown error')})")
            time.sleep(self.retry_delay)
        
        self.logger.error(f"Database connection timeout after {timeout} seconds")
        return False
    
    @contextmanager
    def safe_database_operation(self, database_url: str):
        """Context manager for safe database operations"""
        conn = None
        try:
            parsed = urlparse(database_url)
            conn_params = {
                'host': parsed.hostname,
                'port': parsed.port or 5432,
                'database': parsed.path.lstrip('/'),
                'user': parsed.username,
                'password': parsed.password,
                'connect_timeout': 10,
                'application_name': 'btc_mining_calculator'
            }
            
            conn = psycopg2.connect(**conn_params)
            yield conn
            
        except Exception as e:
            if conn:
                conn.rollback()
            raise e
        finally:
            if conn:
                conn.close()

# Global instance
db_health_manager = DatabaseHealthManager()