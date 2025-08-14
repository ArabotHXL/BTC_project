"""
Pre-deployment startup checks
Validates environment and database connectivity before starting the application
"""

import os
import sys
import logging
from database_health import db_health_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_environment():
    """Check required environment variables"""
    required_vars = [
        'DATABASE_URL',
        'SESSION_SECRET'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {missing_vars}")
        return False
    
    logger.info("All required environment variables are set")
    return True

def check_database():
    """Check database connectivity"""
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not configured")
        return False
    
    logger.info("Checking database connectivity...")
    db_status = db_health_manager.check_database_connection(database_url)
    
    if db_status['connected']:
        logger.info(f"Database connection successful: {db_status.get('database_version', 'Unknown version')}")
        return True
    else:
        error_msg = db_status.get('error', 'Unknown error')
        suggestion = db_status.get('suggestion', 'Check configuration')
        
        logger.error(f"Database connection failed: {error_msg}")
        logger.error(f"Suggestion: {suggestion}")
        
        if db_status.get('neon_specific'):
            logger.error("NEON DATABASE ISSUE DETECTED:")
            logger.error("1. Visit https://console.neon.tech/")
            logger.error("2. Navigate to your project")
            logger.error("3. Check if the database endpoint is enabled")
            logger.error("4. Verify your DATABASE_URL is correct")
        
        return False

def main():
    """Run all startup checks"""
    logger.info("Starting pre-deployment checks...")
    
    checks_passed = True
    
    # Check environment variables
    if not check_environment():
        checks_passed = False
    
    # Check database connectivity
    if not check_database():
        checks_passed = False
    
    if checks_passed:
        logger.info("All startup checks passed successfully")
        return 0
    else:
        logger.error("Startup checks failed - deployment may encounter issues")
        return 1

if __name__ == '__main__':
    sys.exit(main())