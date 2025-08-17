#!/usr/bin/env python3
"""
Deployment Health Check Script
Provides rapid health checks optimized for deployment systems
"""

import os
import sys
import json
import time
import requests
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_app_readiness():
    """Check if application is ready for deployment"""
    port = os.environ.get('PORT', 5000)
    base_url = f"http://0.0.0.0:{port}"
    
    # Check readiness endpoint
    try:
        response = requests.get(f"{base_url}/ready", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'ready':
                logger.info("✅ Application readiness check passed")
                return True
    except Exception as e:
        logger.warning(f"Readiness check failed: {e}")
    
    # Fallback to simple status check
    try:
        response = requests.get(f"{base_url}/alive", timeout=3)
        if response.status_code == 200:
            logger.info("✅ Application liveness check passed")
            return True
    except Exception as e:
        logger.warning(f"Liveness check failed: {e}")
    
    logger.error("❌ Application health checks failed")
    return False

def check_file_readiness():
    """Check for readiness signal file"""
    readiness_file = '/tmp/app_ready'
    if os.path.exists(readiness_file):
        try:
            with open(readiness_file, 'r') as f:
                content = f.read().strip()
                if content == 'ready':
                    logger.info("✅ Deployment readiness signal found")
                    return True
        except Exception as e:
            logger.warning(f"Could not read readiness file: {e}")
    
    logger.warning("⚠️ No deployment readiness signal found")
    return False

def wait_for_readiness(max_wait=120):
    """Wait for application to be ready with timeout"""
    start_time = time.time()
    logger.info(f"Waiting for application readiness (max {max_wait}s)...")
    
    while time.time() - start_time < max_wait:
        # Check both HTTP endpoints and file signal
        if check_app_readiness() or check_file_readiness():
            elapsed = time.time() - start_time
            logger.info(f"🚀 Application is ready after {elapsed:.1f} seconds")
            return True
        
        time.sleep(2)  # Check every 2 seconds
    
    logger.error(f"❌ Application failed to become ready within {max_wait} seconds")
    return False

def main():
    """Main deployment health check"""
    if len(sys.argv) > 1 and sys.argv[1] == '--wait':
        # Wait mode for deployment scripts
        if wait_for_readiness():
            sys.exit(0)
        else:
            sys.exit(1)
    else:
        # Immediate check mode
        if check_app_readiness():
            print(json.dumps({
                "status": "ready",
                "timestamp": datetime.now().isoformat(),
                "deployment": "healthy"
            }))
            sys.exit(0)
        else:
            print(json.dumps({
                "status": "not_ready",
                "timestamp": datetime.now().isoformat(),
                "deployment": "unhealthy"
            }))
            sys.exit(1)

if __name__ == "__main__":
    main()